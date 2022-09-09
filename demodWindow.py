from PySide6.QtWidgets import QMainWindow, QVBoxLayout, QHBoxLayout, QFormLayout, QWidget, QLabel, QComboBox, QPushButton
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
        self.layout = QHBoxLayout()
        widget.setLayout(self.layout)
        self.setCentralWidget(widget)

        # Options menus
        self.optOuterLayout = QVBoxLayout()
        self.layout.addLayout(self.optOuterLayout)

        self.optLayout = QFormLayout()
        self.optOuterLayout.addLayout(self.optLayout)

        self.modDropdown = QComboBox()
        self.modtypestrings = ["Select Scheme", "BPSK", "QPSK", "8PSK"]
        self.modDropdown.addItems(self.modtypestrings)
        self.modDropdown.currentIndexChanged.connect(self.makeDemodulator)
        self.optLayout.addRow("Modulation Type", self.modDropdown)

        self.demodBtn = QPushButton("Demodulate")
        self.demodBtn.clicked.connect(self.runDemod)
        self.optOuterLayout.addWidget(self.demodBtn)

        # Object holder for the demodulator
        self.demodulator = None

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


        