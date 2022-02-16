from PySide6.QtWidgets import QMainWindow, QVBoxLayout, QHBoxLayout, QWidget, QLabel, QComboBox
from PySide6.QtWidgets import QFormLayout, QLineEdit, QCheckBox, QPushButton
from PySide6.QtCore import Qt, Signal, Slot, QRectF
import pyqtgraph as pg
import numpy as np
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
        self.layout.addWidget(self.fftwidget)

        # Centre Control Panel
        self.ctrlLayout = QVBoxLayout()

        # Control Panel Form
        self.formLayout = QFormLayout()
        self.orderDropdown = QComboBox()
        self.orderDropdown.addItems([str(2**i) for i in range(1,4)])
        self.formLayout.addRow("Order", self.orderDropdown)
        self.ctrlLayout.addLayout(self.formLayout)
        self.zoomBtn = QPushButton("Zoom FFT Plot")
        self.ctrlLayout.addWidget(self.zoomBtn)

        self.layout.addLayout(self.ctrlLayout)

        # Right CZT Plot
        self.cztwidget = pg.GraphicsLayoutWidget()
        self.cztplot = self.cztwidget.addPlot()
        self.layout.addWidget(self.cztwidget)
        
        # Initialize FFT plot
        self.odata = None # Some placeholders
        self.f = None
        self.ffreq = None 
        self.replotFFT()

        # Link order changes to replot
        self.orderDropdown.currentTextChanged.connect(self.replotFFT)

    @Slot()
    def replotFFT(self):
        self.odata = self.calculateCM()
        self.f = np.fft.fft(self.odata)
        self.ffreq = np.fft.fftfreq(self.odata.size, self.fs/self.odata.size)
        self.fftplot.clear()
        self.fftplot.plot(
            np.fft.fftshift(self.ffreq),
            np.fft.fftshift(20*np.log10(np.abs(self.f))))
        # TODO: fix wrong X and Y ranges when replotting (should auto focus)

    def calculateCM(self):
        return self.slicedData ** int(self.orderDropdown.currentText())