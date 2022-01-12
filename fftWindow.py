from PySide6.QtWidgets import QMainWindow, QVBoxLayout, QHBoxLayout, QWidget, QLabel, QComboBox
from PySide6.QtCore import Qt, Signal, Slot, QRectF
import pyqtgraph as pg
import numpy as np
import scipy.signal as sps

from dsp import makeFreq

class FFTWindow(QMainWindow):
    def __init__(self, slicedData=None, startIdx=None, endIdx=None, fs=1.0):
        super().__init__()

        # Attaching data
        self.slicedData = slicedData
        self.fs = fs

        # Aesthetics..
        self.setWindowTitle("FFT Time Slice")

        # Main layout
        widget = QWidget()
        self.layout = QVBoxLayout()
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
        self.fftlenLayout = QHBoxLayout()
        self.fftlenLabel = QLabel("FFT Length: ")
        self.fftlenLayout.addWidget(self.fftlenLabel)
        self.setupFFTDropdown()
        self.layout.addLayout(self.fftlenLayout)

        # Plot the data
        self.plot()

    def setupFFTDropdown(self):
        self.fftlenDropdown = QComboBox()
        self.fftlenDropdown.addItems([str(i) for i in [1024,2048,4096,8192,16384,32768,65536]])
        self.fftlenLayout.addWidget(self.fftlenDropdown)
        self.fftlenDropdown.activated.connect(self.on_fftlen_selected)

    @Slot()
    def on_fftlen_selected(self):
        # Replot
        self.plot()

    def plot(self):
        f = np.fft.fft(self.slicedData, int(self.fftlenDropdown.currentText()))
        self.plt.setData(
            x=np.fft.fftshift(makeFreq(int(self.fftlenDropdown.currentText()), self.fs)),
            y=20*np.log10(np.abs(np.fft.fftshift(f))))