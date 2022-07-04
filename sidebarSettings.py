from PySide6.QtWidgets import QFrame, QVBoxLayout, QHBoxLayout, QGroupBox, QFormLayout, QCheckBox, QStyle, QWidget
from PySide6.QtWidgets import QPushButton, QLabel, QLineEdit, QInputDialog, QMessageBox, QSlider, QSizePolicy, QRadioButton
from PySide6.QtWidgets import QColorDialog, QMessageBox
from PySide6.QtCore import Qt, Signal, Slot, QRectF
import numpy as np
import scipy.signal as sps
from functools import partial

class SidebarSettings(QFrame):
    changeSpecgramContrastSignal = Signal(float, bool)
    changeSpecgramLogScaleSignal = Signal(bool)
    addSmaSignal = Signal(int)
    changeAmpPlotSignal = Signal(str)

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

        # Initialise amp-plot groupbox
        self.initAmpPlotGroupbox()

        # Initialise spectrogram groupbox
        self.initSpecgramGroupbox()

        # At the end, add a stretch
        self.settingsLayout.addStretch()

    ############### Amplitude-plot settings
    def initAmpPlotGroupbox(self):
        self.ampplotgroupbox = QGroupBox("Amplitude-Time Plot")
        self.ampplotlayout = QFormLayout()
        self.ampplotgroupbox.setLayout(self.ampplotlayout)
        self.settingsLayout.addWidget(self.ampplotgroupbox)

        # Add real/imag view
        self.reimgroupbox = QGroupBox()
        self.reimgrouplayout = QHBoxLayout()
        self.reimgroupbox.setLayout(self.reimgrouplayout)
        self.ampviewBtn = QRadioButton("Amplitude")
        self.ampviewBtn.setChecked(True)
        self.reimgrouplayout.addWidget(self.ampviewBtn)
        self.reimviewBtn = QRadioButton("Real/Imag")
        self.reimgrouplayout.addWidget(self.reimviewBtn)
        self.ampplotlayout.addRow("Plot Type", self.reimgroupbox)
        # Connection
        self.reimgroupbox.clicked.connect(self.changeAmpPlotType) # not working?
        

        # Add average filter options
        self.smalens = {}
        self.addsmaBtn = QPushButton("Add")
        self.ampplotlayout.addRow("Moving Average", self.addsmaBtn)
        # Connection
        self.addsmaBtn.clicked.connect(self.addsma)
        
    @Slot()
    def changeAmpPlotType(self):
        s = "amp" if self.ampviewBtn.isChecked() else "reim"
        self.changeAmpPlotSignal.emit(s)
        print(s) # debug

    @Slot()
    def addsma(self):
        val, ok = QInputDialog.getInt(self,
            "Add New Moving Average",
            "Moving Average Length: ",
            value=25
        )

        if ok:
            self.addSmaSignal.emit(val)
            # Add a row internally as well
            if val not in self.smalens:
                # Create the widget that contains the others
                hwidget = QWidget()
                hlayout = QHBoxLayout()
                hwidget.setLayout(hlayout)

                # Deletion button
                smadelBtn = QPushButton(parent=hwidget) # Ensure child deletion
                smadelBtn.setIcon(self.style().standardIcon(QStyle.SP_DialogCancelButton))
                # Connection
                smadelBtn.clicked.connect(partial(self.deleteSma, val))
                
                # Color Button
                smaColorBtn = QPushButton("Color", parent=hwidget)
                # Connection
                smaColorBtn.clicked.connect(self.colourSma)

                # Add to the UI
                hlayout.addWidget(smadelBtn)
                hlayout.addWidget(smaColorBtn)
                self.ampplotlayout.addRow("MA: %d" % (val), hwidget)
                # Add to internals
                self.smalens[val] = hwidget

            else:
                # Display error dialog
                _ = QMessageBox.critical(self, "Moving Average Error",
                    "Repeat moving average lengths are not allowed."
                )

            print(self.smalens)

    @Slot()
    def deleteSma(self, val: int):
        # Remove from the UI
        self.ampplotlayout.removeRow(self.smalens[val])
        # Remove from internals
        self.smalens.pop(val)
        # TODO: emit appropriate signal
        pass

    @Slot()
    def colourSma(self):
        colour = QColorDialog.getColor(Qt.red, self)

        if colour.isValid():
            print(colour)
            # Working correctly up to here
            # TODO: emit appropriate signal


    ############### Specgram settings
    def initSpecgramGroupbox(self):
        self.specgroupbox = QGroupBox("Spectrogram")
        self.specgroupbox.setMinimumWidth(250) # Use this to size the entire layout
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
        # Must reset contrast bar
        self.contrastSlider.setValue(0)



