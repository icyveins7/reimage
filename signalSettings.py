from PySide6.QtWidgets import QDialog, QVBoxLayout, QLineEdit, QFormLayout, QComboBox
from PySide6.QtWidgets import QDialogButtonBox, QCheckBox, QSpinBox, QLabel
from PySide6.QtCore import Qt, Signal, Slot
import numpy as np
# import sqlite3 as sq

class SignalSettingsDialog(QDialog):
    signalsettingsSignal = Signal(dict)

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Signal Viewer Settings")

        ## Layout
        self.layout = QVBoxLayout()
        self.formlayout = QFormLayout()
        self.layout.addLayout(self.formlayout)
        self.setLayout(self.layout)

        ## Buttons
        buttonBox = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttonBox.accepted.connect(self.accept)
        buttonBox.rejected.connect(self.reject)
        self.layout.addWidget(buttonBox)

        ## Options
        # Specgram nperseg
        self.specNpersegDropdown = QComboBox()
        self.specNpersegDropdown.addItems([str(2**i) for i in range(8,17)])
        self.formlayout.addRow("Spectrogram Window Size (samples)", self.specNpersegDropdown)

        # Specgram Noverlap
        nperseg = int(self.specNpersegDropdown.currentText())
        self.specNoverlapDropdown = QSpinBox()
        self.specNoverlapDropdown.setValue(nperseg/8)
        self.specNoverlapDropdown.setRange(0, nperseg-1)
        self.specNpersegDropdown.currentTextChanged.connect(self.onNpersegChanged)
        self.specNoverlapLabel = QLabel("Spectrogram Overlap (samples) [default: %d]" % (nperseg/8) )
        self.formlayout.addRow(self.specNoverlapLabel, self.specNoverlapDropdown)

        # Sample Rate
        self.fsEdit = QLineEdit("1")
        self.formlayout.addRow("Sample Rate (samples per second)", self.fsEdit)

        # Frequency shift
        self.freqshiftCheckbox = QCheckBox()
        self.formlayout.addRow("Apply initial frequency shift?", self.freqshiftCheckbox)
        self.freqshiftEdit = QLineEdit()
        self.freqshiftEdit.setEnabled(False)
        self.freqshiftCheckbox.toggled.connect(self.freqshiftEdit.setEnabled)
        self.formlayout.addRow("Initial frequency shift (Hz)", self.freqshiftEdit)

        # Filtering
        self.filterCheckbox = QCheckBox()
        self.formlayout.addRow("Apply filter?", self.filterCheckbox)
        self.numTapsDropdown = QComboBox()
        self.numTapsDropdown.addItems([str(2**i) for i in range(3,15)])
        self.numTapsDropdown.setEnabled(False)
        self.cutoffEdit = QLineEdit()
        self.cutoffEdit.setEnabled(False)
        self.filterCheckbox.toggled.connect(self.numTapsDropdown.setEnabled)
        self.filterCheckbox.toggled.connect(self.cutoffEdit.setEnabled)
        self.formlayout.addRow("No. of Filter Taps", self.numTapsDropdown)
        self.formlayout.addRow("Cutoff Frequency (Hz)", self.cutoffEdit)

        # Downsampling
        self.downsampleCheckbox = QCheckBox()
        self.formlayout.addRow("Apply downsampling?", self.downsampleCheckbox)
        self.downsampleEdit = QLineEdit()
        self.downsampleEdit.setEnabled(False)
        self.downsampleCheckbox.toggled.connect(self.downsampleEdit.setEnabled)
        self.formlayout.addRow("Downsample Rate", self.downsampleEdit)

    @Slot(str)
    def onNpersegChanged(self, txt: str):
        # We edit the Noverlapdropdown
        nperseg = int(txt)
        self.specNoverlapDropdown.setRange(0, nperseg-1)
        self.specNoverlapLabel.setText("Spectrogram Overlap (samples) [default: %d]" % (nperseg/8))

    def accept(self):
        
        super().accept()
        

