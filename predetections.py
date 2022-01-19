from PySide6.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QLineEdit, QFormLayout, QComboBox, QDialogButtonBox, QCheckBox
from PySide6.QtWidgets import QLabel, QRadioButton, QGroupBox, QProgressDialog
from PySide6.QtCore import Qt, Signal, Slot, QThread, QObject
import numpy as np

import time

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

        # Launch a thread?
        worker = PredetectAmpWorker([], options)
        worker.resultReady.connect(self.handleResults)
        worker.finished.connect(worker.deleteLater)
        worker.start()

        # Launch a progress dialog
        progress = QProgressDialog(
            "Running predetection on files",
            "",
            0, 5, parent=self)
        worker.progressNow.connect(progress.setValue)

        super().accept()

    @Slot(str)
    def displayNewSNR(self, s: str):
        if len(s) > 0:
            self.signalSNRdb.setText(str(10*np.log10(float(s))))

    @Slot(list)
    def handleResults(results: list):
        print("TODO: handle results")

class PredetectAmpWorker(QThread):
    resultReady = Signal(list)
    progressNow = Signal(int)

    def __init__(self, filelist: list, options: dict, parent=None):
        super().__init__(parent)

        self.filelist = filelist
        self.options = options

    def run(self):
        for i in range(5):
            time.sleep(1)
            self.progressNow.emit(i+1)

        self.resultReady.emit([])