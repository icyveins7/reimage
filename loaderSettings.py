'''
Reworked Settings Dialog.
Should now spawn upon loading of a file, not as a pre-set.
This gives more clarity as to what the current settings are,
and allows use-cases such as .wav file automatic sample rate filling.
'''

from PySide6.QtWidgets import QDialog, QVBoxLayout, QLineEdit, QFormLayout, QComboBox, QDialogButtonBox, QCheckBox, QGroupBox
from PySide6.QtWidgets import QSpinBox, QLabel, QHBoxLayout
from PySide6.QtCore import Qt, Signal, Slot
# import numpy as np
import configparser
import os

#%% Define the configs here
class LoaderSettingsConfig:
    loaderSettingsFile = "loaderSettings.ini"

    def __init__(self):
        # Create on init
        self.createDefaultConfigFile()

    def load(self):
        return configparser.ConfigParser(allow_no_value=True)

    def getSavedConfigs(self):
        return configparser.ConfigParser(allow_no_value=True).sections()

    def createDefaultConfigFile(self):
        cfg = self.load()
        cfg['DEFAULT'] = {
            "fmt": "complex int16",
            "headersize": "0",
            "usefixedlen": "False",
            "fixedlen": "-1",
            "invSpec": "False",
            ##### 
            'nperseg': "128",
            'noverlap': "16", # Note this is 128//8
            'fs': "1",
            'fc': "0.0",
            'freqshift': None, 
            'numTaps': None, 
            'filtercutoff': None,
            'dsr': None
        }
        # Write it if it doesn't exist
        if not os.path.exists(self.loaderSettingsFile):
            print("Generating default config for the first time.")
            with open(self.loaderSettingsFile, "w") as configfile:
                cfg.write(configfile)


#%%
class LoaderSettingsDialog(QDialog):
    filesettingsSignal = Signal(dict)
    signalsettingsSignal = Signal(dict)

    def __init__(self, filesettings: dict, signalsettings: dict, specialType: str=""):
        super().__init__()
        self.setWindowTitle("Settings")

        ## New config file source
        self.config = LoaderSettingsConfig()

        ## Layout
        self.layout = QVBoxLayout()
        self.configLayout = QHBoxLayout()
        self.layout.addLayout(self.configLayout)
        self.formatGroupBox = QGroupBox("File Format")
        self.layout.addWidget(self.formatGroupBox)
        self.viewerGroupBox = QGroupBox("Signal Viewer")
        self.layout.addWidget(self.viewerGroupBox)
        self.setLayout(self.layout)
        
        ## Buttons
        buttonBox = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttonBox.accepted.connect(self.accept)
        buttonBox.rejected.connect(self.reject)
        self.layout.addWidget(buttonBox)

        ################################# Configurations
        self.configDropdown = QComboBox()
        savedcfgs = self.config.getSavedConfigs()
        assert(isinstance(savedcfgs, list))
        savedcfgs.insert(0, 'DEFAULT')
        self.configDropdown.addItems(savedcfgs)
        self.configLayout.addWidget(self.configDropdown)

        ################################# File Format Layout
        self.formlayout = QFormLayout()
        self.formatGroupBox.setLayout(self.formlayout)

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

        ################################# Signal Viewer Layout
        self.sformlayout = QFormLayout()
        self.viewerGroupBox.setLayout(self.sformlayout)

        ## Options
        # Specgram nperseg
        self.specNpersegDropdown = QComboBox()
        self.specNpersegDropdown.addItems([str(2**i) for i in range(3,17)])
        self.specNpersegDropdown.setCurrentText(str(signalsettings['nperseg']))
        self.sformlayout.addRow("Spectrogram Window Size (samples)", self.specNpersegDropdown)

        # Specgram Noverlap
        nperseg = int(self.specNpersegDropdown.currentText())
        self.specNoverlapSpinbox = QSpinBox()
        self.specNoverlapSpinbox.setRange(0, nperseg-1)
        self.specNoverlapSpinbox.setValue(signalsettings['noverlap'])
        self.specNpersegDropdown.currentTextChanged.connect(self.onNpersegChanged)
        self.specNoverlapLabel = QLabel("Spectrogram Overlap (samples) [default: %d]" % (nperseg/8) )
        self.sformlayout.addRow(self.specNoverlapLabel, self.specNoverlapSpinbox)

        # Sample Rate
        self.fsEdit = QLineEdit(str(signalsettings['fs']))
        self.sformlayout.addRow("Sample Rate (samples per second)", self.fsEdit)

        # Centre Frequency (this is really just for display purposes)
        self.fcEdit = QLineEdit(str(signalsettings['fc']))
        self.sformlayout.addRow("Centre Frequency (Hz)", self.fcEdit)

        # Frequency shift
        self.freqshiftCheckbox = QCheckBox()
        self.sformlayout.addRow("Apply initial frequency shift?", self.freqshiftCheckbox)
        self.freqshiftEdit = QLineEdit(str(signalsettings['freqshift']) if signalsettings['freqshift'] is not None else None)
        self.freqshiftEdit.setEnabled(False)
        self.freqshiftCheckbox.toggled.connect(self.freqshiftEdit.setEnabled)
        self.sformlayout.addRow("Initial frequency shift (Hz)", self.freqshiftEdit)
        self.freqshiftCheckbox.setChecked(True if signalsettings['freqshift'] is not None else False)

        # Filtering
        self.filterCheckbox = QCheckBox()
        self.sformlayout.addRow("Apply filter?", self.filterCheckbox)
        self.numTapsDropdown = QComboBox()
        self.numTapsDropdown.addItems([str(2**i) for i in range(3,15)])
        self.numTapsDropdown.setCurrentText(str(signalsettings['numTaps']) if signalsettings['numTaps'] is not None else None)
        self.numTapsDropdown.setEnabled(False)
        self.cutoffEdit = QLineEdit(str(signalsettings['filtercutoff']) if signalsettings['filtercutoff'] is not None else None)
        self.cutoffEdit.setEnabled(False)
        self.filterCheckbox.toggled.connect(self.numTapsDropdown.setEnabled)
        self.filterCheckbox.toggled.connect(self.cutoffEdit.setEnabled)
        self.sformlayout.addRow("No. of Filter Taps", self.numTapsDropdown)
        self.sformlayout.addRow("Cutoff Frequency (Hz)", self.cutoffEdit)
        self.filterCheckbox.setChecked(True if signalsettings['numTaps'] is not None else False)

        # Downsampling
        self.downsampleCheckbox = QCheckBox()
        self.sformlayout.addRow("Apply downsampling?", self.downsampleCheckbox)
        self.downsampleEdit = QLineEdit(str(signalsettings['dsr']) if signalsettings['dsr'] is not None else None)
        self.downsampleEdit.setEnabled(False)
        self.downsampleCheckbox.toggled.connect(self.downsampleEdit.setEnabled)
        self.sformlayout.addRow("Downsample Rate", self.downsampleEdit)
        self.downsampleCheckbox.setChecked(True if signalsettings['dsr'] is not None else False)

        # Special type-handling
        if specialType != "":
            self.layout.addWidget(QLabel("Some settings have been automatically filled and/or disabled due to the file type."))
        if specialType == "wav":
            self.layout.addWidget(QLabel("Note that .wav files with more than one channel are averaged into one channel."))
            self.fsEdit.setEnabled(False)
            self.formatGroupBox.setEnabled(False)

        # Set focus to the most common setting
        self.fsEdit.setFocus()


    def accept(self):
        newFmtSettings = {
            "fmt": self.datafmtDropdown.currentText(),
            "headersize": int(self.headersizeEdit.text()),
            "usefixedlen": self.fixedlenCheckbox.isChecked(),
            "fixedlen": int(self.fixedlenEdit.text()),
            "invSpec": self.invertspecCheckbox.isChecked()
        }
        self.filesettingsSignal.emit(newFmtSettings)

        newViewerSettings = {
            'nperseg': int(self.specNpersegDropdown.currentText()),
            'noverlap': self.specNoverlapSpinbox.value(),
            'fs': int(self.fsEdit.text()),
            'fc': float(self.fcEdit.text()),
            'freqshift': float(self.freqshiftEdit.text()) if self.freqshiftCheckbox.isChecked() else None,
            'numTaps': int(self.numTapsDropdown.currentText()) if self.filterCheckbox.isChecked() else None,
            'filtercutoff': float(self.cutoffEdit.text()) if self.filterCheckbox.isChecked() else None,
            'dsr': int(self.downsampleEdit.text()) if self.downsampleCheckbox.isChecked() else None
        }
        self.signalsettingsSignal.emit(newViewerSettings)

        super().accept()
        
    @Slot(str)
    def onNpersegChanged(self, txt: str):
        # We edit the Noverlapdropdown
        nperseg = int(txt)
        self.specNoverlapSpinbox.setRange(0, nperseg-1)
        self.specNoverlapLabel.setText("Spectrogram Overlap (samples) [default: %d]" % (nperseg/8))
        self.specNoverlapSpinbox.setValue(nperseg/8)

