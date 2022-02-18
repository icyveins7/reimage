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
        self.fftplot.setMouseEnabled(x=True, y=False)
        self.fftplotItem = pg.PlotDataItem()
        self.fftplot.addItem(self.fftplotItem)
        self.layout.addWidget(self.fftwidget)

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
        self.zoomBtn = QPushButton("Zoom FFT Plot")
        self.ctrlLayout.addWidget(self.zoomBtn)

        self.layout.addLayout(self.ctrlLayout)

        # CZT Plot Item
        self.cztplotItem = pg.PlotDataItem(pen='r')
        self.fftplot.addItem(self.cztplotItem)
        
        # Initialize FFT plot
        self.odata = None # Some placeholders
        self.f = None
        self.ffreq =  np.fft.fftfreq(self.slicedData.size, 1/self.fs)
        self.replotFFT()

        # Link order changes to replot
        self.orderDropdown.currentTextChanged.connect(self.replotFFT)

        # Link button for czt plot
        self.zoomBtn.clicked.connect(self.replotCZT)

        # TODO: add options for manual zoom viewbox setting for exact CZT freq windows

    @Slot()
    def replotFFT(self):
        self.odata = self.calculateCM()
        self.f = np.fft.fft(self.odata)
        
        self.fftplotItem.setData(
            np.fft.fftshift(self.ffreq),
            np.fft.fftshift(20*np.log10(np.abs(self.f))))
        # TODO: fix wrong X and Y ranges when replotting (should auto focus)

    def calculateCM(self):
        return self.slicedData ** int(self.orderDropdown.currentText())

    @Slot()
    def replotCZT(self):
        # Retrieve the freq region from current viewbox
        xviewrange = self.fftplot.viewRange()[0]
        cztRes = float(self.cresEdit.text())
        numPts = int((xviewrange[1] - xviewrange[0]) / cztRes + 1) # Estimate number of czt points
        czt = self.calculateCztCM(numPts, xviewrange[0], xviewrange[1], cztRes)
        cztfreq = np.arange(numPts) * cztRes + xviewrange[0]
        # Now plot it
        self.cztplotItem.setData(
            cztfreq, 20*np.log10(np.abs(czt))
        )


    def calculateCztCM(self, numPts, startFreq, endFreq, cztRes):
        w = np.exp(-1j*2*np.pi*(endFreq-startFreq+cztRes)/(numPts*self.fs))
        a = np.exp(1j*2*np.pi*startFreq/self.fs)
        czt = sps.czt(self.odata, numPts, w, a) # CM already calculated before CZT

        return czt
