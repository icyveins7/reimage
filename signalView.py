from PySide6.QtWidgets import QFrame, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, QLineEdit
from PySide6.QtCore import Qt, Signal, Slot, QRectF
import pyqtgraph as pg
import numpy as np
import scipy.signal as sps

class SignalView(QFrame):
    def __init__(self, ydata, parent=None, f=Qt.WindowFlags()):
        super().__init__(parent, f)
        # Attach the data (hopefully this doesn't copy)
        self.ydata = ydata

        # Placeholder for xdata
        self.xdata = None
        self.fs = None
        self.startTime = None

        # Placeholder for spectrogram data
        self.freqs = None
        self.ts = None
        self.sxx = None

        # Create a graphics view
        self.glw = pg.GraphicsLayoutWidget() # Window for the amplitude time plot
        self.p = self.glw.addPlot(row=0,col=0) # The amp-time plotItem
        self.sp = pg.ImageItem()
        self.spw = self.glw.addPlot(row=1,col=0)
        self.spw.addItem(self.sp)

        # Create some buttons for plot manipulations
        self.btnLayout = QHBoxLayout()
        self.linearRegionStartEdit = QLineEdit()
        self.linearRegionEndEdit = QLineEdit()
        self.linearRegionColon = QLabel(":")
        self.linearRegionBtn = QPushButton("Add/Remove Time Slice")
        self.linearRegionBtn.clicked.connect(self.onLinearRegionBtnClicked)
        self.btnLayout.addWidget(self.linearRegionStartEdit)
        self.btnLayout.addWidget(self.linearRegionColon)
        self.btnLayout.addWidget(self.linearRegionEndEdit)
        self.btnLayout.addWidget(self.linearRegionBtn)

        # Placeholders for linear regions 
        self.linearRegion = None # TODO: make ctrl-click add it instead of via button?
        # TODO: make linear region text edits update with click and drag of the region

        # Create the main layout
        self.layout = QVBoxLayout()
        self.layout.addLayout(self.btnLayout)
        self.layout.addWidget(self.glw)

        self.setLayout(self.layout)

        

    def setXData(self, fs, startTime=0):
        self.fs = fs
        self.startTime = startTime
        self.xdata = (np.arange(self.ydata.size) * 1/self.fs) + self.startTime

    def setYData(self, ydata):
        self.ydata = ydata
        self.p.clear()
        self.spw.clear()
        self.plotAmpTime()
        self.plotSpecgram()

    def plotAmpTime(self):
        if self.xdata is None:
            self.p.plot(np.abs(self.ydata))
        else:
            self.p.plot(self.xdata, np.abs(self.ydata))
        self.p.setMouseEnabled(x=True,y=False)
            
    def plotSpecgram(self, fs=1.0, window=('tukey',0.25), nperseg=None, noverlap=None, nfft=None, auto_transpose=True):
        self.fs = fs

        self.freqs, self.ts, self.sxx = sps.spectrogram(self.ydata, fs, window, nperseg, noverlap, nfft, return_onesided=False)

        self.freqs = np.fft.fftshift(self.freqs)
        self.sxx = np.fft.fftshift(self.sxx, axes=0)
        # Obtain the spans and gaps for proper plotting
        tgap = self.ts[1] - self.ts[0]
        fgap = self.freqs[1] - self.freqs[0]
        tspan = self.ts[-1] - self.ts[0]
        fspan = self.freqs[-1] - self.freqs[0]

        if auto_transpose:
            self.sxx = self.sxx.T

        if self.xdata is None:
            self.sp.setImage(self.sxx) # set image on existing item instead?
            self.sp.setRect(QRectF(self.ts[0]-tgap/2, self.freqs[0]-fgap/2, tspan+tgap, fspan+fgap)) # Proper setting of the box boundaries
            cm2use = pg.colormap.getFromMatplotlib('viridis')
            self.sp.setLookupTable(cm2use.getLookupTable())
            
            self.spw.addItem(self.sp) # Must add it back because clears are done in setYData
            self.spw.setMouseEnabled(x=True,y=False)


    @Slot()
    def onLinearRegionBtnClicked(self):
        if self.linearRegion is None: # Then make it and add it
            start = float(self.linearRegionStartEdit.text())
            end = float(self.linearRegionEndEdit.text())

            if end > start:
                # Then create the region object
                self.linearRegion = pg.LinearRegionItem(values=(start,end))
                # Add to the current plots?
                self.p.addItem(self.linearRegion)
                # Connect to slot for updates
                self.linearRegion.sigRegionChanged.connect(self.onRegionChanged)
        
        else: # Otherwise remove it and delete it
            self.p.removeItem(self.linearRegion)
            self.linearRegion = None
            # Reset the text
            self.linearRegionStartEdit.setText("")
            self.linearRegionEndEdit.setText("")

    @Slot()
    def onRegionChanged(self):
        region = self.linearRegion.getRegion()
        self.linearRegionStartEdit.setText(str(region[0]))
        self.linearRegionEndEdit.setText(str(region[1]))

