from PySide6.QtWidgets import QMainWindow, QVBoxLayout, QHBoxLayout, QWidget, QLabel, QComboBox
from PySide6.QtWidgets import QFormLayout, QLineEdit, QCheckBox
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

        # Calculate plain fft
        self.datafft = np.fft.fft(self.slicedData, 65536) # TODO: make fft len variable

        # Aesthetics..
        self.setWindowTitle("Baud Rate Estimation")

        # Main layout
        widget = QWidget()
        self.layout = QHBoxLayout()
        widget.setLayout(self.layout)
        self.setCentralWidget(widget)

        # Add the plot widget
        self.glw = pg.GraphicsLayoutWidget()
        self.layout.addWidget(self.glw)
        self.p = self.glw.addPlot(row=0,col=0)
        if startIdx is not None and endIdx is not None:
            self.p.setLabels(title="Sample %d to %d" % (startIdx, endIdx))
        self.plt = pg.PlotDataItem()
        self.p.addItem(self.plt)
        
        # Create the options
        self.paramsLayout = QFormLayout()
        self.fsNonEdit = QLineEdit("%f" % (self.fs))
        self.fsNonEdit.setEnabled(False) # Disable edits
        self.paramsLayout.addRow("Sample rate:", self.fsNonEdit)
        self.prefilterCheckbox = QCheckBox()
        self.paramsLayout.addRow("Prefilter?", self.prefilterCheckbox)
        self.numTapsDropdown = QComboBox()
        self.numTapsDropdown.addItems(["%d" % (2**i) for i in range(6,15)])
        self.paramsLayout.addRow("Prefilter No. of Taps", self.numTapsDropdown)
        self.layout.addLayout(self.paramsLayout)

        # Plot the left (initial data fft) side first
        self.leftplot()
        
    def leftplot(self):
        self.plt.setData(
            np.fft.fftshift(makeFreq(self.datafft.size, self.fs)),
            np.fft.fftshift(20*np.log10(np.abs(self.datafft)))
        )