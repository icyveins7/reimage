from PySide6.QtWidgets import QMainWindow, QVBoxLayout, QHBoxLayout, QWidget, QLabel, QComboBox
from PySide6.QtWidgets import QFormLayout, QLineEdit, QCheckBox, QPushButton
from PySide6.QtCore import Qt, Signal, Slot, QRectF
import pyqtgraph as pg
import numpy as np
from dsp import *

class EstimateBaudWindow(QMainWindow):
    def __init__(self, slicedData=None, startIdx=None, endIdx=None, fs=1.0):
        super().__init__()

        # Attaching data
        self.slicedData = slicedData
        self.fs = fs

        # Processed data
        self.filtered = None

        # Calculate plain fft
        self.datafft = np.fft.fft(self.slicedData, 65536) # TODO: make fft len variable

        # And processed fft
        self.filteredfft = None
        
        # Some optional plot items
        self.filtRegion = None

        # Aesthetics..
        self.setWindowTitle("Baud Rate Estimation")

        # Main layout
        widget = QWidget()
        self.layout = QHBoxLayout()
        widget.setLayout(self.layout)
        self.setCentralWidget(widget)

        # Add the left plot widget
        self.glw = pg.GraphicsLayoutWidget()
        self.layout.addWidget(self.glw)
        self.p = self.glw.addPlot(row=0,col=0)
        if startIdx is not None and endIdx is not None:
            self.p.setLabels(title="Sample %d to %d" % (startIdx, endIdx))
        self.plegend = self.p.addLegend() # TODO: fix legend not appearing?
        self.plt = pg.PlotDataItem() # Original data
        self.pltf = pg.PlotDataItem(pen='r') # for the filtered version
        self.plegend.addItem(self.plt, 'Original FFT')
        self.plegend.addItem(self.pltf, 'Filtered FFT at Baseband')
        self.p.addItem(self.plt)
        self.p.addItem(self.pltf)
        
        # Create the options
        self.midLayout = QVBoxLayout()
        self.paramsLayout = QFormLayout()
        self.midLayout.addLayout(self.paramsLayout)

        self.fsNonEdit = QLineEdit("%f" % (self.fs))
        self.fsNonEdit.setEnabled(False) # Disable edits
        self.paramsLayout.addRow("Sample rate", self.fsNonEdit)

        self.prefilterCheckbox = QCheckBox()
        self.paramsLayout.addRow("Prefilter?", self.prefilterCheckbox)
        self.filtLfreq = QLineEdit()
        self.filtLfreq.setEnabled(False)
        self.filtRfreq = QLineEdit()
        self.filtRfreq.setEnabled(False)
        self.paramsLayout.addRow("Prefilter Left Bound", self.filtLfreq)
        self.paramsLayout.addRow("Prefilter Right Bound", self.filtRfreq)

        self.numTapsDropdown = QComboBox()
        self.numTapsDropdown.addItems(["%d" % (2**i) for i in range(6,15)])
        self.numTapsDropdown.setEnabled(False)
        self.paramsLayout.addRow("Prefilter No. of Taps", self.numTapsDropdown)
        # Link filter checkbox to things
        self.prefilterCheckbox.toggled.connect(self.numTapsDropdown.setEnabled)
        self.prefilterCheckbox.toggled.connect(self.spawnFilterRegion)

        # The final bits..
        self.runBtn = QPushButton("Run")
        self.runBtn.clicked.connect(self.run)
        self.midLayout.addWidget(self.runBtn)
        self.layout.addLayout(self.midLayout)

        # Add the right plot widget
        self.oglw = pg.GraphicsLayoutWidget()
        self.layout.addWidget(self.oglw)
        self.op = self.oglw.addPlot(row=0,col=0)
        self.oplegend = self.op.addLegend()
        self.oplt = pg.PlotDataItem() # Original data
        self.opltmarkers = pg.ScatterPlotItem(symbol='x', pen='r', brush='r') # For the idx markers
        self.oplegend.addItem(self.oplt, "Output Cyclostationary Spectrum")
        self.oplegend.addItem(self.opltmarkers, "Peaks Used in Baud Estimation")
        self.op.addItem(self.oplt)
        self.op.addItem(self.opltmarkers)

        # Plot the left (initial data fft) side first
        self.leftplot()

    @Slot()
    def spawnFilterRegion(self):
        if self.prefilterCheckbox.isChecked():
            # Add a linear region
            self.filtRegion = pg.LinearRegionItem((-0.1*self.fs,0.1*self.fs))
            self.filtRegion.sigRegionChanged.connect(self.onFiltRegionChanged)
            self.p.addItem(self.filtRegion)
            self.onFiltRegionChanged() # Call it once to update the text
        else:
            # Delete the region
            self.p.removeItem(self.filtRegion)
            self.filtRegion = None
            # Clear the region text 
            self.filtLfreq.clear()
            self.filtRfreq.clear()

    @Slot()
    def onFiltRegionChanged(self):
        region = self.filtRegion.getRegion()
        self.filtLfreq.setText("%f" % (region[0]))
        self.filtRfreq.setText("%f" % (region[1]))
        
    def leftplot(self):
        self.plt.setData(
            np.fft.fftshift(makeFreq(self.datafft.size, self.fs)),
            np.fft.fftshift(20*np.log10(np.abs(self.datafft)))
        )

        if self.filteredfft is not None:
            print("Plotting filtered fft")
            self.pltf.setData(
                np.fft.fftshift(makeFreq(self.filteredfft.size, self.fs)),
                np.fft.fftshift(20*np.log10(np.abs(self.filteredfft)))
            )

    @Slot()
    def run(self):
        # First filter + shift data if set
        if self.prefilterCheckbox.isChecked():
            region = self.filtRegion.getRegion()

            ftap = sps.firwin(
                int(self.numTapsDropdown.currentText()),
                (region[1]-region[0])/self.fs
            )

            freqshift = np.exp(1j*2*np.pi*-np.mean(region)*np.arange(self.slicedData.size)/self.fs)

            self.filtered = sps.lfilter(ftap,1,self.slicedData*freqshift)

        else:
            self.filtered = np.copy(self.slicedData)

        # Create fft of it
        self.filteredfft = np.fft.fft(self.filtered, 65536) # TODO: make fft len variable

        # Replot the filtered version
        self.leftplot()

        # Now run the actual cyclostationary process
        estBaud, idx1, idx2, Xf, Xfreq = estimateBaud(self.filtered, self.fs)

        # And plot the results on the right
        self.rightplot(estBaud, idx1, idx2, Xf, Xfreq)

    def rightplot(self, estBaud, idx1, idx2, Xf, Xfreq):
        self.oplt.setData(
            Xfreq,
            np.abs(Xf)
        )

        # Place markers for the indices used
        self.opltmarkers.setData(
            x=[Xfreq[idx1], Xfreq[idx2]],
            y=np.abs([Xf[idx1], Xf[idx2]]),
            symbol='x'
        )

        # Set the title to reflect the baud rate estimate
        self.op.setLabels(title="Est. Baudrate = %f" % (estBaud))
