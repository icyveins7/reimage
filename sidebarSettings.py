from PySide6.QtWidgets import QFrame, QVBoxLayout, QHBoxLayout, QGroupBox, QFormLayout, QCheckBox
from PySide6.QtWidgets import QPushButton, QLabel, QLineEdit, QApplication, QMenu, QInputDialog, QMessageBox, QSlider
from PySide6.QtCore import Qt, Signal, Slot, QRectF
import pyqtgraph as pg
import numpy as np
import scipy.signal as sps

class SidebarSettings(QFrame):
    changeSpecgramContrastSignal = Signal(int)
    changeSpecgramLogScaleSignal = Signal(bool)

    def __init__(self,
        parent=None, f=Qt.WindowFlags()
    ):
        super().__init__(parent, f)

        # Outer layout
        self.layout = QVBoxLayout()
        self.setLayout(self.layout)

        # Initialise spectrogram groupbox
        self.initSpecgramGroupbox()



    def initSpecgramGroupbox(self):
        self.specgroupbox = QGroupBox("Spectrogram")
        self.speclayout = QFormLayout()
        self.specgroupbox.setLayout(self.speclayout)
        self.layout.addWidget(self.specgroupbox)

        # Add a colour slider control
        self.contrastSlider = QSlider(Qt.Horizontal)
        self.contrastSlider.setRange(1, 100)
        self.speclayout.addRow("Contrast", self.contrastSlider)
        # Connection
        self.contrastSlider.valueChanged.connect(self.changeSpecgramContrast)

        # Add Logarithmic view option
        self.logCheckbox = QCheckBox()
        self.speclayout.addRow("Logarithmic Scale", self.logCheckbox)
        # Connection
        self.logcheckbox.checked.connect(self.changeSpecgramLogScale)

    @Slot()
    def changeSpecgramContrast(self):
        percentile = self.contrastSlider.value()/100.0
        contrast = np.exp((percentile-1)/0.25)
        self.changeSpecgramContrastSignal.emit(contrast)
        # if self.sxxMax is not None:
        #     percentile = self.contrastSlider.value()/100.0
        #     contrast = np.exp((percentile-1)/0.25) * self.sxxMax # like a log2 squared contrast, this is more natural
        #     self.sp.setLevels([0, contrast])

    @Slot()
    def changeSpecgramLogScale(self):
        self.changeSpecgramLogScaleSignal.emit(self.logCheckbox.isChecked())



