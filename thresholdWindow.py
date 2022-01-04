from PySide6.QtWidgets import QMainWindow, QVBoxLayout, QHBoxLayout, QWidget, QLabel, QComboBox, QFormLayout
from PySide6.QtWidgets import QPushButton
from PySide6.QtCore import Qt, Signal, Slot, QRectF
import pyqtgraph as pg
import numpy as np
import scipy.signal as sps


class ThresholdWindow(QMainWindow):
    def __init__(self, freqs, ts, sxx):
        super().__init__()

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
        widget.setLayout(self.layout)
        self.setCentralWidget(widget)

        # Add the plot widget
        self.glw = pg.GraphicsLayoutWidget()
        self.layout.addWidget(self.glw)
        self.p = self.glw.addPlot(row=0,col=0)
        self.plt = pg.ImageItem()
        self.p.addItem(self.plt)

        # Initialize with the same spectrogram immediately
        self.plt.setImage(self.sxx)
        self.plt.setRect(
            QRectF(
                self.ts[0]-self.tgap/2, 
                self.freqs[0]-self.fgap/2, self.tspan+self.tgap, self.fspan+self.fgap
            )
        ) # Proper setting of the box boundaries
        cm2use = pg.colormap.getFromMatplotlib('viridis')
        self.plt.setLookupTable(cm2use.getLookupTable())
        self.p.setMouseEnabled(x=True,y=False)
        self.p.setMenuEnabled(False)

        viewBufferX = 0.1 * self.ts[-1]
        self.p.setLimits(xMin = -viewBufferX, xMax = self.ts[-1] + viewBufferX)
        
        # Make another plot for the histogram of powers
        self.hglw = pg.GraphicsLayoutWidget()
        self.layout.addWidget(self.hglw)

        self.histoplt = pg.HistogramLUTItem()
        self.histoplt.setImageItem(self.plt)
        self.hglw.addItem(self.histoplt)

        # Create the options
        self.optLayout = QFormLayout()
        self.runBtn = QPushButton("Run")
        self.optLayout.addWidget(self.runBtn)
        self.layout.addLayout(self.optLayout)
