from PySide6.QtWidgets import QFrame, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, QLineEdit, QApplication, QMenu
from PySide6.QtCore import Qt, Signal, Slot, QRectF
import pyqtgraph as pg
import numpy as np
import scipy.signal as sps

from fftWindow import FFTWindow

class SignalView(QFrame):
    def __init__(self, ydata, parent=None, f=Qt.WindowFlags()):
        super().__init__(parent, f)

        # Formatting
        self.setMinimumWidth(800)

        # Attach the data (hopefully this doesn't copy)
        self.ydata = ydata

        # Placeholder for xdata
        self.xdata = None
        self.fs = None
        self.startTime = None
        
        # Placeholder for downsample rates
        self.dsrs = []
        self.dscache = []
        self.curDsrIdx = -1
        self.setDownsampleCache()

        # Placeholder for spectrogram data
        self.freqs = None
        self.ts = None
        self.sxx = None

        # Create a graphics view
        self.glw = pg.GraphicsLayoutWidget() # Window for the amplitude time plot
        self.p1 = self.glw.addPlot(row=0,col=0) # The amp-time plotItem
        self.p = None # Placeholder for the absolute time PlotDataItem
        self.sp = pg.ImageItem()
        self.spw = self.glw.addPlot(row=1,col=0)
        self.spw.addItem(self.sp)

        # Connections for the plots
        self.p1proxy = pg.SignalProxy(self.p1.scene().sigMouseMoved, rateLimit=60, slot=self.ampMouseMoved)
        self.spwproxy = pg.SignalProxy(self.spw.scene().sigMouseMoved, rateLimit=60, slot=self.specMouseMoved)

        # Create a layout for linear region
        self.linearRegionInputLayout = QHBoxLayout()
        self.linearRegionStartEdit = QLineEdit()
        self.linearRegionEndEdit = QLineEdit()
        self.linearRegionColon = QLabel(":")
        self.linearRegionBtn = QPushButton("Add/Remove Time Slice")
        self.linearRegionBtn.clicked.connect(self.onLinearRegionBtnClicked)
        self.linearRegionStartEdit.editingFinished.connect(self.onStartEdited)
        self.linearRegionEndEdit.editingFinished.connect(self.onEndEdited)
        self.linearRegionInputLayout.addWidget(self.linearRegionStartEdit)
        self.linearRegionInputLayout.addWidget(self.linearRegionColon)
        self.linearRegionInputLayout.addWidget(self.linearRegionEndEdit)
        self.linearRegionInputLayout.addWidget(self.linearRegionBtn)

        # Corresponding labels for linear region
        self.linearRegionLabelsLayout = QHBoxLayout()
        self.linearRegionBoundsLabel = QLabel()
        self.linearRegionLabelsLayout.addWidget(self.linearRegionBoundsLabel)

        # Placeholders for linear regions 
        self.linearRegion = None # TODO: make ctrl-click add it instead of via button?

        # ViewBox statistics
        self.viewboxLabelsLayout = QHBoxLayout()
        self.viewboxlabel = QLabel()
        self.viewboxLabelsLayout.addWidget(self.viewboxlabel)
        self.ampCoordLabel = QLabel()
        self.viewboxLabelsLayout.addWidget(self.ampCoordLabel)
        self.specCoordLabel = QLabel()
        self.viewboxLabelsLayout.addWidget(self.specCoordLabel)
        self.p1.sigRangeChanged.connect(self.onZoom)

        # Create the main layout
        self.layout = QVBoxLayout()
        self.layout.addLayout(self.linearRegionInputLayout)
        self.layout.addLayout(self.linearRegionLabelsLayout)
        self.layout.addLayout(self.viewboxLabelsLayout)
        self.layout.addWidget(self.glw)

        self.setLayout(self.layout)


    def setDownsampleCache(self):
        # Clear existing cache
        self.dscache = []
        self.dsrs = []
        # We cache the original sample rate to use as the bootstrap
        self.dscache.append(np.abs(self.ydata))
        self.dsrs.append(1)

        cursize = self.ydata.size
        while cursize > 1e5: # Recursively downsample in orders of magnitude
            self.dscache.append(self.dscache[-1][::10])
            self.dsrs.append(self.dsrs[-1]*10)
            cursize = self.dscache[-1].size
        
        print(self.dscache)
        print(self.dsrs)

    def setXData(self, fs, startTime=0):
        self.fs = fs
        self.startTime = startTime
        self.xdata = (np.arange(self.ydata.size) * 1/self.fs) + self.startTime

    def setYData(self, ydata):
        self.p1.clear()
        self.spw.clear()
        self.ydata = ydata

        self.setDownsampleCache()
        self.plotAmpTime()
        self.plotSpecgram()

        # Equalize the widths of the y-axis?
        self.p1.getAxis('left').setWidth(30) # Hardcoded for now
        self.spw.getAxis('left').setWidth(30) # TODO: evaluate maximum y values in both graphs, then set an appropriate value

        # Link axes
        self.p1.setXLink(self.spw)

    def plotAmpTime(self):
        # Create and save the PlotDataItems as self.p
        if self.xdata is None:
            # self.p.plot(np.abs(self.ydata), downsample=100, autoDownsample=True, downsampleMethod='subsample') # TODO: figure out whether these options do anything?
            self.p = self.p1.plot(np.arange(0,self.ydata.size,self.dsrs[-1]), self.dscache[-1])
            self.p.setClipToView(True) # the plot function doesn't set the clipToView keyword correctly, but it works on the PlotDataItem returned
        else:
            self.p = self.p1.plot(self.xdata, np.abs(self.ydata))
            self.p.setClipToView(True)
        self.p1.setMouseEnabled(x=True,y=False)
        self.p1.setMenuEnabled(False)
        viewBufferX = 0.1 * self.ydata.size # TODO: adjust based on xdata as well
        self.p1.setLimits(xMin = -viewBufferX, xMax = self.ydata.size + viewBufferX) # TODO: adjust based on xdata next time
        self.curDsrIdx = -1 # On init, the maximum dsr is used
            
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
            self.spw.setMenuEnabled(False)

            viewBufferX = 0.1 * self.ydata.size # TODO: adjust based on xdata as well
            self.spw.setLimits(xMin = -viewBufferX, xMax = self.ydata.size + viewBufferX) # TODO: adjust based on xdata next time


    @Slot()
    def onLinearRegionBtnClicked(self):
        if self.linearRegion is None: # Then make it and add it
            start = float(self.linearRegionStartEdit.text())
            end = float(self.linearRegionEndEdit.text())

            # Clear the edits
            self.linearRegionStartEdit.clear()
            self.linearRegionEndEdit.clear()

            if end > start:
                # Then create the region object
                self.linearRegion = pg.LinearRegionItem(values=(start,end))
                # Add to the current plots?
                self.p1.addItem(self.linearRegion)
                # Connect to slot for updates
                self.linearRegion.sigRegionChanged.connect(self.onRegionChanged)
                # Set the initial labels
                self.linearRegionBoundsLabel.setText("%f : %f" % (start,end))
        
        else: # Otherwise remove it and delete it
            self.p1.removeItem(self.linearRegion)
            self.linearRegion = None
            # Reset the text
            self.linearRegionStartEdit.setText("")
            self.linearRegionEndEdit.setText("")
            self.linearRegionBoundsLabel.clear()

    @Slot()
    def onRegionChanged(self):
        region = self.linearRegion.getRegion()
        self.linearRegionBoundsLabel.setText("%f : %f" % (region[0], region[1]))

    @Slot()
    def onStartEdited(self):
        if self.linearRegion is not None:
            region = self.linearRegion.getRegion()
            self.linearRegion.setRegion((float(self.linearRegionStartEdit.text()), region[1]))
            self.linearRegionStartEdit.clear()

    @Slot()
    def onEndEdited(self):
        if self.linearRegion is not None:
            region = self.linearRegion.getRegion()
            self.linearRegion.setRegion((region[0], float(self.linearRegionEndEdit.text())))
            self.linearRegionEndEdit.clear()

    @Slot()
    def onZoom(self):
        xstart = self.p1.viewRange()[0][0]
        xend = self.p1.viewRange()[0][1]
        self.viewboxlabel.setText("Zoom Downsample Rate: %5d / %5d (Max)" % (self.dsrs[self.curDsrIdx], self.dsrs[-1]))
        
        # Count how many points are in range
        numPtsInRange = (xend-xstart)
        targetDSR = 10**(np.floor(np.log10(numPtsInRange)) - 4)
        # print("curDsr = %d" % (self.dsrs[self.curDsrIdx]))
        # print("targetDSR = %d" % (targetDSR))
        # print("%d points in range" % numPtsInRange)
        if targetDSR < self.dsrs[self.curDsrIdx]: # If few points, zoom in i.e. lower the DSR
            if len(self.dsrs) + self.curDsrIdx > 0: # But only lower to the DSR of 1
                self.curDsrIdx = self.curDsrIdx - 1
                # Set the zoomed data on the PlotDataItem
                dsr = self.dsrs[self.curDsrIdx]
                self.p.setData(np.arange(0,self.ydata.size,dsr), self.dscache[self.curDsrIdx], clipToView=True) # setting clipToView on the plotdataitem works directly
        
        if targetDSR > self.dsrs[self.curDsrIdx]: # If too many points, zoom out i.e. increase the DSR
            if self.curDsrIdx < -1:
                self.curDsrIdx = self.curDsrIdx + 1
                # Set the zoomed data on the PlotDataItem
                dsr = self.dsrs[self.curDsrIdx]
                self.p.setData(np.arange(0,self.ydata.size,dsr), self.dscache[self.curDsrIdx], clipToView=True)

        # TODO: rightclick 'view all' bug: does not zoom out completely?

    def ampMouseMoved(self, evt):
        mousePoint = self.p1.vb.mapSceneToView(evt[0])
        self.ampCoordLabel.setText("Top: %f, %f" % (mousePoint.x(), mousePoint.y()))

    def specMouseMoved(self, evt):
        mousePoint = self.spw.vb.mapSceneToView(evt[0])
        self.specCoordLabel.setText("Bottom: %f, %f" % (mousePoint.x(), mousePoint.y()))

    # # Override default key press
    # def keyPressEvent(self, event):
    #     super().keyPressEvent(event)
    #     print("Custom slot")

    # Override default mouse press
    def mousePressEvent(self, event):
        modifiers = QApplication.keyboardModifiers()
        if event.button() == Qt.LeftButton and bool(modifiers == Qt.ControlModifier):
            print("Ctrl-leftclicked, implement the marking here")
        else:
            super().mousePressEvent(event)

    # Override default context menu # TODO: move this to the graphics layout widget subclass instead, so we dont get to rclick outside the plots
    def contextMenuEvent(self, event):
        modifiers = QApplication.keyboardModifiers()
        if bool(modifiers == Qt.ControlModifier): # Going to leave it as control-modifier, in case we want the pyqtgraph default menu back later on
            menu = QMenu()
            fftAction = menu.addAction("FFT Time Slice")
            action = menu.exec_(self.mapToGlobal(event.pos()))
            if action == fftAction:
                if self.linearRegion is None: # Use all the data
                    self.fftwin = FFTWindow(self.ydata)
                    self.fftwin.show()
                else: # Slice only that region
                    region = self.linearRegion.getRegion()
                    startIdx = int(region[0])
                    endIdx = int(region[1])
                    self.fftwin = FFTWindow(self.ydata[startIdx:endIdx], startIdx, endIdx)
                    self.fftwin.show()
                

