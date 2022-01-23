from PySide6.QtWidgets import QDialog, QVBoxLayout, QLineEdit, QFormLayout, QComboBox
from PySide6.QtWidgets import QDialogButtonBox, QCheckBox, QSpinBox, QLabel
from PySide6.QtCore import Qt, Signal, Slot
import numpy as np
# import sqlite3 as sq

class SignalSettingsDialog(QDialog):
    signalsettingsSignal = Signal(dict)

    def __init__(self, signalsettings: dict):
        super().__init__()
        self.setWindowTitle("Signal Viewer Settings")

        ## Layout
        self.layout = QVBoxLayout()
        self.formlayout = QFormLayout()
        self.layout.addLayout(self.formlayout)
        self.setLayout(self.layout)

        ## Buttons
        buttonBox = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel | QDialogButtonBox.RestoreDefaults)
        buttonBox.accepted.connect(self.accept)
        buttonBox.rejected.connect(self.reject)
        self.layout.addWidget(buttonBox)

        ## Options
        # Specgram nperseg
        self.specNpersegDropdown = QComboBox()
        self.specNpersegDropdown.addItems([str(2**i) for i in range(8,17)])
        self.specNpersegDropdown.setCurrentText(str(signalsettings['nperseg']))
        self.formlayout.addRow("Spectrogram Window Size (samples)", self.specNpersegDropdown)

        # Specgram Noverlap
        nperseg = int(self.specNpersegDropdown.currentText())
        self.specNoverlapSpinbox = QSpinBox()
        self.specNoverlapSpinbox.setRange(0, nperseg-1)
        self.specNoverlapSpinbox.setValue(signalsettings['noverlap'])
        self.specNpersegDropdown.currentTextChanged.connect(self.onNpersegChanged)
        self.specNoverlapLabel = QLabel("Spectrogram Overlap (samples) [default: %d]" % (nperseg/8) )
        self.formlayout.addRow(self.specNoverlapLabel, self.specNoverlapSpinbox)

        # Sample Rate
        self.fsEdit = QLineEdit(str(signalsettings['fs']))
        self.formlayout.addRow("Sample Rate (samples per second)", self.fsEdit)

        # Frequency shift
        self.freqshiftCheckbox = QCheckBox()
        self.formlayout.addRow("Apply initial frequency shift?", self.freqshiftCheckbox)
        self.freqshiftEdit = QLineEdit(str(signalsettings['freqshift']) if signalsettings['freqshift'] is not None else None)
        self.freqshiftEdit.setEnabled(False)
        self.freqshiftCheckbox.toggled.connect(self.freqshiftEdit.setEnabled)
        self.formlayout.addRow("Initial frequency shift (Hz)", self.freqshiftEdit)
        self.freqshiftCheckbox.setChecked(True if signalsettings['freqshift'] is not None else False)

        # Filtering
        self.filterCheckbox = QCheckBox()
        self.formlayout.addRow("Apply filter?", self.filterCheckbox)
        self.numTapsDropdown = QComboBox()
        self.numTapsDropdown.addItems([str(2**i) for i in range(3,15)])
        self.numTapsDropdown.setCurrentText(str(signalsettings['numTaps']) if signalsettings['numTaps'] is not None else None)
        self.numTapsDropdown.setEnabled(False)
        self.cutoffEdit = QLineEdit(str(signalsettings['filtercutoff']) if signalsettings['filtercutoff'] is not None else None)
        self.cutoffEdit.setEnabled(False)
        self.filterCheckbox.toggled.connect(self.numTapsDropdown.setEnabled)
        self.filterCheckbox.toggled.connect(self.cutoffEdit.setEnabled)
        self.formlayout.addRow("No. of Filter Taps", self.numTapsDropdown)
        self.formlayout.addRow("Cutoff Frequency (Hz)", self.cutoffEdit)
        self.filterCheckbox.setChecked(True if signalsettings['numTaps'] is not None else False)


        # Downsampling
        self.downsampleCheckbox = QCheckBox()
        self.formlayout.addRow("Apply downsampling?", self.downsampleCheckbox)
        self.downsampleEdit = QLineEdit(str(signalsettings['dsr']) if signalsettings['dsr'] is not None else None)
        self.downsampleEdit.setEnabled(False)
        self.downsampleCheckbox.toggled.connect(self.downsampleEdit.setEnabled)
        self.formlayout.addRow("Downsample Rate", self.downsampleEdit)
        self.downsampleCheckbox.setChecked(True if signalsettings['dsr'] is not None else False)

    @Slot(str)
    def onNpersegChanged(self, txt: str):
        # We edit the Noverlapdropdown
        nperseg = int(txt)
        self.specNoverlapSpinbox.setRange(0, nperseg-1)
        self.specNoverlapLabel.setText("Spectrogram Overlap (samples) [default: %d]" % (nperseg/8))
        self.specNoverlapSpinbox.setValue(nperseg/8)

    def accept(self):
        newsettings = {
            'nperseg': int(self.specNpersegDropdown.currentText()),
            'noverlap': self.specNoverlapSpinbox.value(),
            'fs': int(self.fsEdit.text()),
            'freqshift': float(self.freqshiftEdit.text()) if self.freqshiftCheckbox.isChecked() else None,
            'numTaps': int(self.numTapsDropdown.currentText()) if self.filterCheckbox.isChecked() else None,
            'filtercutoff': float(self.cutoffEdit.text()) if self.filterCheckbox.isChecked() else None,
            'dsr': int(self.downsampleEdit.text()) if self.downsampleCheckbox.isChecked() else None
        }
        self.signalsettingsSignal.emit(newsettings)
        super().accept()
        

