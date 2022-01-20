from PySide6.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QLineEdit, QFormLayout, QComboBox, QDialogButtonBox, QCheckBox
from PySide6.QtWidgets import QLabel, QRadioButton, QGroupBox, QProgressDialog
from PySide6.QtCore import Qt, Signal, Slot, QThread, QObject
import numpy as np

import time

class PredetectAmpDialog(QDialog):
    predetectAmpSignal = Signal(list)

    def __init__(self, filelist: list, parent=None):

        super().__init__()
        self.setWindowTitle("Predetect via Amplitude")

        self.filelist = filelist
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
        self.formlayout.addRow("Signal Amplitude Ratio (Linear)", self.signalSNR)
        self.signalSNRdb = QLineEdit()
        self.signalSNRdb.setEnabled(False)
        self.signalSNR.textEdited.connect(self.displayNewSNR)
        self.displayNewSNR(self.signalSNR.text())
        self.formlayout.addRow("Signal Amplitude Ratio (dB)", self.signalSNRdb)


    def accept(self):
        options = {
            "meanNoise": self.useMeanNoise.isChecked(),
            "medianNoise": self.useMedianNoise.isChecked(),
            "snr": float(self.signalSNR.text())
        }


        # Launch a thread?
        worker = PredetectAmpWorker(self.filelist, options)
        worker.resultReady.connect(self.handleResults)
        worker.finished.connect(worker.deleteLater)
        worker.start()

        # Launch a progress dialog
        progress = QProgressDialog(
            "Running predetection on files",
            None,
            0, len(self.filelist), parent=self)
        worker.progressNow.connect(progress.setValue)
        progress.exec() # exec at the end, this will close along with the worker, ensuring no segfaults

        super().accept()

    @Slot(str)
    def displayNewSNR(self, s: str):
        if len(s) > 0:
            self.signalSNRdb.setText(str(10*np.log10(float(s))))

    @Slot(list)
    def handleResults(results: list):
        print(results)
        print("TODO: handle results")

class PredetectAmpWorker(QThread):
    resultReady = Signal(list)
    progressNow = Signal(int)

    def __init__(self, filelist: list, options: dict, parent=None):
        super().__init__(parent)

        self.filelist = filelist
        self.options = options

    def run(self):
        results = [False for i in range(len(self.filelist))]

        for i in range(len(self.filelist)):
            # Open the file
            data = np.fromfile(self.filelist[i]) # TODO: get the file settings
            data = data.astype(np.float32).view(np.complex64)
            absdata = np.abs(data)

            # Noise floor determination
            if self.options['meanNoise']:
                noisefloor = np.mean(absdata)

            elif self.options['medianNoise']:
                noisefloor = np.median(absdata)

            # Detect signal presence
            found = np.any(absdata > (noisefloor * self.options['snr']))
            # results.append(found)
            results[i] = found

            time.sleep(0.1)

            self.progressNow.emit(i+1)
            
        print(results)
        self.resultReady.emit(results)