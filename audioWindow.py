from PySide6.QtWidgets import QMainWindow, QVBoxLayout, QHBoxLayout, QWidget, QLabel, QComboBox
from PySide6.QtWidgets import QPushButton, QSlider
from PySide6.QtCore import Qt, Signal, Slot, QRectF, QThread, QObject
from PySide6.QtGui import QIcon
import pyqtgraph as pg
import numpy as np
import scipy.signal as sps
import sounddevice as sd

#%% Target for smoothness up to 50kHz sample rate.
# This should cover the typical sample rates of 44.1k to 48k.


class AudioWindow(QMainWindow):
    audioPause = Signal()
    audioReset = Signal()
    audioStart = Signal()
    tuneSignal = Signal(int)
    audioFrame = Signal(int)

    def __init__(self, slicedData=None, startIdx=None, endIdx=None, fs=1.0):
        super().__init__()
        self.setAttribute(Qt.WA_DeleteOnClose) # Ensure deletion so threads are cleanedup

        # Attaching data
        # TODO: fix padding so that specgram can be performed
        self.slicedData = slicedData
        self.fs = fs
        print(self.fs)
        self.timevec = np.arange(self.slicedData.size) / self.fs # pre-generate time

        # And also the spectrogram form
        print("Pre-calcing specgram")
        # self.fSpec, self.tSpec, self.dataSpec = sps.spectrogram(self.slicedData, self.fs, return_onesided=False)
        self.fSpec, self.tSpec, self.dataSpec = sps.spectrogram(self.slicedData, self.fs, return_onesided=True) # No point doing 2-sided
        # self.fSpec = np.fft.fftshift(self.fSpec) # only fftshift if two-sided
        # self.dataSpec = np.fft.fftshift(self.dataSpec, axes=0) # only fftshift if two sided
        self.dataSpec = self.dataSpec[:,::-1] # flip frequencies if one-sided
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
        self.playBtn = QPushButton("")
        self.playBtn.setIcon(QIcon.fromTheme("media-playback-start"))
        self.pauseBtn = QPushButton("")
        self.pauseBtn.setIcon(QIcon.fromTheme("media-playback-pause"))
        self.resetBtn = QPushButton("")
        self.resetBtn.setIcon(QIcon.fromTheme("media-playback-stop"))
        self.playbackLayout.addWidget(self.playBtn)
        self.playbackLayout.addWidget(self.pauseBtn)
        self.playbackLayout.addWidget(self.resetBtn)
        self.playBtn.clicked.connect(self.play)
        self.pauseBtn.clicked.connect(self.pause)
        self.resetBtn.clicked.connect(self.reset)

        # And then some audio feedback stats
        self.audioSlider = QSlider(Qt.Horizontal)
        self.audioSlider.setRange(0, self.slicedData.size)
        self.audioSlider.valueChanged.connect(self.adjustAudioFrame)
        self.playbackLayout.addWidget(self.audioSlider)
        self.audioTimeLabel = QLabel("%.2f" % 0)
        self.playbackLayout.addWidget(self.audioTimeLabel)

        # Add the top and bottom plots
        self.plotLayout = QHBoxLayout()
        self.plotWidget = pg.GraphicsLayoutWidget()
        self.topPlot = self.plotWidget.addPlot(row=0,col=0)
        self.btmPlot = self.plotWidget.addPlot(row=1,col=0)
        self.plotLayout.addWidget(self.plotWidget)

        self.freqSlider = QSlider(Qt.Vertical)
        self.freqSlider.setTickPosition(QSlider.TicksRight)
        self.freqSlider.valueChanged.connect(self.rollFreq)
        self.blocksize = 512 # TODO: make this adjustable
        self.freqSlider.setRange(0, self.blocksize-1)

        self.plotLayout.addWidget(self.freqSlider)
        self.layout.addLayout(self.plotLayout)
        self.topPlot.setXLink(self.btmPlot)
        self.topPlot.setMouseEnabled(x=True,y=False)
        self.topPlot.getAxis('left').setWidth(60) # Hardcoded for now
        self.btmPlot.getAxis('left').setWidth(60) # TODO: evaluate maximum y values in both graphs, then set an appropriate value

        # Placeholders
        self.topPlotItem = None

        # Some connections
        self.topPlot.sigRangeChanged.connect(self.onZoom)

        # Dynamic plotting variables
        self.pltDsr = 1

        # Add the image item
        self.btmImg = pg.ImageItem()
        self.btmPlot.addItem(self.btmImg)
        
        # if startIdx is not None and endIdx is not None:
        #     self.p.setLabels(title="Sample %d to %d" % (startIdx, endIdx))
        # self.plt = pg.PlotDataItem()
        # self.p.addItem(self.plt)

        # Plot the data
        self.timeBlock = 1.0 # constant for now
        self.timeExtent = np.array([0, 2 * self.timeBlock]) # initial time extent to plot
        self.extent = (self.timeExtent * self.fs).astype(np.uint32)
        self.plot()

        # Set up audio playback tracking lines
        self.topline, self.btmline = self.setupPlayLines()

        # Definitions for audio streams
        # Using a QThread
        self.thread = QThread(parent=self)
        self.worker = AudioWorker(self.fs, self.slicedData, blksize=self.blocksize)
        self.worker.moveToThread(self.thread)
        # self.thread.started.connect(self.worker.run) # Do not run on start
        # self.worker.finished.connect(self.thread.quit) # Do not quit either when finished
        # self.worker.finished.connect(self.worker.deleteLater)
        # self.thread.finished.connect(self.thread.deleteLater) # No deletions

        self.worker.progress.connect(self.updateAudioProgress)
        self.audioPause.connect(self.worker.stop)
        self.audioReset.connect(self.worker.reset)
        self.audioStart.connect(self.worker.run)
        self.tuneSignal.connect(self.worker.tune)
        self.audioFrame.connect(self.worker.updateFrame)

        self.thread.start()

        # self.current_frame = 0
        # self.stream = None
        # self.initAudioStream() # self.stream is initialised

    # In order to ensure proper thread cleanup,
    def closeEvent(self, evnt):
        # Stop thread 
        self.worker.stop()
        self.thread.quit()
        # Wait for it
        self.thread.wait()
        super().closeEvent(evnt)
        
    def plot(self):
        # Plot just like in signalView, but no need to downsample
        self.topPlotItem = self.topPlot.plot(np.arange(self.slicedData.size)/self.fs, self.slicedData) # and no need to abs
        # self.topPlotItem = self.topPlot.plot(
        #     self.timevec[self.extent[0]:self.extent[1]],
        #     self.slicedData[self.extent[0]:self.extent[1]]) # Plot 20 seconds only
        self.topPlotItem.setClipToView(True)
        
        # Set initial zoom (10 seconds only)
        self.topPlot.vb.setXRange(self.timeExtent[0], self.timeExtent[1])
        # self.topPlot.vb.setXRange(0, self.slicedData.size/self.fs) # Full extent for debugging
        self.topPlot.vb.disableAutoRange(axis=pg.ViewBox.XAxis) # This prevents every frame from updating the axis limits
        self.btmPlot.vb.disableAutoRange(axis=pg.ViewBox.XAxis) # Need to do this for both, then the graph will not consume excessive resources

        # self.btmImg.setImage(self.dataSpec[:,self.extent[0]:self.extent[1]])
        # self.btmImg.setRect(QRectF(self.timeExtent[0], -self.fs/2, self.timeExtent[1], self.fs))
        self.btmImg.setImage(self.dataSpec)
        # self.btmImg.setRect(QRectF(0, -self.fs/2, self.slicedData.size/self.fs, self.fs))
        self.btmImg.setRect(QRectF(0, 0, self.slicedData.size/self.fs, self.fs)) # Use this if one-sided specgram
        cm2use = pg.colormap.getFromMatplotlib('viridis')
        self.btmImg.setLookupTable(cm2use.getLookupTable())

        # Set limits
        viewBufferX = 0.1 * self.slicedData.size / self.fs
        self.topPlot.setLimits(xMin = -viewBufferX, xMax = self.slicedData.size/self.fs + viewBufferX)
        viewBufferY = 0.1 * (self.fSpec[-1]-self.fSpec[0])
        self.btmPlot.setLimits(
            xMin = -viewBufferX, xMax = self.slicedData.size/self.fs + viewBufferX,
            yMin = self.fSpec[0] - viewBufferY, yMax = self.fSpec[-1] + viewBufferY
        )

        
    def setupPlayLines(self):
        topline = pg.InfiniteLine(0)
        btmline = pg.InfiniteLine(0)
        self.topPlot.addItem(topline)
        self.btmPlot.addItem(btmline)
        return topline, btmline

    #%% Frequency manipulation
    def rollFreq(self):
        self.tuneSignal.emit(self.freqSlider.value())

    def play(self):
        # Simply emit the signal
        self.audioStart.emit()
    
    @Slot()
    def adjustAudioFrame(self):
        frame = self.audioSlider.value()
        # Emit signal to audio stream
        self.audioFrame.emit(frame)
        # Adjust text
        self.updateAudioTimeLabel(frame/self.fs)
        # Adjust playlines
        self.updatePlaylines(frame/self.fs)

    @Slot(float)
    def updateAudioProgress(self, t: float):
        # print("Audio progress is %f" % t)
        self.updatePlaylines(t)
        self.updateAudioTimeLabel(t)
        self.audioSlider.setValue(int(t * self.fs))

    def updatePlaylines(self, t: float):
        self.topline.setValue(t)
        self.btmline.setValue(t)

    def updateAudioTimeLabel(self, t: float):
        self.audioTimeLabel.setText("%.2f / %.2f" % (t, self.slicedData.size / self.fs))

    def pause(self):
        self.audioPause.emit()
        
    def reset(self):
        self.audioReset.emit()

    #%% Handlers for dynamic zoom loading
    @Slot()
    def onZoom(self):
        xrange = self.topPlot.viewRange()[0]
        xstart = xrange[0]
        xend = xrange[1]
        # print("xrange = %f to %f" % (xstart,xend))

        # Define limits
        targetSamples = 10000
        # maxSamples = 20000

        # Count the number of samples inside the range now
        numRawInRange = int((xend-xstart)*self.fs) + 1
        # print("numRawInRange = %d" % numRawInRange)
        targetDsr = numRawInRange // targetSamples
        # print("targetDsr = %d" % targetDsr)

        if targetDsr > self.pltDsr * 10:
            self.pltDsr = self.pltDsr * 10
        elif self.pltDsr > targetDsr * 10 and self.pltDsr > 1:
            self.pltDsr = self.pltDsr // 10

        # Replot (this is surprisingly good enough, without caching)
        if self.topPlotItem is not None:
            self.topPlotItem.setData(
                np.arange(0,self.slicedData.size,self.pltDsr) / self.fs,
                self.slicedData[::self.pltDsr]
            )


#%% 
class AudioWorker(QObject):
    finished = Signal()
    progress = Signal(float)
    current_frame = 0

    def __init__(self, fs, slicedData, blksize=256, parent=None):
        super().__init__(parent=parent)

        self.fs = fs

        self.slicedData = slicedData
        self.stream = sd.OutputStream(
            samplerate = fs,
            channels = 1,
            callback = self._callback,
            dtype = np.float32,
            blocksize = blksize
        )

        self.blksize = blksize

        self.tone = np.cos(2*np.pi*0*np.arange(self.blksize)/self.blksize)

    @Slot(int)
    def tune(self, f_int: int):
        self.tone = np.cos(2*np.pi*f_int*np.arange(self.blksize)/self.blksize)

    #%% For sounddevice stream
    def _callback(self, outdata, frames, time, status):
        if status:
            print(status)

        chunksize = min(len(self.slicedData) - self.current_frame, frames)
        # print(chunksize, frames)

        # outdata[:chunksize] = self.slicedData[self.current_frame:self.current_frame + chunksize]
         # for now, hotfix the single channel
        # outdata[:chunksize, 0] = self.slicedData[self.current_frame:self.current_frame + chunksize]
        # Can we do a multiply in the stream?
        outdata[:chunksize, 0] = self.slicedData[self.current_frame:self.current_frame + chunksize] * self.tone[:chunksize]
        if chunksize < frames:
            outdata[chunksize:] = 0
            self.finished.emit()
            # Stop the stream if it ends
            self.stream.stop()
            # raise sd.CallbackStop() # Do not raise this, or the stream object crashes
        self.current_frame += chunksize

        # Update the label?
        # print("Input", time.inputBufferAdcTime)
        # self.audioTimeLabel.setText("%.2f" % time.inputBufferAdcTime)
        # self.progress.emit(time.inputBufferAdcTime)
        self.progress.emit(self.current_frame / self.fs)
        # print("Output", time.outputBufferDacTime) # These 2 are a bit useless
        # print(time.currentTime)

    @Slot(int)
    def updateFrame(self, frame):
        self.current_frame = frame

    @Slot()
    def run(self):
        self.stream.start()

    @Slot()
    def stop(self):
        self.stream.stop()
        # self.current_frame = 0
        self.finished.emit()

    @Slot()
    def reset(self):
        self.stream.stop()
        self.current_frame = 0
        self.progress.emit(0)
        
