from PySide6.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QLineEdit, QFormLayout, QComboBox, QDialogButtonBox, QCheckBox
from PySide6.QtWidgets import QLabel, QRadioButton, QGroupBox
from PySide6.QtCore import Qt, Signal, Slot
import numpy as np

class PredetectAmpDialog(QDialog):
    predetectAmpSignal = Signal(dict)

    def __init__(self, parent=None):

        super().__init__()
        self.setWindowTitle("Predetect via Amplitude")

        ## Layout
        self.layout = QVBoxLayout()
        # Description
        self.layout.addWidget(QLabel("This method will highlight files that meet a certain amplitude criteria."))
        # Main settings
        self.formlayout = QFormLayout()
        self.layout.addLayout(self.formlayout)
        self.setLayout(self.layout)
        ## Buttons
        buttonBox = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttonBox.accepted.connect(self.accept)
        buttonBox.rejected.connect(self.reject)
        self.layout.addWidget(buttonBox)

        ## Fill in the options
        # Noise
        self.useMeanNoise = QRadioButton("Mean (fast)")
        self.useMeanNoise.setChecked(True)
        self.useMedianNoise = QRadioButton("Median (slow)")
        self.noiseGroupBox = QGroupBox()
        self.noiseGroupBox.setStyleSheet("border: 0px;")
        self.noiseLayout = QHBoxLayout()
        self.noiseLayout.addWidget(self.useMeanNoise)
        self.noiseLayout.addWidget(self.useMedianNoise)
        self.noiseGroupBox.setLayout(self.noiseLayout)
        self.formlayout.addRow("Noise Estimation Method", self.noiseGroupBox)
        # Signal
        self.signalSNR = QLineEdit("2")
        self.formlayout.addRow("Signal SNR (Linear)", self.signalSNR)
        self.signalSNRdb = QLineEdit()
        self.signalSNRdb.setEnabled(False)
        self.signalSNR.textEdited.connect(self.displayNewSNR)
        self.displayNewSNR(self.signalSNR.text())
        self.formlayout.addRow("Signal SNR (dB)", self.signalSNRdb)


    def accept(self):
        options = {
            "meanNoise": self.useMeanNoise.isChecked(),
            "medianNoise": self.useMedianNoise.isChecked(),
            "snr": float(self.signalSNR.text())
        }
        self.predetectAmpSignal.emit(options)

        super().accept()

    @Slot(str)
    def displayNewSNR(self, s: str):
        if len(s) > 0:
            self.signalSNRdb.setText(str(10*np.log10(float(s))))