from PySide6.QtWidgets import QMainWindow, QVBoxLayout, QHBoxLayout, QFormLayout, QWidget, QLabel, QComboBox, QPushButton
from PySide6.QtWidgets import QSpinBox
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
        self.btmLayout = QHBoxLayout()
        self.layout.addLayout(self.btmLayout)

        # Plots
        self.setupPlots() # This has to be before setupOptions for layout reasons

        # Options menus
        self.setupOptions()

        # Object holder for the demodulator
        self.demodulator = None

    def setupPlots(self):
        self.abswin = pg.GraphicsLayoutWidget()
        self.topLayout.addWidget(self.abswin)
        self.absplt = self.abswin.addPlot()
        self.abspltitem = self.absplt.plot(np.arange(self.slicedData.size)/self.fs, np.abs(self.slicedData))

        self.rwin = pg.GraphicsLayoutWidget()
        self.btmLayout.addWidget(self.rwin)
        self.eoplt = self.rwin.addPlot(0,0)
        self.conplt = self.rwin.addPlot(0,1)



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
        self.baudSpinbox.setMinimum(1)
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

        print("TODO: runDemod")


        