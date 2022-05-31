from PySide6.QtWidgets import QMainWindow, QVBoxLayout, QHBoxLayout, QWidget, QLabel, QComboBox
from PySide6.QtWidgets import QPushButton, QSlider
from PySide6.QtCore import Qt, Signal, Slot, QRectF
import pyqtgraph as pg
import numpy as np
import scipy.signal as sps
import sounddevice as sd

class AudioWindow(QMainWindow):
    def __init__(self, slicedData=None, startIdx=None, endIdx=None, fs=1.0):
        super().__init__()

        # Attaching data
        self.slicedData = slicedData
        self.fs = fs
        print(self.fs)

        # Pre-generate the FFT of the signal
        print("Pre-calcing FFT")
        self.dataFFT = np.fft.fft(self.slicedData)
        # And also the spectrogram form
        print("Pre-calcing specgram")
        self.fSpec, self.tSpec, self.dataSpec = sps.spectrogram(self.slicedData, self.fs)
        self.fSpec = np.fft.fftshift(self.fSpec)
        self.dataSpec = np.fft.fftshift(self.dataSpec, axes=0)
        self.dataSpec = self.dataSpec.T # auto-transpose

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
        self.playBtn.clicked.connect(self.play)
        self.pauseBtn.clicked.connect(self.pause)
        self.resetBtn.clicked.connect(self.reset)

        # Add the top and bottom plots
        self.plotLayout = QHBoxLayout()
        self.plotWidget = pg.GraphicsLayoutWidget()
        self.topPlot = self.plotWidget.addPlot(row=0,col=0)
        self.btmPlot = self.plotWidget.addPlot(row=1,col=0)
        self.plotLayout.addWidget(self.plotWidget)
        self.freqSlider = QSlider(Qt.Vertical)
        self.freqSlider.setTickPosition(QSlider.TicksRight)
        # self.freqSlider.valueChanged.connect(self.rollFreq) # TODO: need to use on release instead
        self.plotLayout.addWidget(self.freqSlider)
        self.layout.addLayout(self.plotLayout)
        self.topPlot.setXLink(self.btmPlot)
        self.topPlot.setMouseEnabled(x=True,y=False)
        self.topPlot.getAxis('left').setWidth(60) # Hardcoded for now
        self.btmPlot.getAxis('left').setWidth(60) # TODO: evaluate maximum y values in both graphs, then set an appropriate value


        # Add the image item
        self.btmImg = pg.ImageItem()
        self.btmPlot.addItem(self.btmImg)
        
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

        # Plot the data
        self.plot()

    def plot(self):
        # Plot just like in signalView, but no need to downsample
        self.topPlot.plot(np.arange(self.slicedData.size)/self.fs, self.slicedData) # and no need to abs
        self.btmImg.setImage(self.dataSpec)
        self.btmImg.setRect(QRectF(0.0, -self.fs/2, self.slicedData.size/self.fs, self.fs))
        cm2use = pg.colormap.getFromMatplotlib('viridis')
        self.btmImg.setLookupTable(cm2use.getLookupTable())

    #%% Frequency manipulation
    def rollFreq(self):
        print("TODO: roll frequency")
        pass

    #%% Playback controls
    def play(self):
        sd.play(self.slicedData, self.fs)

    def pause(self):
        sd.stop()

    def reset(self):
        pass

