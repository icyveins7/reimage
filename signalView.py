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
from phasorWindow import PhasorWindow

from markerdb import MarkerDB

import time

class SignalView(QFrame):
    VIEW_BUFFER_FRACTION = 0.05

    AMPL_PLOT = 0
    REIM_PLOT = 1
    SignalViewStatusTip = Signal(str)
    DataSelectionSignal = Signal(list, list, np.ndarray)

    lower, target, upper = (5000, 10000, 20000) # This is the lower bound, target, and upper bounds for sample slicing

    def __init__(self, ydata, filelist=None, sampleStarts=None, parent=None, f=Qt.WindowFlags()):
        super().__init__(parent, f)

        # Set global specgram image configuration
        pg.setConfigOption('imageAxisOrder', 'row-major')

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
        # self.setDownsampleCache()

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
        self.pmarker = None # Placeholder for amp plot marker
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

        # Placeholders for phasors
        self.phasorSampBuffer = 1

        # Placeholder for time vector
        self.timevec = None
        
        # Placeholders for viewbox tracking
        self.idx0 = 0
        self.idx1 = -1
        self.skip = 1

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
            t1 = time.time()
            self.sp.setLevels([minval, maxval])
            t2 = time.time()
            print("Took %f seconds to set contrast" % (t2-t1))

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
        """
        This is the main method from the main script, which is called whenever files are loaded.
        It performs all necessary pre-processing, clears old plots, and renders the new data.

        Parameters
        ----------
        ydata : np.ndarray
            Complex data to be viewed.
        filelist : list of str
            Filelist that was loaded. This is used for marker labels which are
            tagged to file/sample pairs.
        sampleStarts : list of int
            List of sample start values for each file. This is also used for marker
            label calculations.
        """
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
            print("Tone gen: %fs.\n" % (t2-t1))
            self.ydata = self.ydata * tone
            t3 = time.time()
            print("Tone mul: %fs.\n" % (t3-t2))
        
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

        # Define the time vector
        print('displayedFs = %d' % (self.getDisplayedFs()))
        self.timevec = np.arange(0, self.ydata.size) / self.getDisplayedFs()
        
        self.filelist = filelist
        self.sampleStarts = sampleStarts

        self.loadMarkers()

        # self.setDownsampleCache()
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

    @Slot()
    def changeToReimPlot(self):
        # Set the plot type
        self.plotType = self.REIM_PLOT

        # First thing is to clear the amplitude plot
        self.p1.clear()

        # Then create the reim one
        self.plotReim()

    def plotAmpTime(self):
        # Create and save the PlotDataItems as self.p
        if self.timevec is not None:
            length = self.timevec.size
            self.skip = length // self.target
            self.idx0 = 0
            self.idx1 = length

            t1 = time.time()
            t = self.timevec[self.idx0:self.idx1:self.skip]
            t2 = time.time()
            amp = np.abs(self.ydata[self.idx0:self.idx1:self.skip])
            t3 = time.time()
            print(t)
            print(amp)
            
            self.p = self.p1.plot(t, amp)
            self.p.setClipToView(True)
            t4 = time.time()
            self.p1.vb.setYRange(0, np.max(amp))
            t5 = time.time()
            self.p1.disableAutoRange(axis=pg.ViewBox.YAxis)
            t6 = time.time()
            print("Took %f, %f to slice time and data" % (t2-t1, t3-t2))
            print("Took %f, %f, %f to set data, set y range and disable autorange" % (
                t4-t3, t5-t4, t6-t5))


            self.p1.setMouseEnabled(x=True,y=False)
            self.p1.setMenuEnabled(False)

            dfs = self.getDisplayedFs()
            viewBufferX = self.VIEW_BUFFER_FRACTION * self.ydata.size / dfs
            self.p1.setLimits(xMin = -viewBufferX, xMax = self.ydata.size / dfs + viewBufferX)
            self.curDsrIdx = -1 # On init, the maximum dsr is used
            self.p1.vb.setXRange(-viewBufferX, self.ydata.size/dfs + viewBufferX) # Set it to zoomed out at start

            # Create the tracking marker
            self.pmarker = self.p1.plot([0],[0],pen=None,symbol='o',symbolBrush='y')
            

    def plotReim(self):
        # Legend for reim
        self.p1.addLegend()
        # Recreate the plots like ampTime        
        self.pre = self.p1.plot(
            self.timevec[self.idx0:self.idx1:self.skip], 
            np.real(self.ydata[self.idx0:self.idx1:self.skip]),
            pen='r', name='Re')
        self.pim = self.p1.plot(
            self.timevec[self.idx0:self.idx1:self.skip], 
            np.imag(self.ydata[self.idx0:self.idx1:self.skip]), 
            pen='c', name='Im')
        self.pre.setClipToView(True)
        self.pim.setClipToView(True)
        

        self.p1.setMouseEnabled(x=True,y=False)
        self.p1.setMenuEnabled(False)

        dfs = self.getDisplayedFs()
        viewBufferX = self.VIEW_BUFFER_FRACTION * self.ydata.size / dfs
        self.p1.setLimits(xMin = -viewBufferX, xMax = self.ydata.size / dfs + viewBufferX)
        self.curDsrIdx = -1 # On init, the maximum dsr is used
        self.p1.vb.setXRange(-viewBufferX, self.ydata.size/dfs + viewBufferX) # Set it to zoomed out at start

        

    def plotSpecgram(self, window=('tukey',0.25), auto_transpose=False):
        dfs = self.getDisplayedFs()
        self.freqs, self.ts, self.sxx = sps.spectrogram(
            self.ydata, dfs, window, self.nperseg, self.noverlap, self.nperseg, 
            return_onesided=False, detrend=False
        )
        # print(self.sxx.shape) # This is (nfft, self.ts.size)

        # Calculate resolutions for later
        self.specFreqRes = dfs / self.nperseg
        # print(self.specFreqRes, self.freqs[1]-self.freqs[0]) # confirmed the same
        self.specTimeRes = self.ts[1] - self.ts[0]

        self.freqs = np.fft.fftshift(self.freqs) + self.fc # Offset by the centre freq
        self.sxx = np.fft.fftshift(self.sxx, axes=0)
        self.sxxMax = np.max(self.sxx.flatten())
        self.sxxMin = np.min(self.sxx.flatten()) # use this in log-view
        # Obtain the spans and gaps for proper plotting
        tspan = self.ts[-1] - self.ts[0]
        fspan = self.freqs[-1] - self.freqs[0]

        if auto_transpose:
            self.sxx = self.sxx.T

        if self.xdata is None:
            self.sp.setImage(
                self.sxx, 
                autoLevels=False, 
                levels=[0, self.sxxMax],
                rect=QRectF(
                    self.ts[0]-self.specTimeRes/2, 
                    self.freqs[0]-self.specFreqRes/2, 
                    tspan+self.specTimeRes, 
                    fspan+self.specFreqRes)
            ) # set image on existing item instead?
            self.sp.setAutoDownsample(active=False) # Performance on the downsampler is extremely bad! Main cause of lag spikes
            cm2use = pg.colormap.get('viridis') # you don't need matplotlib to use viridis!
            self.sp.setLookupTable(cm2use.getLookupTable())
            
            self.spw.addItem(self.sp) # Must add it back because clears are done in setYData
            self.spw.setMenuEnabled(False)

            viewBufferX = self.VIEW_BUFFER_FRACTION * self.ydata.size/dfs
            viewBufferY = self.VIEW_BUFFER_FRACTION * fspan
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
            self.spd.setCurveClickable(False)

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
        tt0 = time.time()

        # ==== New implementation
        # Get the current axes view limits
        xstart, xend = self.p1.viewRange()[0]
        # Define the number of points we want to render for any given snapshot
        lower, target, upper = (5000, 10000, 20000) # This is the lower bound, target, and upper bounds

        # Conditions for re-calculating the plot slice
        reslice = False
        ### Check zooms        
        dfs = self.getDisplayedFs()
        numPtsInRange = (xend-xstart) * dfs // self.skip # Find number of points currently plotted and in viewbox
        # print("numPtsInRange = %d" % (numPtsInRange))
        # Check only if we can zoom further in
        reslice = True if self.skip > 1 and (numPtsInRange < lower or numPtsInRange > upper) else reslice
        if reslice:
            print("Reslice is %s after checking zoom" % (reslice))
        ### Check panning shifts
        target_i0 = max(int(xstart * dfs), 0) # This is what is requested
        target_i1 = min(int(xend * dfs), self.ydata.size)
        reslice = True if target_i0 < self.idx0 or target_i1 > self.idx1 else reslice
        if reslice:
            print("Reslice is %s after checking pan" % (reslice))

        # TODO: For specgram downsampling, not used for now
        # target_i0_spec = max(int((xstart-self.ts[0]) / self.specTimeRes), 0)
        # target_i1_spec = min(int((xend-self.ts[0]) / self.specTimeRes), self.ts.size)

        # Reslice if needed
        if reslice:
            print("Old %d:%d" % (self.idx0, self.idx1))
            # Add some buffer so we don't trigger too often
            self.idx0 = max(target_i0 - target, 0)
            self.idx1 = min(target_i1 + target, self.ydata.size)
            self.skip = max((target_i1 - target_i0) // target, 1) # We don't include the buffer in the skip calculation
            print("Plotting %d:%d:%d" % (self.idx0, self.idx1, self.skip))

            
            t1 = time.time()
            t = self.timevec[self.idx0:self.idx1:self.skip]
            t2 = time.time()
            if self.plotType == self.AMPL_PLOT:
                amp = np.abs(self.ydata[self.idx0:self.idx1:self.skip])
                t3 = time.time()
                
                self.p.setData(t, amp,
                            clipToView=True)
                t4 = time.time()
                self.p1.vb.setYRange(0, np.max(amp))
                t5 = time.time()
            elif self.plotType == self.REIM_PLOT:
                re = np.real(self.ydata[self.idx0:self.idx1:self.skip])
                im = np.imag(self.ydata[self.idx0:self.idx1:self.skip])
                t3 = time.time()

                self.pre.setData(
                    t, re,
                    clipToView=True
                )
                self.pim.setData(
                    t, im,
                    clipToView=True
                )
                t4 = time.time()
                self.p1.vb.setYRange(min(np.min(re),np.min(im)), max(np.max(re), np.max(im)))
                t5 = time.time()


            self.p1.disableAutoRange(axis=pg.ViewBox.YAxis)
            t6 = time.time()
            print("Took %f, %f to slice time and data" % (t2-t1, t3-t2))
            print("Took %f, %f, %f to set data, set y range and disable autorange" % (
                t4-t3, t5-t4, t6-t5))
            
            # # TODO: Similar work for specgram # This is very slow..
            # self.idx0_spec = max(target_i0_spec - target_i0, 0)
            # self.idx1_spec = min(target_i1_spec + target_i1, self.ts.size)
            # self.skip_spec = max((target_i1_spec - target_i0_spec) // target, 1)
            # print("Plotting %d:%d:%d" % (self.idx0_spec, self.idx1_spec, self.skip_spec))

            # t = self.ts[self.idx0_spec:self.idx1_spec:self.skip_spec]
            # sxx = self.sxx[:, self.idx0_spec:self.idx1_spec:self.skip_spec]


            # tspan = self.ts[-1] - self.ts[0]
            # fspan = self.freqs[-1] - self.freqs[0]
            # self.sp.setImage(
            #     sxx, 
            #     autoLevels=False, 
            #     levels=[0, self.sxxMax],
            #     rect=QRectF(
            #         self.ts[0]-self.specTimeRes/2,
            #         self.freqs[0]-self.specFreqRes/2, 
            #         tspan+self.specTimeRes, 
            #         fspan+self.specFreqRes)
            # )
            



        # Update UI
        self.viewboxlabel.setText("Plot indices: %5d : %5d : %5d (Max)" % (
            self.idx0, self.idx1, self.skip))
        
        tt1 = time.time()
        print("%fs for update." % (tt1-tt0))


    def ampMouseMoved(self, evt):
        modifiers = QApplication.keyboardModifiers()
        # Only map markers when shift is held down, otherwise this can slow down zooming for large data sets
        # TODO: maybe only mark based on plotted values?
        if modifiers == Qt.ShiftModifier:
            mousePoint = self.p1.vb.mapSceneToView(evt[0])
            self.xCoordLabel.setText("X: %f" % (mousePoint.x()))
            self.ampCoordLabel.setText("Y (Top): %f" % (mousePoint.y()))

            # Find nearest point based on x value
            # For now, we ignore the viewing downsample rate (only read the pure data)
            timevec = self.getTimevec(1)
            timeIdx = int(np.round((mousePoint.x() - timevec[0]) * self.getDisplayedFs()))
            
            # Set the marker
            if timeIdx > 0 and timeIdx < self.ydata.size:
                self.pmarker.setData([timevec[timeIdx]],[np.abs(self.ydata[timeIdx])])

                # If the phasor window is open, set the data there
                try:
                    start = np.max([0, timeIdx-self.phasorSampBuffer])
                    end = np.min([self.ydata.size, timeIdx+self.phasorSampBuffer+1]) # Need +1 to include
                    self.phasorWindow.updateData(
                        self.ydata[start:end],
                        timeIdx - start # This is the actual offset, to mark the 'middle', accounting for when too near to 0
                    )
                except Exception as e:
                    pass
                    # Left here for debugging purposes
                    # print("Exception for phasor: %s" % str(e))


    def specMouseMoved(self, evt):
        modifiers = QApplication.keyboardModifiers()
        # Only map markers when shift is held down, otherwise this can slow down zooming for large data sets
        # TODO: maybe only mark based on plotted values?
        if modifiers == Qt.ShiftModifier:
            mousePoint = self.spw.vb.mapSceneToView(evt[0])
            self.specCoordLabel.setText("Y (Bottom): %f" % (mousePoint.y()))
            # Attempt to find the nearest point
            if self.specFreqRes is not None:
                timeIdx = int(np.round((mousePoint.x() - self.ts[0]) / self.specTimeRes))
                freqIdx = int(np.round((mousePoint.y() - self.freqs[0]) / self.specFreqRes))
                if timeIdx > 0 and timeIdx < self.ts.size and freqIdx > 0 and freqIdx < self.freqs.size: # only the upwards movement has errors
                    # self.specPowerLabel.setText("Z (Bottom): %g" % self.sxx[timeIdx, freqIdx])
                    self.specPowerLabel.setText("Z (Bottom): %g" % self.sxx[freqIdx, timeIdx]) # For non-transposed data now, TODO: handle transposed cases?
                    # Set the marker
                    self.spd.setData([self.ts[timeIdx]], [self.freqs[freqIdx]])

    def onAmpMouseClicked(self, evt):
        # print(evt[0].button())
        modifiers = QApplication.keyboardModifiers()
        if modifiers == Qt.ControlModifier | Qt.AltModifier:
            # Add Window ie LinearRegion
            if self.linearRegion is None:
                mousePoint = self.p1.vb.mapSceneToView(evt[0].scenePos())
                start = mousePoint.x() # remember to use scenepos and mapscenetoview to get the specgram plot correct, even over the tracking dot!

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

        # Extract the slice if it's present
        if self.linearRegion is not None:
            region = self.linearRegion.getRegion()
            startIdx, endIdx = self.convertRegionToIndices(region)
            selection = self.ydata[startIdx:endIdx]
        else:
            startIdx = 0
            endIdx = len(self.ydata)
            selection = self.ydata # Shouldn't invoke a copy so we should be fine

        modifiers = QApplication.keyboardModifiers()
        if bool(modifiers == Qt.ControlModifier): # Going to leave it as control-modifier, in case we want the pyqtgraph default menu back later on
            menu = QMenu()
            # Menu Entries
            # ===
            selectAction = menu.addAction("Select Data for Export")
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
            # ===
            phasorAction = menu.addAction("View Phasor")


            # Start the menu
            action = menu.exec_(self.mapToGlobal(event.pos()))
            if action == fftAction:
                self.fftwin = FFTWindow(selection, startIdx, endIdx, dfs)
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
                self.baudwin = EstimateBaudWindow(selection, startIdx, endIdx, dfs)
                self.baudwin.show()

            elif action == estFreqAction:
                self.freqwin = EstimateFreqWindow(selection, startIdx, endIdx, dfs)
                self.freqwin.show()

            elif action == energyDetectAction:
                self.threshwin = ThresholdWindow(self.freqs, self.ts, self.sxx, self)
                self.threshwin.show()

            elif action == audioAction:
                self.audiowin = AudioWindow(selection, startIdx, endIdx, dfs)
                self.audiowin.show()

            elif action == demodAction:
                self.demodwin = DemodWindow(selection, startIdx, endIdx, dfs)
                self.demodwin.show()

            elif action == phasorAction:
                self.phasorWindow = PhasorWindow(self.phasorSampBuffer, self)
                # Connect the settings
                self.phasorWindow.changeSampBufferSignal.connect(self.changePhasorSampBuffer)
                self.phasorWindow.show()

            elif action == selectAction:
                # Emit the data selection signal first!
                self.DataSelectionSignal.emit(
                    self.filelist,
                    [startIdx, endIdx],
                    selection
                )
                # Show the dialog; user can copy/paste code and it should be ready by the time
                # the dialog shows up
                text, ok = QInputDialog.getMultiLineText(
                    self, 
                    "Extract selection", 
                    "The selected data can be retrieved by running the following code:",
                    "from ipc import getReimageData\n\n"
                    "exported = getReimageData()"
                )
                # Don't need to process anything

                    


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

    # Connections for live phasor window
    @Slot(int)
    def changePhasorSampBuffer(self, sampbuffer: int):
        self.phasorSampBuffer = sampbuffer
        try:
            self.phasorWindow.setSampBufferLabel(self.phasorSampBuffer)
        except Exception as e:
            pass
            # For debugging purposes..
            # print("Exception when changing phasor samp buffer %s" % str(e))

