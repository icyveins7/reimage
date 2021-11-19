from PySide6.QtWidgets import QFrame, QVBoxLayout, QHBoxLayout, QPushButton
from PySide6.QtCore import Qt, Signal, Slot
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
        # self.btnLayout = QHBoxLayout()
        # self.specgramBtn = QPushButton("Show Spectrogram")
        # self.specgramBtn.clicked.connect(self.onShowSpecgramBtnClicked)
        # self.btnLayout.addWidget(self.specgramBtn)

        # Create the main layout
        self.layout = QVBoxLayout()
        # self.layout.addLayout(self.btnLayout)
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
        if auto_transpose:
            self.sxx = self.sxx.T

        if self.xdata is None:
            self.sp.setImage(self.sxx) # set image on existing item instead?
            cm2use = pg.colormap.getFromMatplotlib('viridis')
            self.sp.setLookupTable(cm2use.getLookupTable())
            
            self.spw.addItem(self.sp) # Must add it back because clears are done in setYData
            self.spw.setMouseEnabled(x=True,y=False)


    # @Slot()
    # def onShowSpecgramBtnClicked(self):
    #     if not self.spShown:
    #         self.plotSpecgram(fs=1.0, window=('tukey',0.25), nperseg=None, noverlap=None, nfft=None) # TODO: link options to dialog?
    #         self.spw.show()
    #         self.spShown = True
    #     else: # TODO: weird bug where hide/show multiple times causes size of specgram to take less height
    #         self.spw.hide()
    #         self.spShown = False

