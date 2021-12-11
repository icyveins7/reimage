from PySide6.QtWidgets import QDialog, QVBoxLayout, QLineEdit, QFormLayout, QComboBox, QDialogButtonBox, QCheckBox
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
        self.formlayout.addRow("Spectrogram Window Size", self.specNpersegDropdown)

    def accept(self):
        
        super().accept()
        

