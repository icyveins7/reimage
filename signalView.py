from PySide6.QtWidgets import QFrame, QVBoxLayout, QHBoxLayout
from PySide6.QtWidgets import QPushButton, QLabel, QLineEdit, QApplication, QMenu, QInputDialog, QMessageBox, QSlider
from PySide6.QtCore import Qt, Signal, Slot, QRectF, QEvent
import pyqtgraph as pg
import numpy as np
import scipy.signal as sps

from fftWindow import FFTWindow
from estBaudWindow import EstimateBaudWindow
from cmWindow import EstimateFreqWindow
from thresholdWindow import ThresholdWindow
from audioWindow import AudioWindow
from demodWindow import DemodWindow

from markerdb import MarkerDB

import time

class SignalView(QFrame):
    AMPL_PLOT = 0
    REIM_PLOT = 1
    SignalViewStatusTip = Signal(str)

    def __init__(self, ydata, filelist=None, sampleStarts=None, parent=None, f=Qt.WindowFlags()):
        super().__init__(parent, f)

        # Formatting
        self.setMinimumWidth(800)

        # Enable hover events, for status tips
        self.setAttribute(Qt.WA_Hover)

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
        self.pre = None # Placeholder for real plot
        self.pim = None # Placeholder for imag plot
        self.sp = pg.ImageItem()
        self.spw = self.glw.addPlot(row=1,col=0)
        self.spw.addItem(self.sp)
        self.spd = None # Placeholder for the dot used in tracking

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
        self.freqRegion = None # only need one for the specgram

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
        self.specPowerLabel = QLabel()
        self.viewboxLabelsLayout.addWidget(self.specPowerLabel)
        self.p1.sigRangeChanged.connect(self.onZoom)

        # Create the main layout
        self.layout = QVBoxLayout()
        self.layout.addLayout(self.linearRegionLabelsLayout)
        self.layout.addLayout(self.viewboxLabelsLayout)
        self.layout.addWidget(self.glw)

        self.setLayout(self.layout)

        # DSP Settings
        self.nperseg = 256
        self.noverlap = 256/8
        self.fs = 1
        self.fc = 0
        self.freqshift = None
        self.numTaps = None
        self.filtercutoff = None
        self.dsr = None

        # Placeholders for SMAs
        self.smas = {} # Save complex SMA
        self.smaplots = {}

        # Placeholders for plot types
        self.plotType = self.AMPL_PLOT # 0: amp, 1: reim

    @Slot(int)
    def addSma(self, length: int):
        taps = np.ones(length)/length
        sma = np.convolve(taps, np.abs(self.ydata), 'same')
        self.smas[length] = sma
        # Add to plot
        self.smaplots[length] = pg.PlotDataItem(
            np.arange(self.ydata.size) / self.fs,
            np.abs(sma),
            pen='r' # Default colour
        )
        self.p1.addItem(self.smaplots[length])
        

    @Slot(int)
    def delSma(self, length: int):
        # Delete from plot
        self.p1.removeItem(self.smaplots[length])
        # And from internal memory
        self.smaplots.pop(length)
        self.smas.pop(length)
        

    @Slot(int, int, int, int)
    def colourSma(self, length: int, r: int, g: int, b: int):
        self.smaplots[length].setPen(pg.mkPen(r,g,b))
        
    @Slot(float, bool)
    def adjustSpecgramContrast(self, percentile: float, isLog: bool):
        if self.sxxMax is not None:
            maxval = np.log10(self.sxxMax * percentile) if isLog else self.sxxMax * percentile
            minval = np.log10(self.sxxMin) if isLog else 0
            self.sp.setLevels([minval, maxval])

    @Slot(float)
    def adjustSpecgramLog(self, isLog: bool):
        if isLog and self.sxx is not None:
            self.sp.setImage(np.log10(self.sxx))
            self.sp.setLevels([
                np.log10(self.sxxMin),
                np.log10(self.sxxMax)])
        elif self.sxx is not None:
            self.sp.setImage(self.sxx)
            self.sp.setLevels([0, self.sxxMax])

    def setDownsampleCache(self):
        # Clear existing cache
        self.dscache = []
        self.dsrs = [] # Note that this is the cached downsample values, unlike self.dsr (the pre-processing value)
        # We cache the original sample rate to use as the bootstrap
        # self.dscache.append(np.abs(self.ydata)) # Cache amplitude directly?
        self.dscache.append(self.ydata) # Cache the original complex data
        self.dsrs.append(1)

        cursize = self.ydata.size
        while cursize > 1e5: # Recursively downsample in orders of magnitude
            self.dscache.append(self.dscache[-1][::10])
            self.dsrs.append(self.dsrs[-1]*10)
            cursize = self.dscache[-1].size
        
        # print(self.dscache)
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
        # Reset SMA plots
        self.smaplots.clear()
        self.smas.clear()

        self.p1.clear()
        self.spw.clear()
        self.ydata = ydata

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

    @Slot()
    def changeToAmpPlot(self):
        # Set the plot type
        self.plotType = self.AMPL_PLOT
        
        # First thing is to clear the reim plot
        self.p1.clear()

        # Then create the ampl one
        self.plotAmpTime()

        # Finally re-zoom to current axes
        # self.onZoom() # TODO: the previous call resets to the zoomed out version, can we keep the current limits?

    @Slot()
    def changeToReimPlot(self):
        # Set the plot type
        self.plotType = self.REIM_PLOT

        # First thing is to clear the amplitude plot
        self.p1.clear()

        # Then create the reim one
        self.plotReim()

        # Finally re-zoom to current axes
        # self.onZoom() # TODO: the previous call resets to the zoomed out version, can we keep the current limits?

    def plotAmpTime(self):
        # Create and save the PlotDataItems as self.p
        timevec = self.getTimevec(self.dsrs[-1])
        # self.p = self.p1.plot(timevec, self.dscache[-1]) # If cache is amp already
        self.p = self.p1.plot(timevec, np.abs(self.dscache[-1])) # If cache is complex
        self.p.setClipToView(True)

        self.p1.setMouseEnabled(x=True,y=False)
        self.p1.setMenuEnabled(False)

        dfs = self.getDisplayedFs()
        viewBufferX = 0.1 * self.ydata.size / dfs
        self.p1.setLimits(xMin = -viewBufferX, xMax = self.ydata.size / dfs + viewBufferX)
        self.curDsrIdx = -1 # On init, the maximum dsr is used
        self.p1.vb.setXRange(-viewBufferX, self.ydata.size/dfs + viewBufferX) # Set it to zoomed out at start

    def plotReim(self):
        # Legend for reim
        self.p1.addLegend()
        # Recreate the plots like ampTime
        timevec = self.getTimevec(self.dsrs[-1])
        self.pre = self.p1.plot(timevec, np.real(self.dscache[-1]), pen='r', name='Re')
        self.pim = self.p1.plot(timevec, np.imag(self.dscache[-1]), pen='c', name='Im')
        self.pre.setClipToView(True)
        self.pim.setClipToView(True)
        

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
        self.specFreqRes = dfs / self.nperseg
        # print(self.specFreqRes, self.freqs[1]-self.freqs[0]) # confirmed the same
        self.specTimeRes = self.ts[1] - self.ts[0]

        self.freqs = np.fft.fftshift(self.freqs) + self.fc # Offset by the centre freq
        self.sxx = np.fft.fftshift(self.sxx, axes=0)
        self.sxxMax = np.max(self.sxx.flatten())
        self.sxxMin = np.min(self.sxx.flatten()) # use this in log-view
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
            cm2use = pg.colormap.get('viridis') # you don't need matplotlib to use viridis!
            self.sp.setLookupTable(cm2use.getLookupTable())
            self.sp.setLevels([0, self.sxxMax])
            
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

            # Create the tracking dot
            self.spd = self.spw.plot([0], [0],
                pen=None,
                symbol='o',
                symbolBrush='k',
                symbolSize=5
            )
            self.spd.setCurveClickable(False) # prevent clicks? TODO: this still doesn't fix time linear region not showing when hovered over specgram

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
            self.formatlinearRegionBoundsLabel((start,end))

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

    def formatlinearRegionBoundsLabel(self, region):
        self.linearRegionBoundsLabel.setText("%f : %f (%f)" % (region[0], region[1], region[1]-region[0]))

    @Slot()
    def onAmpRegionChanged(self):
        region = self.linearRegion.getRegion()
        self.formatlinearRegionBoundsLabel(region)
        # Change the other region to match
        self.specLinearRegion.setRegion(region)


    @Slot()
    def onSpecRegionChanged(self):
        region = self.specLinearRegion.getRegion()
        self.formatlinearRegionBoundsLabel(region)
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
                if self.plotType == self.AMPL_PLOT:
                    # self.p.setData(self.getTimevec(dsr), self.dscache[self.curDsrIdx], clipToView=True) # setting clipToView on the plotdataitem works directly
                    self.p.setData(self.getTimevec(dsr), np.abs(self.dscache[self.curDsrIdx]), clipToView=True) # use this if cache is complex
                elif self.plotType == self.REIM_PLOT:
                    self.pre.setData(self.getTimevec(dsr), np.real(self.dscache[self.curDsrIdx]), clipToView=True)
                    self.pim.setData(self.getTimevec(dsr), np.imag(self.dscache[self.curDsrIdx]), clipToView=True)
                    
        
        if targetDSR > self.dsrs[self.curDsrIdx]: # If too many points, zoom out i.e. increase the DSR
            if self.curDsrIdx < -1:
                self.curDsrIdx = self.curDsrIdx + 1
                # Set the zoomed data on the PlotDataItem
                dsr = self.dsrs[self.curDsrIdx]
                if self.plotType == self.AMPL_PLOT:
                    # self.p.setData(self.getTimevec(dsr), self.dscache[self.curDsrIdx], clipToView=True) # setting clipToView on the plotdataitem works directly
                    self.p.setData(self.getTimevec(dsr), np.abs(self.dscache[self.curDsrIdx]), clipToView=True) # use this if cache is complex
                elif self.plotType == self.REIM_PLOT:
                    self.pre.setData(self.getTimevec(dsr), np.real(self.dscache[self.curDsrIdx]), clipToView=True)
                    self.pim.setData(self.getTimevec(dsr), np.imag(self.dscache[self.curDsrIdx]), clipToView=True)

        # TODO: rightclick 'view all' bug: does not zoom out completely?

    def ampMouseMoved(self, evt):
        mousePoint = self.p1.vb.mapSceneToView(evt[0])
        self.xCoordLabel.setText("X: %f" % (mousePoint.x()))
        self.ampCoordLabel.setText("Y (Top): %f" % (mousePoint.y()))

    def specMouseMoved(self, evt):
        mousePoint = self.spw.vb.mapSceneToView(evt[0])
        self.specCoordLabel.setText("Y (Bottom): %f" % (mousePoint.y()))
        # Attempt to find the nearest point
        if self.specFreqRes is not None:
            timeIdx = int(np.round((mousePoint.x() - self.ts[0]) / self.specTimeRes))
            freqIdx = int(np.round((mousePoint.y() - self.freqs[0]) / self.specFreqRes))
            if timeIdx > 0 and timeIdx < self.ts.size and freqIdx > 0 and freqIdx < self.freqs.size: # only the upwards movement has errors
                self.specPowerLabel.setText("Z (Bottom): %g" % self.sxx[timeIdx, freqIdx])
                # Set the marker
                self.spd.setData([self.ts[timeIdx]], [self.freqs[freqIdx]])

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

        elif modifiers == Qt.ControlModifier | Qt.ShiftModifier:
            if self.freqRegion is None:
                self.addFreqRegion()
                
            else:
                # Retrieve limits
                region = self.freqRegion.getRegion()
                print("freqregion = ", region)

                # Confirm filter mechanics
                item, ok = QInputDialog.getItem(self,
                    "Confirm Filter",
                    "No. of Filter Taps:",
                    [str(2**i) for i in range(3,15)], # for now, manually copied from loaderSettings
                    0, # index of default
                    False # no edits allowed
                )
                # TODO: custom dialog to also have downsampling option

                if ok and item:
                    numTaps = int(item)
                    cutoff = region[1] - region[0]
                    freqshift = -np.mean(region)
                    print("Taps: %d, cutoff: %g, freqshift: %g" % (numTaps,cutoff,freqshift))
                    
                    # TODO: Perform the re-filter, save as a separate array and display, with option to revert


                # Remove the linear region regardless
                self.delFreqRegion()
                

    def addFreqRegion(self):
        # Don't bother getting the cursor, just add to the middle of the screen
        viewrange = self.spw.viewRange()[1] # get y-limits
        middle = np.mean(viewrange)
        span = viewrange[1] - viewrange[0]
        # Create the linear region
        self.freqRegion = pg.LinearRegionItem(
            values=(middle-0.1*span, middle+0.1*span),
            orientation='horizontal'
        )
        self.spw.addItem(self.freqRegion)

    def delFreqRegion(self):
        self.spw.removeItem(self.freqRegion)
        self.freqRegion = None

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
            demodAction = menu.addAction("Demodulate")


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
                    self.audiowin.show()

            elif action == demodAction:
                if self.linearRegion is None:
                    self.demodwin = DemodWindow(self.ydata, fs=dfs)
                else:
                    region = self.linearRegion.getRegion()
                    startIdx, endIdx = self.convertRegionToIndices(region)
                    self.demodwin = DemodWindow(self.ydata[startIdx:endIdx], startIdx, endIdx, fs=dfs)
                self.demodwin.show()

    def convertRegionToIndices(self, region):
        dfs = self.getDisplayedFs()

        # First make sure it's clipped to the start/end of the data only
        rstart = region[0] if region[0] >=0 else 0
        rend = region[1] if region[1] < self.ydata.size/dfs else (self.ydata.size-1)/dfs

        startIdx = int(rstart*dfs)
        endIdx = int(rend*dfs)

        return startIdx, endIdx

    def event(self, event):
        '''Override events for status tips.'''
        if event.type() == QEvent.HoverEnter:
            self.SignalViewStatusTip.emit("Ctrl-Alt-Click to select a region for processing; by default, processes all data.")
        # elif event.type() == QEvent.HoverLeave:
        #     print("leave") # TODO: do we need this?
        return super().event(event)
