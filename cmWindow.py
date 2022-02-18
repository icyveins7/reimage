from PySide6.QtWidgets import QMainWindow, QVBoxLayout, QHBoxLayout, QWidget, QLabel, QComboBox
from PySide6.QtWidgets import QFormLayout, QLineEdit, QCheckBox, QPushButton
from PySide6.QtCore import Qt, Signal, Slot, QRectF
import pyqtgraph as pg
import numpy as np
import scipy.signal as sps
from dsp import *

class EstimateFreqWindow(QMainWindow):
    def __init__(self, slicedData=None, startIdx=None, endIdx=None, fs=1.0):
        super().__init__()

        # Attaching data
        self.slicedData = slicedData
        self.fs = fs

        # Aesthetics..
        self.setWindowTitle("Carrier Offset Estimation")

        # Main layout
        widget = QWidget()
        self.layout = QHBoxLayout()
        widget.setLayout(self.layout)
        self.setCentralWidget(widget)

        # Left FFT Plot
        self.fftwidget = pg.GraphicsLayoutWidget()
        self.fftplot = self.fftwidget.addPlot()
        self.fftplotItem = pg.PlotDataItem()
        self.fftplot.addItem(self.fftplotItem)
        self.layout.addWidget(self.fftwidget)
        # Freq selection region
        self.cztRegion = pg.LinearRegionItem(values=(-0.25*fs,0.25*fs))
        # Add to the current plots?
        self.fftplot.addItem(self.cztRegion)

        # Centre Control Panel
        self.ctrlLayout = QVBoxLayout()

        # Control Panel Form
        self.formLayout = QFormLayout()
        self.orderDropdown = QComboBox()
        self.orderDropdown.addItems([str(2**i) for i in range(1,4)])
        self.formLayout.addRow("Order", self.orderDropdown)
        
        self.resEdit = QLineEdit(str(self.fs/self.slicedData.size))
        self.resEdit.setEnabled(False)
        self.formLayout.addRow("Original Resolution (Hz)", self.resEdit)

        self.cresEdit = QLineEdit("0.1")
        self.formLayout.addRow("Zoomed Resolution (Hz)", self.cresEdit)

        self.ctrlLayout.addLayout(self.formLayout)
        self.zoomBtn = QPushButton("Zoom FFT Plot ->")
        self.ctrlLayout.addWidget(self.zoomBtn)

        self.layout.addLayout(self.ctrlLayout)

        # Right CZT Plot
        self.cztwidget = pg.GraphicsLayoutWidget()
        self.cztplot = self.cztwidget.addPlot()
        self.cztplotItem = pg.PlotDataItem()
        self.cztplot.addItem(self.cztplotItem)
        self.layout.addWidget(self.cztwidget)
        
        # Initialize FFT plot
        self.odata = None # Some placeholders
        self.f = None
        self.ffreq = None 
        self.replotFFT()

        # Link order changes to replot
        self.orderDropdown.currentTextChanged.connect(self.replotFFT)

        # Link button for czt plot
        self.zoomBtn.clicked.connect(self.replotCZT)

    @Slot()
    def replotFFT(self):
        self.odata = self.calculateCM()
        self.f = np.fft.fft(self.odata)
        self.ffreq = np.fft.fftfreq(self.odata.size, 1/self.fs)
        self.fftplotItem.setData(
            np.fft.fftshift(self.ffreq),
            np.fft.fftshift(20*np.log10(np.abs(self.f))))
        # TODO: fix wrong X and Y ranges when replotting (should auto focus)

    def calculateCM(self):
        return self.slicedData ** int(self.orderDropdown.currentText())

    @Slot()
    def replotCZT(self):
        # Retrieve the freq region
        region = self.cztRegion.getRegion()
        startFreq = region[0]
        cztRes = float(self.cresEdit.text())
        numPts = int((region[1] - startFreq) / cztRes) # Estimate number of czt points
        czt = self.calculateCztCM(self.slicedData, numPts, startFreq, cztRes)
        cztfreq = np.arange(numPts) * cztRes + startFreq
        # Now plot it
        self.cztplotItem.setData(
            cztfreq, 20*np.log10(np.abs(czt))
        )


    def calculateCztCM(self, data, numPts, startFreq, cztRes):
        order = int(self.orderDropdown.currentText())
        w = np.exp(-1j*2*np.pi*cztRes/data.size)
        a = np.exp(1j*2*np.pi*startFreq/data.size)
        czt = sps.czt(data**order, numPts, w, a)
        # cztfreq = sps.czt_points(numPts, w, a) # not working as expected
        
        return czt
