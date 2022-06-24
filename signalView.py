from PySide6.QtWidgets import QFrame, QVBoxLayout, QHBoxLayout
from PySide6.QtWidgets import QPushButton, QLabel, QLineEdit, QApplication, QMenu, QInputDialog, QMessageBox, QSlider
from PySide6.QtCore import Qt, Signal, Slot, QRectF
import pyqtgraph as pg
import numpy as np
import scipy.signal as sps

from fftWindow import FFTWindow
from estBaudWindow import EstimateBaudWindow
from cmWindow import EstimateFreqWindow
from thresholdWindow import ThresholdWindow
from audioWindow import AudioWindow

from markerdb import MarkerDB

import time

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
        self.sxxMax = None # For image control
        self.specFreqRes = None
        self.specTimeRes = None # For spectrogram point-finding

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

        # Corresponding labels for linear region
        self.linearRegionLabelsLayout = QHBoxLayout()
        self.linearRegionBoundsLabel = QLabel()
        self.linearRegionLabelsLayout.addWidget(self.linearRegionBoundsLabel)

        # Placeholders for linear regions 
        self.linearRegion = None
        self.specLinearRegion = None # Replicate the region in both

        # ViewBox statistics
        self.viewboxLabelsLayout = QHBoxLayout()
        self.viewboxlabel = QLabel()
        self.viewboxLabelsLayout.addWidget(self.viewboxlabel)

        self.viewboxLabelsLayout.addStretch()
        self.xCoordLabel = QLabel()
        self.viewboxLabelsLayout.addWidget(self.xCoordLabel)
        self.ampCoordLabel = QLabel()
        self.viewboxLabelsLayout.addWidget(self.ampCoordLabel)
        self.specCoordLabel = QLabel()
        self.viewboxLabelsLayout.addWidget(self.specCoordLabel)
        self.p1.sigRangeChanged.connect(self.onZoom)

        # Create the main layout
        self.layout = QVBoxLayout()
        self.layout.addLayout(self.linearRegionLabelsLayout)
        self.layout.addLayout(self.viewboxLabelsLayout)
        self.layout.addWidget(self.glw)

        self.setLayout(self.layout)

        # Add a colour slider control
        self.contrastLayout = QHBoxLayout()
        self.contrastSlider = QSlider(Qt.Horizontal)
        self.contrastSlider.setRange(1, 100)
        self.contrastSlider.valueChanged.connect(self.changeSpecgramContrast)
        self.contrastLayout.addWidget(QLabel("Contrast"))
        self.contrastLayout.addWidget(self.contrastSlider)
        self.layout.addLayout(self.contrastLayout)

        # DSP Settings
        self.nperseg = 256
        self.noverlap = 256/8
        self.fs = 1
        self.freqshift = None
        self.numTaps = None
        self.filtercutoff = None
        self.dsr = None

    @Slot()
    def changeSpecgramContrast(self):
        if self.sxxMax is not None:
            percentile = self.contrastSlider.value()/100.0
            contrast = np.exp((percentile-1)/0.25) * self.sxxMax # like a log2 squared contrast, this is more natural
            self.sp.setLevels([0, contrast])
        

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
            normalizedSample = (samplestarts[i] + self.sampleStarts[si]) / self.fs  # offset by file
            print("normalized sample = %f " % (normalizedSample))
            loadedsamples.append(normalizedSample)
            loadedlabels.append(labels[i])
        
        # Add the lines
        self.addMarkerLines(loadedsamples, loadedlabels)

    def getDisplayedFs(self):
        # This is usually the fs value used in all functions, other than the preprocessing steps
        # and the marker values (which are normalised)
        return self.fs if self.dsr is None else self.fs/self.dsr

    def getTimevec(self, curDSR):
        dfs = self.getDisplayedFs()
        return np.arange(0, self.ydata.size, curDSR) / dfs

    def setYData(self, ydata, filelist, sampleStarts):
        self.p1.clear()
        self.spw.clear()
        self.ydata = ydata

        # Reset the contrast slider
        self.contrastSlider.setValue(100)

        # Apply initial processing
        if self.freqshift is not None:
            print("Initial freqshift..")
            t1 = time.time()
            tone = np.exp(1j*2*np.pi*self.freqshift*np.arange(ydata.size)/self.fs)
            t2 = time.time()
            self.ydata = self.ydata * tone
            print("Tone gen: %fs.\n" % (t2-t1))
        
        if self.numTaps is not None:
            print("Initial filter..")
            taps = sps.firwin(self.numTaps, self.filtercutoff/self.fs)
            t1 = time.time()
            self.ydata = sps.lfilter(taps,1,self.ydata)
            t2 = time.time()
            print("Filter: %fs.\n" % (t2-t1))

        if self.dsr is not None:
            self.ydata = self.ydata[::self.dsr]
            print("Using displayed fs %d" % (self.getDisplayedFs()))
        
        self.filelist = filelist
        self.sampleStarts = sampleStarts

        self.loadMarkers()

        self.setDownsampleCache()
        self.plotAmpTime()
        self.plotSpecgram()

        # Equalize the widths of the y-axis?
        self.p1.getAxis('left').setWidth(60) # Hardcoded for now
        self.spw.getAxis('left').setWidth(60) # TODO: evaluate maximum y values in both graphs, then set an appropriate value

        # Link axes
        self.p1.setXLink(self.spw)

    def plotAmpTime(self):
        # Create and save the PlotDataItems as self.p
        timevec = self.getTimevec(self.dsrs[-1])
        self.p = self.p1.plot(timevec, self.dscache[-1])
        self.p.setClipToView(True)

        self.p1.setMouseEnabled(x=True,y=False)
        self.p1.setMenuEnabled(False)

        dfs = self.getDisplayedFs()
        viewBufferX = 0.1 * self.ydata.size / dfs
        self.p1.setLimits(xMin = -viewBufferX, xMax = self.ydata.size / dfs + viewBufferX)
        self.curDsrIdx = -1 # On init, the maximum dsr is used
        self.p1.vb.setXRange(-viewBufferX, self.ydata.size/dfs + viewBufferX) # Set it to zoomed out at start
            
    def plotSpecgram(self, window=('tukey',0.25), auto_transpose=True):
        dfs = self.getDisplayedFs()
        # self.freqs, self.ts, self.sxx = sps.spectrogram(self.ydata, fs, window, nperseg, noverlap, nfft, return_onesided=False)
        self.freqs, self.ts, self.sxx = sps.spectrogram(
            self.ydata, dfs, window, self.nperseg, self.noverlap, self.nperseg, return_onesided=False)

        # Calculate resolutions for later
        self.specFreqRes = self.fs / self.nperseg
        # print(self.specFreqRes, self.freqs[1]-self.freqs[0]) # confirmed the same
        self.specTimeRes = self.ts[1] - self.ts[0]

        self.freqs = np.fft.fftshift(self.freqs)
        self.sxx = np.fft.fftshift(self.sxx, axes=0)
        self.sxxMax = np.max(self.sxx.flatten())
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
            # self.spw.setMouseEnabled(x=True,y=False)
            self.spw.setMenuEnabled(False)

            viewBufferX = 0.1 * self.ydata.size/dfs
            viewBufferY = 0.1 * fspan
            self.spw.setLimits(
                xMin = -viewBufferX, xMax = self.ydata.size/dfs + viewBufferX, 
                yMin = self.freqs[0] - viewBufferY, yMax = self.freqs[-1] + viewBufferY)
            self.spw.setYRange(self.freqs[0] - viewBufferY, self.freqs[-1] + viewBufferY) # Set to zoomed out by default
            self.spw.vb.setXRange(-viewBufferX, self.ydata.size/dfs + viewBufferX) # Set it to zoomed out at start, you must repeat this here, not just in the abs time widget, otherwise on increasing x plot lengths it will fail to zoom out

    @Slot()
    def createLinearRegions(self, start, end):
        if end > start:
            # Then create the region object
            self.linearRegion = pg.LinearRegionItem(values=(start,end))
            # Add to the current plots?
            self.p1.addItem(self.linearRegion)
            # Connect to slot for updates
            self.linearRegion.sigRegionChanged.connect(self.onAmpRegionChanged)
            # Set the initial labels
            self.linearRegionBoundsLabel.setText("%f : %f" % (start,end))

            # Create a similar region object for the specgram
            self.specLinearRegion = pg.LinearRegionItem(values=(start,end))
            self.spw.addItem(self.specLinearRegion)
            # Connect to slot for updates as well
            self.specLinearRegion.sigRegionChanged.connect(self.onSpecRegionChanged)
            
    @Slot()
    def deleteLinearRegions(self):
        self.p1.removeItem(self.linearRegion)
        self.spw.removeItem(self.specLinearRegion)
        self.linearRegion = None
        self.specLinearRegion = None
        # Reset the text
        self.linearRegionBoundsLabel.clear()

    @Slot()
    def onAmpRegionChanged(self):
        region = self.linearRegion.getRegion()
        self.linearRegionBoundsLabel.setText("%f : %f" % (region[0], region[1]))
        # Change the other region to match
        self.specLinearRegion.setRegion(region)


    @Slot()
    def onSpecRegionChanged(self):
        region = self.specLinearRegion.getRegion()
        self.linearRegionBoundsLabel.setText("%f : %f" % (region[0], region[1]))
        # Change the other region to match
        self.linearRegion.setRegion(region)

    @Slot()
    def onZoom(self):
        xstart = self.p1.viewRange()[0][0]
        xend = self.p1.viewRange()[0][1]
        self.viewboxlabel.setText("Zoom Downsample Rate: %5d / %5d (Max)" % (self.dsrs[self.curDsrIdx], self.dsrs[-1]))
        
        # Count how many points are in range
        dfs = self.getDisplayedFs()
        numPtsInRange = (xend-xstart) * dfs # Scale by the sample rate
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
        self.xCoordLabel.setText("X: %f" % (mousePoint.x()))
        self.ampCoordLabel.setText("Y (Top): %f" % (mousePoint.y()))

    def specMouseMoved(self, evt):
        mousePoint = self.spw.vb.mapSceneToView(evt[0])
        self.specCoordLabel.setText("Y (Bottom): %f" % (mousePoint.y()))
        # Attempt to find the nearest point
        # TODO: use resolutions to quickly find nearest point, then display spectrogram value

    def onAmpMouseClicked(self, evt):
        # print(evt[0].button())
        modifiers = QApplication.keyboardModifiers()
        if modifiers == Qt.ControlModifier | Qt.AltModifier:
            # Add Window ie LinearRegion
            if self.linearRegion is None:
                mousePoint = self.p1.vb.mapToView(evt[0].pos())
                start = mousePoint.x()
                # Get a rough estimate of the current zoom
                viewrange = self.p1.viewRange()[0]
                end = start + (viewrange[1] - viewrange[0]) / 10 # Just initialize with roughly 10%
                # Create the regions
                self.createLinearRegions(start,end)
            else:
                self.deleteLinearRegions()


        elif modifiers == Qt.ControlModifier and Qt.MouseButton.LeftButton == evt[0].button():
            # Add Marker
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

                scaled_x = mousePoint.x() * self.fs # Scale to the sample fs, (not displayed fs)
                dbfilepath, dbsamplestart = self.getFileSamplePair(scaled_x)

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
                dbfilepath, dbsamplestart = self.getFileSamplePair(event.p[0] * self.fs) # Scale to sample rate (not displayed fs)
                # Remove from db
                self.markerdb.delMarkers([dbfilepath], [dbsamplestart])
                # Remove from the plot
                self.p1.removeItem(event)
                

    # Override default context menu # TODO: move this to the graphics layout widget subclass instead, so we dont get to rclick outside the plots
    def contextMenuEvent(self, event):
        dfs = self.getDisplayedFs()

        modifiers = QApplication.keyboardModifiers()
        if bool(modifiers == Qt.ControlModifier): # Going to leave it as control-modifier, in case we want the pyqtgraph default menu back later on
            menu = QMenu()
            # Menu Entries
            # ===
            fftAction = menu.addAction("FFT Time Slice")
            # ===
            addSliceAction = menu.addAction("Add/Remove Time Window")
            # addSliceAction.setShortcut("Ctrl+Alt+Click") # This doesn't work
            # ===
            estBaudAction = menu.addAction("Estimate Baud Rate (Cyclostationary)")
            # ===
            estFreqAction = menu.addAction("Estimate Carrier Offset (Cyclostationary)")
            # ===
            energyDetectAction = menu.addAction("Detect Energy (Thresholding)")
            # ===
            audioAction = menu.addAction("Audio Manipulation")
            # ===
            demodSubmenu = menu.addMenu("Demodulate")
            pskdemodAction = demodSubmenu.addAction("PSK (TODO)")
            cpmdemodAction = demodSubmenu.addAction("CPM (TODO)")

            # Start the menu
            action = menu.exec_(self.mapToGlobal(event.pos()))
            if action == fftAction:
                if self.linearRegion is None: # Use all the data
                    self.fftwin = FFTWindow(self.ydata, fs=dfs)
                    self.fftwin.show()
                else: # Slice only that region
                    region = self.linearRegion.getRegion()
                    startIdx, endIdx = self.convertRegionToIndices(region)
                    self.fftwin = FFTWindow(self.ydata[startIdx:endIdx], startIdx, endIdx, dfs)
                    self.fftwin.show()

            elif action == addSliceAction:
                if self.linearRegion is None:
                    mousePoint = self.p1.vb.mapToView(event.pos()) # this is not exact, but doesn't matter
                    start = mousePoint.x()
                    # Get a rough estimate of the current zoom
                    viewrange = self.p1.viewRange()[0]
                    end = start + (viewrange[1] - viewrange[0]) / 10 # Just initialize with roughly 10%
                    # Create the regions
                    self.createLinearRegions(start,end)
                else:
                    self.deleteLinearRegions()

            elif action == estBaudAction:
                if self.linearRegion is None: # Use all the data
                    self.baudwin = EstimateBaudWindow(self.ydata, fs=dfs)
                    self.baudwin.show()
                else: # Slice that region
                    region = self.linearRegion.getRegion()
                    startIdx, endIdx = self.convertRegionToIndices(region)
                    self.baudwin = EstimateBaudWindow(self.ydata[startIdx:endIdx], startIdx, endIdx, fs=dfs)
                    self.baudwin.show()

            elif action == estFreqAction:
                if self.linearRegion is None:
                    self.freqwin = EstimateFreqWindow(self.ydata, fs=dfs)
                    self.freqwin.show()
                else:
                    region = self.linearRegion.getRegion()
                    startIdx, endIdx = self.convertRegionToIndices(region)
                    self.freqwin = EstimateFreqWindow(self.ydata[startIdx:endIdx], startIdx, endIdx, fs=dfs)
                    self.freqwin.show()

            elif action == energyDetectAction:
                self.threshwin = ThresholdWindow(self.freqs, self.ts, self.sxx, self)
                self.threshwin.show()

            elif action == audioAction:
                if self.linearRegion is None:
                    self.audiowin = AudioWindow(self.ydata, fs=dfs)
                    self.audiowin.show()
                else:
                    region = self.linearRegion.getRegion()
                    startIdx, endIdx = self.convertRegionToIndices(region)
                    self.audiowin = AudioWindow(self.ydata[startIdx:endIdx], startIdx, endIdx, fs=dfs)
                    slef.audiowin.show()

            elif action == pskdemodAction:
                print("TODO: PSK DEMODULATION") # TODO

            elif action == cpmdemodAction:
                print("TODO: CPM DEMODULATION") # TODO

    def convertRegionToIndices(self, region):
        dfs = self.getDisplayedFs()

        # First make sure it's clipped to the start/end of the data only
        rstart = region[0] if region[0] >=0 else 0
        rend = region[1] if region[1] < self.ydata.size/dfs else (self.ydata.size-1)/dfs

        startIdx = int(rstart*dfs)
        endIdx = int(rend*dfs)

        return startIdx, endIdx

