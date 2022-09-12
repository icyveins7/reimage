from PySide6.QtWidgets import QMainWindow, QVBoxLayout, QHBoxLayout, QFormLayout, QWidget, QLabel, QComboBox, QPushButton
from PySide6.QtWidgets import QSpinBox, QMessageBox, QLineEdit, QTextBrowser, QSlider
from PySide6.QtCore import Qt, Signal, Slot, QRectF
import pyqtgraph as pg
import numpy as np
import scipy.signal as sps

from dsp import makeFreq, SimpleDemodulatorBPSK, SimpleDemodulatorQPSK, SimpleDemodulator8PSK, SimpleDemodulatorPSK

class DemodWindow(QMainWindow):
    def __init__(self, slicedData=None, startIdx=None, endIdx=None, fs=1.0):
        super().__init__()

        # Attaching data
        self.slicedData = slicedData
        self.fs = fs

        # Aesthetics..
        self.setWindowTitle("Demodulator")

        # Main layout
        widget = QWidget()
        self.layout = QVBoxLayout()
        widget.setLayout(self.layout)
        self.setCentralWidget(widget)

        self.topLayout = QHBoxLayout()
        self.layout.addLayout(self.topLayout)
        self.midLayout = QHBoxLayout()
        self.layout.addLayout(self.midLayout)
        self.btmLayout = QHBoxLayout()
        self.layout.addLayout(self.btmLayout)

        # Plots
        self.setupPlots() # This has to be before setupOptions for layout reasons

        # Options menus
        self.setupOptions()

        # Bits results
        self.setupBitsViews()

        # Object holder for the demodulator
        self.demodulator = None

    def setupBitsViews(self):
        self.hexBrowser = QTextBrowser()
        self.btmLayout.addWidget(self.hexBrowser)

        self.asciiBrowser = QTextBrowser()
        self.btmLayout.addWidget(self.asciiBrowser)

    def setupPlots(self):
        self.abswin = pg.GraphicsLayoutWidget()
        self.topLayout.addWidget(self.abswin)
        self.absplt = self.abswin.addPlot()
        self.abspltitem = self.absplt.plot(np.arange(self.slicedData.size)/self.fs, np.abs(self.slicedData))

        self.rwin = pg.GraphicsLayoutWidget()
        self.midLayout.addWidget(self.rwin)
        self.eoplt = self.rwin.addPlot(0,0)
        self.conplt = self.rwin.addPlot(0,1)

        self.symSizeSlider = QSlider(Qt.Vertical)
        self.midLayout.addWidget(self.symSizeSlider)
        self.symSizeSlider.valueChanged.connect(self.adjustSymSize)


    def setupOptions(self):
        self.optOuterLayout = QVBoxLayout()
        self.topLayout.addLayout(self.optOuterLayout)

        self.optLayout = QFormLayout()
        self.optOuterLayout.addLayout(self.optLayout)

        self.modDropdown = QComboBox()
        self.modtypestrings = ["Select Scheme", "BPSK", "QPSK", "8PSK"]
        self.modDropdown.addItems(self.modtypestrings)
        self.modDropdown.currentIndexChanged.connect(self.makeDemodulator)
        self.optLayout.addRow("Modulation Type", self.modDropdown)

        self.fsLabel = QLabel(str(self.fs))
        self.optLayout.addRow("Input Sample Rate: ", self.fsLabel)

        self.baud = 1
        self.baudSpinbox = QSpinBox()
        self.baudSpinbox.setRange(1, 2147483647) # Arbitrarily set maximum to int32 max
        self.baudSpinbox.valueChanged.connect(self.setBaud)
        self.optLayout.addRow("Baud Rate", self.baudSpinbox)

        self.osrSpinbox = QSpinBox()
        self.osr = 1
        self.osrSpinbox.setMinimum(1)
        self.osrSpinbox.valueChanged.connect(self.osrChanged)
        self.optLayout.addRow("Target OSR", self.osrSpinbox)

        self.updownLabel = QLabel()
        self.optLayout.addRow("Resample Factors: ", self.updownLabel)

        self.finalfsLabel = QLabel()
        self.optLayout.addRow("Output Sample Rate: ", self.finalfsLabel)

        # Call the slot once to initialize the other values
        self.osrChanged(self.osr) 

        self.demodBtn = QPushButton("Demodulate")
        self.demodBtn.clicked.connect(self.runDemod)
        self.optOuterLayout.addWidget(self.demodBtn)

    @Slot(int)
    def adjustSymSize(self, size):
        pass # TODO
        # self.conpltitem.setSymbol()

    @Slot(int)
    def setBaud(self, baud):
        self.baud = baud
        # Re-evaluate the resampling factors
        self.evaluateResampling()


    @Slot(int)
    def osrChanged(self, osr):
        self.osr = osr
        # Re-evaluate the resampling factors
        self.evaluateResampling()

    def evaluateResampling(self):
        # Evaluate the resample factors
        self.up = np.lcm(self.fs, self.osr * self.baud) // self.fs
        self.down = np.lcm(self.fs, self.osr * self.baud) // (self.baud * self.osr)
        self.finalfs = self.osr * self.baud
        # Place them in their widgets
        self.updownLabel.setText("%d/%d" % (self.up, self.down))
        self.finalfsLabel.setText("%f" % self.finalfs)

    @Slot(int)
    def makeDemodulator(self, modidx: int):
        modtype = self.modtypestrings[modidx]
        if modtype == 'BPSK':
            self.demodulator = SimpleDemodulatorBPSK()
            print("Created BPSK")
        elif modtype == 'QPSK':
            self.demodulator = SimpleDemodulatorQPSK()
            print("Created QPSK")
        elif modtype == '8PSK':
            self.demodulator = SimpleDemodulator8PSK()
            print("Created 8PSK")
        else:
            self.demodulator = None


    @Slot()
    def runDemod(self):
        # Ensure a scheme is selected
        if self.modDropdown.currentText() == self.modtypestrings[0]:
            # Raise dialog to say already exists
            QMessageBox.critical(
                self,
                "Invalid Options",
                "Please select a modulation scheme.",
                QMessageBox.Ok)
            return

        # First check if need to resample
        if self.up > 1 or self.down > 1:
            # Run the resampling
            resampled = sps.resample_poly(self.slicedData, self.up, self.down)
        else:
            resampled = self.slicedData
        
        # Run demodulator
        self.demodulator.demod(resampled.astype(np.complex64), self.osr, verb=False)

        # Plot the eye-opening
        self.eopltitem = self.eoplt.plot(
            self.demodulator.eo_metric
        )
        # Plot the constellation
        maxbound = np.max(self.demodulator.reimc.view(np.float32)) * 1.1
        self.conpltitem = self.conplt.plot(
            np.real(self.demodulator.reimc),
            np.imag(self.demodulator.reimc),
            symbol='o',
            symbolPen=None,
            symbolBrush='w',
            pen=None
        )
        self.conplt.setLimits(xMin=-maxbound, xMax=maxbound, yMin=-maxbound, yMax=maxbound)


        