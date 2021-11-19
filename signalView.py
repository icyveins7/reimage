from PySide6.QtWidgets import QFrame, QVBoxLayout, QHBoxLayout, QPushButton
from PySide6.QtCore import Qt, Signal, Slot
import pyqtgraph as pg
import numpy as np
import scipy.signal as sps

class SignalView(QFrame):
    def __init__(self, ydata, parent=None, f=Qt.WindowFlags()):
        super().__init__(parent, f)

        # Create a graphics view
        self.glw = pg.GraphicsLayoutWidget() # Window for the amplitude time plot
        self.p = self.glw.addPlot(row=0,col=0) # The amp-time plotItem
        self.spw = pg.plot() # Window for the spectrogram
        self.sp = None # Placeholder for spectrogram image item
        self.spShown = False # Tracker for show/hide

        # Create some buttons for plot manipulations
        self.btnLayout = QHBoxLayout()
        self.specgramBtn = QPushButton("Show Spectrogram")
        self.specgramBtn.clicked.connect(self.onShowSpecgramBtnClicked)
        self.btnLayout.addWidget(self.specgramBtn)

        # Create the main layout
        self.layout = QVBoxLayout()
        self.layout.addLayout(self.btnLayout)
        self.layout.addWidget(self.glw)
        self.layout.addWidget(self.spw)
        self.spw.hide()
        self.setLayout(self.layout)

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

    def setXData(self, fs, startTime=0):
        self.fs = fs
        self.startTime = startTime
        self.xdata = (np.arange(self.ydata.size) * 1/self.fs) + self.startTime

    def setYData(self, ydata):
        self.ydata = ydata
        self.p.clear()
        self.p.plot(np.abs(self.ydata))

    def plotAmpTime(self):
        if self.xdata is None:
            self.p.plot(np.abs(self.ydata))
        else:
            self.p.plot(self.xdata, np.abs(self.ydata))
            
    def plotSpecgram(self, fs, window, nperseg, noverlap, nfft):
        self.fs = fs

        self.freqs, self.ts, self.sxx = sps.spectrogram(self.ydata, fs, window, nperseg, noverlap, nfft, return_onesided=False)

        if self.xdata is None:
            self.sp = pg.ImageItem(self.sxx)
            cm2use = pg.colormap.getFromMatplotlib('viridis')
            self.sp.setLookupTable(cm2use.getLookupTable())
            # Add to the plot
            self.spw.addItem(self.sp)
            # Show the plot in the layout
            self.spw.show()


    @Slot()
    def onShowSpecgramBtnClicked(self):
        if not self.spShown:
            self.plotSpecgram(fs=1.0, window=('tukey',0.25), nperseg=None, noverlap=None, nfft=None) # TODO: link options to dialog?
            self.spShown = True
        else:
            self.spw.hide()
            self.spShown = False

