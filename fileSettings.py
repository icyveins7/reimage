from PySide6.QtWidgets import QDialog, QVBoxLayout, QLineEdit, QFormLayout, QComboBox, QDialogButtonBox, QCheckBox
from PySide6.QtCore import Qt, Signal, Slot
import numpy as np
# import sqlite3 as sq

class FileSettingsDialog(QDialog):
    filesettingsSignal = Signal(dict)

    def __init__(self, filesettings: dict):
        super().__init__()
        self.setWindowTitle("File Format Settings")

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
        # Data type
        self.datafmtDropdown = QComboBox()
        dataformats = ["complex int16", "complex float32", "complex float64"]
        self.datafmtDropdown.addItems(dataformats)
        if filesettings['fmt'] in dataformats:
            self.datafmtDropdown.setCurrentIndex(dataformats.index(filesettings['fmt']))
        self.formlayout.addRow("File Data Type", self.datafmtDropdown)

        # Header size
        self.headersizeEdit = QLineEdit(str(filesettings['headersize']))
        self.formlayout.addRow("Header Length (bytes)", self.headersizeEdit)

        # Fixed Length
        self.fixedlenCheckbox = QCheckBox()
        self.fixedlenEdit = QLineEdit(str(filesettings['fixedlen']))
        if filesettings['usefixedlen']:
            self.fixedlenCheckbox.setChecked(True)
            self.fixedlenEdit.setEnabled(True)
        else:
            self.fixedlenEdit.setEnabled(False)
        self.fixedlenCheckbox.toggled.connect(self.fixedlenEdit.setEnabled)
        self.formlayout.addRow("Use Fixed Length Per File", self.fixedlenCheckbox)
        self.formlayout.addRow("Data Length Per File (samples)", self.fixedlenEdit)

        # Inverted Spectrum
        self.invertspecCheckbox = QCheckBox()
        self.invertspecCheckbox.setChecked(filesettings['invSpec'])
        self.formlayout.addRow("Inverted Spectrum?", self.invertspecCheckbox)

    def accept(self):
        newsettings = {
            "fmt": self.datafmtDropdown.currentText(),
            "headersize": int(self.headersizeEdit.text()),
            "usefixedlen": self.fixedlenCheckbox.isChecked(),
            "fixedlen": int(self.fixedlenEdit.text()),
            "invSpec": self.invertspecCheckbox.isChecked()
        }
        self.filesettingsSignal.emit(newsettings)
        super().accept()
        
    # # Not really needed..
    # def reject(self):
    #     super().reject()
        
        
