from PySide6.QtWidgets import QMainWindow, QVBoxLayout, QHBoxLayout, QWidget, QLabel, QComboBox, QFormLayout
from PySide6.QtWidgets import QPushButton, QRadioButton, QButtonGroup, QGroupBox
from PySide6.QtCore import Qt, Signal, Slot, QRectF
import pyqtgraph as pg
import numpy as np
import scipy.signal as sps


class ThresholdWindow(QMainWindow):
    def __init__(self, freqs, ts, sxx, parent=None):
        super().__init__(parent)

        # Attaching specgram data
        self.freqs = freqs
        self.ts = ts
        self.sxx = sxx

        # Obtain the spans and gaps for proper plotting
        self.tgap = self.ts[1] - self.ts[0]
        self.fgap = self.freqs[1] - self.freqs[0]
        self.tspan = self.ts[-1] - self.ts[0]
        self.fspan = self.freqs[-1] - self.freqs[0]

        # Aesthetics..
        self.setWindowTitle("Energy Detection (Thresholding)")

        # Main layout
        widget = QWidget()
        self.layout = QHBoxLayout()
        self.plotLayout = QHBoxLayout()
        self.plotLayout.setSpacing(0)
        widget.setLayout(self.layout)
        self.setCentralWidget(widget)
        self.layout.addLayout(self.plotLayout)

        # Add the plot widget
        self.glw = pg.GraphicsLayoutWidget()
        self.plotLayout.addWidget(self.glw)
        self.p = self.glw.addPlot(row=0,col=0)
        self.plt = pg.ImageItem()
        self.p.addItem(self.plt)
        self.scatter = pg.ScatterPlotItem(pen='r', brush='r')
        self.p.addItem(self.scatter)

        # Initialize with the same spectrogram immediately
        self.plt.setImage(self.sxx)
        self.plt.setRect(
            QRectF(
                self.ts[0]-self.tgap/2, 
                self.freqs[0]-self.fgap/2, self.tspan+self.tgap, self.fspan+self.fgap
            )
        ) # Proper setting of the box boundaries
        viewBufferX = 0.1 * self.ts[-1]
        self.p.setLimits(xMin = -viewBufferX, xMax = self.ts[-1] + viewBufferX)
        
        # Make another plot for the histogram of powers
        self.hglw = pg.HistogramLUTWidget(image=self.plt)
        self.plotLayout.addWidget(self.hglw)
        # Manually make the lower line non-adjustable, and the region non-draggable
        for region in self.hglw.item.regions:
            region.setMovable(False)
            region.lines[1].setMovable(True) # Only allow upper line to move
        # Then fix the limits of viewbox
        self.hglw.item.vb.setMouseEnabled(x=False, y=False) 
        self.hglw.item.vb.setMaximumHeight(self.hglw.item.getLevels()[1]*1.1) # TODO: this doesn't stop the y-axis extending when dragging the region..

        # Set colours (after creating HistogramLUT, otherwise it resets colour)
        cm2use = pg.colormap.getFromMatplotlib('viridis')
        print(cm2use)
        self.plt.setLookupTable(cm2use.getLookupTable())
        self.p.setMouseEnabled(x=True,y=False)
        self.p.setMenuEnabled(False)
        self.hglw.gradient.loadPreset("viridis")

        # Create the options
        self.optLayout = QVBoxLayout()
        self.layout.addLayout(self.optLayout)

        self.typeBtnGroup = QButtonGroup()
        self.oneSigBtn = QRadioButton("Only One Signal")
        self.oneSigBtn.setChecked(True)
        self.manySigBtn = QRadioButton("Possibly Many Signals")
        self.typeBtnGroup.addButton(self.oneSigBtn)
        self.typeBtnGroup.addButton(self.manySigBtn)
        self.optLayout.addWidget(self.oneSigBtn)
        self.optLayout.addWidget(self.manySigBtn)

        self.formLayout = QFormLayout()
        self.runBtn = QPushButton("Run")
        self.runBtn.clicked.connect(self.onRun)
        self.formLayout.addWidget(self.runBtn)
        self.optLayout.addLayout(self.formLayout)

    @Slot()
    def onRun(self):
        # Get the histogram LUT values
        histoItem = self.hglw.item
        histlvls = histoItem.getLevels()
        print(histlvls)

        # Mark everything in range (above the upper cutoff)
        idx = np.argwhere(self.sxx > histlvls[1])
        xidx = idx[:,0]
        yidx = idx[:,1]
        tmarks = self.ts[xidx]
        ymarks = self.freqs[yidx]

        self.scatter.setData(x=tmarks, y=ymarks) # TODO: modify so that this shows on drag of the LUT instead

        if self.oneSigBtn.isChecked():
            print("Boxing with one sig only")

        elif self.manySigBtn.isChecked():
            print("Boxing with many sigs")


        print("TODO")

