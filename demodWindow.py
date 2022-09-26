from PySide6.QtWidgets import QMainWindow, QVBoxLayout, QHBoxLayout, QFormLayout, QWidget, QLabel, QComboBox, QPushButton
from PySide6.QtWidgets import QSpinBox, QMessageBox, QLineEdit, QTextBrowser, QSlider, QGroupBox, QRadioButton
from PySide6.QtCore import Qt, Signal, Slot, QRectF
# from PySide6.QtGui import QFontDatabase
import pyqtgraph as pg
import numpy as np
import scipy.signal as sps
from functools import partial

from dsp import makeFreq, SimpleDemodulatorBPSK, SimpleDemodulatorQPSK, SimpleDemodulator8PSK, SimpleDemodulatorPSK

class DemodWindow(QMainWindow):
    def __init__(self, slicedData=None, startIdx=None, endIdx=None, fs=1.0):
        super().__init__()

        # Attaching data
        self.slicedData = slicedData
        self.fs = int(fs)

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
        self.rotGrpBox = QGroupBox()
        self.btmLayout.addWidget(self.rotGrpBox)
        self.rotGrpLayout = QVBoxLayout()
        self.rotGrpBox.setLayout(self.rotGrpLayout)
        # Preload many radio buttons
        self.rotRadioBtns = [
            QRadioButton() for i in range(8) # For now, 8 maximum
        ]
        for i, btn in enumerate(self.rotRadioBtns):
            self.rotGrpLayout.addWidget(btn)
            # Start out as hidden
            btn.hide()
            # Connect it
            btn.clicked.connect(partial(self.rotChanged, i))

        self.hexBrowser = QTextBrowser()
        self.hexBrowser.setMinimumHeight(300)
        self.hexBrowser.setFontFamily("Monospace")
        self.btmLayout.addWidget(self.hexBrowser)

        self.asciiBrowser = QTextBrowser()
        self.asciiBrowser.setFontFamily("Monospace")
        self.btmLayout.addWidget(self.asciiBrowser)

    def setupPlots(self):
        self.abswin = pg.GraphicsLayoutWidget()
        self.topLayout.addWidget(self.abswin)
        self.absplt = self.abswin.addPlot()
        self.abspltitem = self.absplt.plot(np.arange(self.slicedData.size)/self.fs, np.abs(self.slicedData))

        self.rwin = pg.GraphicsLayoutWidget()
        self.rwin.setMinimumHeight(300)
        self.midLayout.addWidget(self.rwin)
        self.eoplt = self.rwin.addPlot(0,0)
        self.conplt = self.rwin.addPlot(0,1)

        self.symSizeSlider = QSlider(Qt.Vertical)
        self.symSizeSlider.setRange(1, 100)
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
        symSize = size / 100 * self.maxSymbolSize
        self.conpltitem.setSymbolSize(symSize)

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
        if resampled.size % self.osr != 0:
            resampled = resampled[:-(resampled.size % self.osr)]
        self.demodulator.demod(resampled.astype(np.complex64), self.osr, verb=False)

        # Plot the eye-opening
        self.eopltitem = self.eoplt.plot(
            self.demodulator.eo_metric
        )
        # Plot the constellation
        maxbound = np.max(self.demodulator.reimc.view(np.float32)) * 1.5
        self.conpltitem = self.conplt.plot(
            np.real(self.demodulator.reimc),
            np.imag(self.demodulator.reimc),
            symbol='o',
            symbolPen=None,
            symbolBrush='w',
            pen=None
        )
        self.maxSymbolSize = self.conpltitem.opts['symbolSize']
        self.symSizeSlider.setValue(100) # Maximum at the start
        self.conplt.setLimits(
            xMin=-maxbound*2,
            xMax=maxbound*2, # Need longer range for x when window is viewed in standard 16:9
            yMin=-maxbound,
            yMax=maxbound
        ) 
        self.conplt.setAspectLocked()

        # Update the options for rotation
        self.updateRotations()

        # Interpret and post to text browsers
        self.interpret()
        

    def interpret(self, phaseSymShift: int=0):
        # Update the text browsers
        hexvals = self.demodulator.packBinaryBytesToBits(
            self.demodulator.unpackToBinaryBytes(
                self.demodulator.symsToBits(phaseSymShift=phaseSymShift)
            )
        )
        self.hexBrowser.setPlainText(
            ' '.join(["%02X" % i for i in hexvals])
            # ' '.join([np.base_repr(i, base=16) for i in hexvals])
        )
        # There may be issues converting to a readable string..
        readable = hexvals.tobytes().decode("utf-8", "backslashreplace")
        # May contain null chars?
        readable = readable.replace("\0", " ") # Replace with spaces?
        
        self.asciiBrowser.setPlainText(
            str(readable)
        )


    def updateRotations(self):
        # Only show buttons up to the current mod type
        [self.rotRadioBtns[i].show() for i in range(self.demodulator.m)]
        # Hide everything after
        [self.rotRadioBtns[i].hide() for i in range(self.demodulator.m, len(self.rotRadioBtns))]

        # Check the first one
        self.rotRadioBtns[0].setChecked(True)

    @Slot(int)
    def rotChanged(self, i: int):
        print("Rotation %d selected" % i)
        # Reinterpret
        self.interpret(i)
        