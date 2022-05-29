from PySide6.QtWidgets import QMainWindow, QVBoxLayout, QHBoxLayout, QWidget, QLabel, QComboBox
from PySide6.QtWidgets import QPushButton, QSlider
from PySide6.QtCore import Qt, Signal, Slot, QRectF
import pyqtgraph as pg
import numpy as np
import scipy.signal as sps

class AudioWindow(QMainWindow):
    def __init__(self, slicedData=None, startIdx=None, endIdx=None, fs=1.0):
        super().__init__()

        # Attaching data
        self.slicedData = slicedData
        self.fs = fs

        # Aesthetics..
        self.setWindowTitle("Audio Manipulation")

        # Main layout
        widget = QWidget()
        self.layout = QVBoxLayout()
        widget.setLayout(self.layout)
        self.setCentralWidget(widget)

        # Playback controls layout
        self.playbackLayout = QHBoxLayout()
        self.layout.addLayout(self.playbackLayout)

        # Add some playback controls
        self.playBtn = QPushButton("Play")
        self.pauseBtn = QPushButton("Pause")
        self.resetBtn = QPushButton("Reset")
        self.playbackLayout.addWidget(self.playBtn)
        self.playbackLayout.addWidget(self.pauseBtn)
        self.playbackLayout.addWidget(self.resetBtn)

        # Add the top and bottom plots
        self.plotLayout = QHBoxLayout()
        self.plotWidget = pg.GraphicsLayoutWidget()
        self.topPlot = self.plotWidget.addPlot(row=0,col=0)
        self.btmPlot = self.plotWidget.addPlot(row=1,col=0)
        self.plotLayout.addWidget(self.plotWidget)
        self.freqSlider = QSlider(Qt.Vertical)
        self.plotLayout.addWidget(self.freqSlider)
        self.layout.addLayout(self.plotLayout)
        
        # if startIdx is not None and endIdx is not None:
        #     self.p.setLabels(title="Sample %d to %d" % (startIdx, endIdx))
        # self.plt = pg.PlotDataItem()
        # self.p.addItem(self.plt)
        
        # # Create the options
        # self.fftlenLayout = QHBoxLayout()
        # self.fftlenLabel = QLabel("FFT Length: ")
        # self.fftlenLayout.addWidget(self.fftlenLabel)
        # self.setupFFTDropdown()
        # self.layout.addLayout(self.fftlenLayout)

        # # Plot the data
        # self.plot()
