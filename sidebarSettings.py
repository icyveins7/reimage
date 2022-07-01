from PySide6.QtWidgets import QFrame, QVBoxLayout, QHBoxLayout, QGroupBox, QFormLayout, QCheckBox, QStyle, QWidget
from PySide6.QtWidgets import QPushButton, QLabel, QLineEdit, QInputDialog, QMessageBox, QSlider, QSizePolicy
from PySide6.QtCore import Qt, Signal, Slot, QRectF
import numpy as np
import scipy.signal as sps

class SidebarSettings(QFrame):
    changeSpecgramContrastSignal = Signal(float, bool)
    changeSpecgramLogScaleSignal = Signal(bool)

    def __init__(self,
        parent=None, f=Qt.WindowFlags()
    ):
        super().__init__(parent, f)

        # Outer layout
        self.layout = QHBoxLayout()
        self.settingsWidget = QWidget() # Used to hide/show
        self.settingsLayout = QVBoxLayout()
        self.settingsWidget.setLayout(self.settingsLayout)
        self.setLayout(self.layout)

        # Add the hide button
        self.hideBtn = QPushButton()
        self.hideBtn.setSizePolicy(QSizePolicy.Maximum, QSizePolicy.Expanding)
        self.hideBtn.setIcon(self.style().standardIcon(QStyle.SP_ToolBarHorizontalExtensionButton))
        self.hideBtn.clicked.connect(self.toggleSidebar)
        self.layout.addWidget(self.hideBtn)
        # And the actual settings layout
        self.layout.addWidget(self.settingsWidget)
        # Start out hidden
        self.settingsWidget.hide()

        # Initialise spectrogram groupbox
        self.initSpecgramGroupbox()



    def initSpecgramGroupbox(self):
        self.specgroupbox = QGroupBox("Spectrogram")
        self.specgroupbox.setMinimumWidth(300) # Use this to size the entire layout
        self.speclayout = QFormLayout()
        self.specgroupbox.setLayout(self.speclayout)
        self.settingsLayout.addWidget(self.specgroupbox)

        # Add a colour slider control
        self.contrastSlider = QSlider(Qt.Horizontal)
        self.contrastSlider.setRange(0, 99)
        self.speclayout.addRow("Contrast", self.contrastSlider)
        # Connection
        self.contrastSlider.valueChanged.connect(self.changeSpecgramContrast)

        # Add Logarithmic view option
        self.logCheckbox = QCheckBox()
        self.speclayout.addRow("Logarithmic Scale", self.logCheckbox)
        # Connection
        self.logCheckbox.stateChanged.connect(self.changeSpecgramLogScale)

    @Slot()
    def resetSpecgramGroupbox(self):
        self.contrastSlider.setValue(0)
        self.logCheckbox.setChecked(False)


    @Slot()
    def toggleSidebar(self):
        if self.settingsWidget.isHidden():
            self.settingsWidget.show()
        else:
            self.settingsWidget.hide()

    @Slot()
    def changeSpecgramContrast(self):
        percentile = (100 - self.contrastSlider.value())/100.0
        # percentile = np.exp((percentile-1)/0.25) # Scale log? don't use this any more
        self.changeSpecgramContrastSignal.emit(percentile, self.logCheckbox.isChecked())

    @Slot()
    def changeSpecgramLogScale(self):
        self.changeSpecgramLogScaleSignal.emit(self.logCheckbox.isChecked())



