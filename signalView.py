from PySide6.QtWidgets import QFrame, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, QLineEdit, QApplication, QMenu, QInputDialog, QMessageBox
from PySide6.QtCore import Qt, Signal, Slot, QRectF
import pyqtgraph as pg
import numpy as np
import scipy.signal as sps

from fftWindow import FFTWindow
from markerdb import MarkerDB

class SignalView(QFrame):
    def __init__(self, ydata, filelist=None, sampleStarts=None, parent=None, f=Qt.WindowFlags()):
        super().__init__(parent, f)

        # Formatting
        self.setMinimumWidth(800)

        # Markers Database
        self.markerdb = MarkerDB()

        # Attach the data (hopefully this doesn't copy)
        self.ydata = ydata

        # Placeholders for file list tracking (for markers)
        self.filelist = filelist
        self.sampleStarts = sampleStarts

        # Placeholder for xdata
        self.xdata = None
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
        self.markerproxy = pg.SignalProxy(self.p1.scene().sigMouseClicked, rateLimit=60, slot=self.onAmpMouseClicked)

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

        # DSP Settings
        self.nperseg = 256
        self.noverlap = 256/8
        self.fs = 1
        self.freqshift = None
        self.numTaps = None
        self.filtercutoff = None
        self.dsr = None


    def setDownsampleCache(self):
        # Clear existing cache
        self.dscache = []
        self.dsrs = [] # Note that this is the cached downsample values, unlike self.dsr (the pre-processing value)
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

    def loadMarkers(self):
        sfilepaths, samplestarts, labels = self.markerdb.getMarkers(self.filelist)

        loadedsamples = []
        loadedlabels = []
        for i in range(len(sfilepaths)):
            si = self.filelist.index(sfilepaths[i])
            loadedsamples.append(samplestarts[i] + self.sampleStarts[si]) # offset by the file samples
            loadedlabels.append(labels[i])
        
        # Add the lines
        self.addMarkerLines(loadedsamples, loadedlabels)

    def getTimevec(self, curDSR):
        return np.arange(0, self.ydata.size, curDSR) / self.fs

    def setYData(self, ydata, filelist, sampleStarts):
        self.p1.clear()
        self.spw.clear()
        self.ydata = ydata

        # Apply initial processing
        if self.freqshift is not None:
            print("Initial freqshift..")
            tone = np.exp(1j*2*np.pi*self.freqshift*np.arange(ydata.size)/self.fs)
            self.ydata = self.ydata * tone
        
        if self.numTaps is not None:
            print("Initial filter..")
            taps = sps.firwin(self.numTaps, self.filtercutoff/self.fs)
            self.ydata = sps.lfilter(taps,1,self.ydata)

        if self.dsr is not None:
            self.ydata = self.ydata[::self.dsr]
            # After performing the downsample, we correct the fs value
            self.fs = self.fs / self.dsr
            self.dsr = None # Set it to None so we don't get confused
        
        self.filelist = filelist
        self.sampleStarts = sampleStarts

        self.loadMarkers()

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
        timevec = self.getTimevec(self.dsrs[-1])
        self.p = self.p1.plot(timevec, self.dscache[-1])
        self.p.setClipToView(True)

        self.p1.setMouseEnabled(x=True,y=False)
        self.p1.setMenuEnabled(False)
        viewBufferX = 0.1 * self.ydata.size / self.fs 
        self.p1.setLimits(xMin = -viewBufferX, xMax = self.ydata.size / self.fs + viewBufferX)
        self.curDsrIdx = -1 # On init, the maximum dsr is used
            
    def plotSpecgram(self, fs=1.0, window=('tukey',0.25), nperseg=None, noverlap=None, nfft=None, auto_transpose=True):
        # self.fs = fs

        # self.freqs, self.ts, self.sxx = sps.spectrogram(self.ydata, fs, window, nperseg, noverlap, nfft, return_onesided=False)
        self.freqs, self.ts, self.sxx = sps.spectrogram(
            self.ydata, self.fs, window, self.nperseg, self.noverlap, self.nperseg, return_onesided=False)

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

            viewBufferX = 0.1 * self.ydata.size/self.fs
            self.spw.setLimits(xMin = -viewBufferX, xMax = self.ydata.size/self.fs + viewBufferX)


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

        if targetDSR < self.dsrs[self.curDsrIdx]: # If few points, zoom in i.e. lower the DSR
            if len(self.dsrs) + self.curDsrIdx > 0: # But only lower to the DSR of 1
                self.curDsrIdx = self.curDsrIdx - 1
                # Set the zoomed data on the PlotDataItem
                dsr = self.dsrs[self.curDsrIdx]
                self.p.setData(self.getTimevec(dsr), self.dscache[self.curDsrIdx], clipToView=True) # setting clipToView on the plotdataitem works directly
        
        if targetDSR > self.dsrs[self.curDsrIdx]: # If too many points, zoom out i.e. increase the DSR
            if self.curDsrIdx < -1:
                self.curDsrIdx = self.curDsrIdx + 1
                # Set the zoomed data on the PlotDataItem
                dsr = self.dsrs[self.curDsrIdx]
                self.p.setData(self.getTimevec(dsr), self.dscache[self.curDsrIdx], clipToView=True)

        # TODO: rightclick 'view all' bug: does not zoom out completely?

    def ampMouseMoved(self, evt):
        mousePoint = self.p1.vb.mapSceneToView(evt[0])
        self.ampCoordLabel.setText("Top: %f, %f" % (mousePoint.x(), mousePoint.y()))

    def specMouseMoved(self, evt):
        mousePoint = self.spw.vb.mapSceneToView(evt[0])
        self.specCoordLabel.setText("Bottom: %f, %f" % (mousePoint.x(), mousePoint.y()))

    def onAmpMouseClicked(self, evt):
        # print(evt[0].button())
        modifiers = QApplication.keyboardModifiers()
        if modifiers == Qt.ControlModifier | Qt.AltModifier:
            print("Reserved for future use")

        elif modifiers == Qt.ControlModifier and Qt.MouseButton.LeftButton == evt[0].button():
            mousePoint = self.p1.vb.mapToView(evt[0].pos()) # use mapToView instead of mapSceneToView here, not sure why..
            # Start a dialog for the label
            label, ok = QInputDialog.getText(self,
                                        "Add Marker Label",
                                        "Marker Label:",
                                        QLineEdit.Normal,
                                        "%f, %f" % (mousePoint.x(), mousePoint.y()))
            if ok and label:
                # Decide which filepath to pair this marker with
                print(self.sampleStarts)
                print(self.filelist)

                dbfilepath, dbsamplestart = self.getFileSamplePair(mousePoint.x())

                # Check if this marker has been saved before
                blist = self.markerdb.checkMarkers([dbfilepath], [dbsamplestart])
                if blist[0] == True:
                    # Raise dialog to say already exists
                    QMessageBox.warning(self,
                                        "Marker Error",
                                        "Marker already exists at this position!",
                                        QMessageBox.Ok)

                else: # Add the marker
                    self.addMarkerLines([mousePoint.x()], [label])
                    print("Saving with %s, %f" % (dbfilepath, dbsamplestart))
                    self.markerdb.addMarkers([dbfilepath], [dbsamplestart], [label])
                    

    def getFileSamplePair(self, x):
        for i in range(len(self.sampleStarts)):
            dbsamplestart = self.sampleStarts[i] - x
            if dbsamplestart > 0:
                dbfilepath = self.filelist[i-1] # this is offset by 1
                dbsamplestart = x - self.sampleStarts[i-1] # revert to positive value
                break
        
        return dbfilepath, dbsamplestart

    def addMarkerLines(self, xvalues, labels):
        for i in range(len(xvalues)):
            infline = pg.InfiniteLine(xvalues[i], label=labels[i], labelOpts={'position': 0.95}) # don't put 1.0, gets chopped off   
            infline.sigClicked.connect(self.onMarkerLineClicked)
            self.p1.addItem(infline)

    @Slot(pg.InfiniteLine)
    def onMarkerLineClicked(self, event: pg.InfiniteLine):
        # Note that event here is actually the infiniteLine object
        label = event.label.format # This should be the label
        modifiers = QApplication.keyboardModifiers()
        if bool(modifiers == Qt.ShiftModifier):
            # Shift-click to delete, but raise dialog
            r = QMessageBox.question(self,
                                    "Delete Marker",
                                    "Delete marker with label: '%s'?" % (label))
            
            if r == QMessageBox.StandardButton.Yes:
                # Get the file for this marker
                dbfilepath, dbsamplestart = self.getFileSamplePair(event.p[0])
                # Remove from db
                self.markerdb.delMarkers([dbfilepath], [dbsamplestart])
                # Remove from the plot
                self.p1.removeItem(event)
                

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
                

