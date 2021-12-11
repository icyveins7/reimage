from PySide6.QtWidgets import QDialog, QVBoxLayout, QLineEdit, QFormLayout, QComboBox, QDialogButtonBox, QCheckBox
from PySide6.QtCore import Qt, Signal, Slot
import numpy as np
import sqlite3 as sq

class FileSettingsDialog(QDialog):
    def __init__(self):
        super().__init__()

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
        self.formlayout.addRow("File Data Type", self.datafmtDropdown)

        # Header size
        self.headersizeEdit = QLineEdit("0")
        self.formlayout.addRow("Header Length (bytes)", self.headersizeEdit)

        # Fixed Length
        self.fixedlenCheckbox = QCheckBox()
        self.fixedlenEdit = QLineEdit()
        self.fixedlenEdit.setEnabled(False)
        self.fixedlenCheckbox.toggled.connect(self.fixedlenEdit.setEnabled)
        self.formlayout.addRow("Use Fixed Length Per File", self.fixedlenCheckbox)
        self.formlayout.addRow("Data Length Per File (samples)", self.fixedlenEdit)


        
