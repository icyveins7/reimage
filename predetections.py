from PySide6.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QLineEdit, QFormLayout, QComboBox, QDialogButtonBox, QCheckBox
from PySide6.QtWidgets import QLabel, QRadioButton, QGroupBox, QProgressDialog
from PySide6.QtCore import Qt, Signal, Slot, QThread, QObject
import numpy as np

import time

class PredetectAmpDialog(QDialog):
    predetectAmpSignal = Signal(list)

    def __init__(self, filelist: list, filesettings: dict, parent=None):

        super().__init__()
        self.setWindowTitle("Predetect via Amplitude")

        self.filelist = filelist
        self.filesettings = filesettings
        print(self.filelist)

        ## Layout
        self.layout = QVBoxLayout()
        # Description
        self.layout.addWidget(
            QLabel(
                "This method will highlight files whose amplitude values meet a certain ratio requirement.\n"
                "It is most useful for quick selection of files where the signal power is high and the signal duration is short (<< length of 1 file).")
            )
        # Main settings
        self.formlayout = QFormLayout()
        self.layout.addLayout(self.formlayout)
        self.setLayout(self.layout)
        ## Buttons
        buttonBox = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttonBox.accepted.connect(self.accept)
        buttonBox.rejected.connect(self.reject)
        self.layout.addWidget(buttonBox)

        ## Fill in both modes
        self.ratioMode = QRadioButton("Ratio")
        self.ratioMode.setChecked(True)
        self.thresholdMode = QRadioButton("Threshold")
        self.modeBox = QGroupBox()
        self.modeBox.setStyleSheet("border: 0px;")
        self.modeLayout = QHBoxLayout()
        self.modeLayout.addWidget(self.ratioMode)
        self.modeLayout.addWidget(self.thresholdMode)
        self.modeBox.setLayout(self.modeLayout)
        self.formlayout.addRow("Detect via minimum", self.modeBox)

        ## Fill in the options for Ratio
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
        self.signalSNR = QLineEdit("10")
        self.formlayout.addRow("Signal Amplitude Ratio (Linear)", self.signalSNR)
        self.signalSNRdb = QLineEdit()
        self.signalSNRdb.setEnabled(False)
        self.signalSNR.textEdited.connect(self.displayNewSNR)
        self.displayNewSNR(self.signalSNR.text())
        self.formlayout.addRow("Signal Amplitude Ratio (dB)", self.signalSNRdb)

        ## Fill in the options for Threshold
        # Level
        self.minThresholdEdit = QLineEdit()
        self.minThresholdEdit.setEnabled(False) # Default to ratio mode
        self.formlayout.addRow("Signal Minimum Threshold", self.minThresholdEdit)

        ## Connect the modes to the widgets
        self.ratioMode.toggled.connect(self.noiseGroupBox.setEnabled)
        self.ratioMode.toggled.connect(self.signalSNR.setEnabled)

        self.thresholdMode.toggled.connect(self.minThresholdEdit.setEnabled)


    def accept(self):
        options = {
            "ratioMode": self.ratioMode.isChecked(),
            "thresholdMode": self.thresholdMode.isChecked(),
            "meanNoise": self.useMeanNoise.isChecked(),
            "medianNoise": self.useMedianNoise.isChecked(),
            "snr": float(self.signalSNR.text()),
            "threshold": float(self.minThresholdEdit.text())
        }

        # Launch a thread?
        results = [False for i in range(len(self.filelist))]
        self.worker = PredetectAmpWorker(self.filelist, options, results, parent=self)
        # self.worker.resultReady.connect(self.handleResults)
        # self.worker.finished.connect(self.worker.deleteLater)
        self.worker.start()

        # Launch a progress dialog
        progress = QProgressDialog(
            "Running predetection on files",
            None,
            0, len(self.filelist), parent=self)
        self.worker.progressNow.connect(progress.setValue)
        progress.exec() # exec at the end, this will close along with the worker, ensuring no segfaults
        # TODO: known bug with qt.qpa.xcb BadWindow error in console, but nothing is wrong?

        self.handleResults(results)

        super().accept()

    @Slot(str)
    def displayNewSNR(self, s: str):
        if len(s) > 0:
            self.signalSNRdb.setText(str(10*np.log10(float(s))))

    @Slot(list)
    def handleResults(self, results):
        print(results)
        self.predetectAmpSignal.emit(results)

# =================================
class PredetectAmpWorker(QThread):
    resultReady = Signal(list)
    progressNow = Signal(int)

    def __init__(self, filelist: list, options: dict, results: list, parent=None):
        super().__init__(parent)

        self.filelist = filelist
        self.options = options
        self.results = results

    def run(self):

        if self.options['ratioMode']:
            for i in range(len(self.filelist)):
                # Open the file
                data = np.fromfile(self.filelist[i], dtype=np.int16) # TODO: get the file settings
                data = data.astype(np.float32).view(np.complex64)
                absdata = np.abs(data)

                # Noise floor determination
                if self.options['meanNoise']:
                    noisefloor = np.mean(absdata)

                elif self.options['medianNoise']:
                    noisefloor = np.median(absdata)

                # Detect signal presence
                found = np.any(absdata > (noisefloor * self.options['snr']))
                self.results[i] = found

                self.progressNow.emit(i+1)
                
            # self.resultReady.emit(self.results)

        elif self.options['thresholdMode']:
            for i in range(len(self.filelist)):
                # Open the file
                data = np.fromfile(self.filelist[i], dtype=np.int16) # TODO: get the file settings
                data = data.astype(np.float32).view(np.complex64)
                absdata = np.abs(data)

                # Detect signal presence
                found = np.any(absdata > self.options['threshold'])
                self.results[i] = found

                self.progressNow.emit(i+1)
                
            # self.resultReady.emit(self.results)