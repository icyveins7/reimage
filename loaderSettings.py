'''
Reworked Settings Dialog.
Should now spawn upon loading of a file, not as a pre-set.
This gives more clarity as to what the current settings are,
and allows use-cases such as .wav file automatic sample rate filling.
'''

from PySide6.QtWidgets import QDialog, QVBoxLayout, QLineEdit, QFormLayout, QComboBox, QDialogButtonBox, QCheckBox, QGroupBox
from PySide6.QtWidgets import QSpinBox, QLabel, QHBoxLayout, QPushButton, QInputDialog
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

    def _write(self, cfg):
        with open(self.loaderSettingsFile, "w") as configfile:
            cfg.write(configfile)

    def load(self):
        c = configparser.ConfigParser(allow_no_value=True)
        c.optionxform = lambda option: option # Ensure upper case is preserved
        return c

    def read(self):
        cfg = self.load()
        cfg.read(self.loaderSettingsFile)
        return cfg

    def getSavedConfigs(self):
        cfg = self.read()
        return cfg.sections()

    def getConfig(self, cfgname: str):
        cfg = self.read()
        return cfg[cfgname]

    def saveConfig(self, newcfgname: str, newcfg: dict):
        cfg = self.load()
        cfg.read(self.loaderSettingsFile)
        cfg[newcfgname] = newcfg
        self._write(cfg)

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
            self._write(cfg)


#%%
class LoaderSettingsDialog(QDialog):
    settingsSignal = Signal(dict)
    configSignal = Signal(str)

    def __init__(self, specialType: str="", configName: str="DEFAULT", wavSamplerate: int=None):
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
        self.configDropdown.textActivated.connect(self._loadSelectedConfigToUI) # Use textActivated so it doesn't fire on construction
        self._populateConfigs()
        self.configLayout.addWidget(self.configDropdown)

        self.addConfigBtn = QPushButton("Save Config")
        self.addConfigBtn.setFixedWidth(100)
        self.addConfigBtn.clicked.connect(self.onNewConfig)
        self.configLayout.addWidget(self.addConfigBtn)

        ################################# File Format Layout
        self.formlayout = QFormLayout()
        self.formatGroupBox.setLayout(self.formlayout)

        ## Options
        # Data type
        self.datafmtDropdown = QComboBox()
        dataformats = ["complex int16", "complex float32", "complex float64"]
        self.datafmtDropdown.addItems(dataformats)
        self.formlayout.addRow("File Data Type", self.datafmtDropdown)

        # Header size
        self.headersizeEdit = QLineEdit()
        self.formlayout.addRow("Header Length (bytes)", self.headersizeEdit)

        # Fixed Length
        self.fixedlenCheckbox = QCheckBox()
        self.fixedlenEdit = QLineEdit()
        self.fixedlenCheckbox.toggled.connect(self.fixedlenEdit.setEnabled)
        self.formlayout.addRow("Use Fixed Length Per File", self.fixedlenCheckbox)
        self.formlayout.addRow("Data Length Per File (samples)", self.fixedlenEdit)

        # Inverted Spectrum
        self.invertspecCheckbox = QCheckBox()
        self.formlayout.addRow("Inverted Spectrum?", self.invertspecCheckbox)

        ################################# Signal Viewer Layout
        self.sformlayout = QFormLayout()
        self.viewerGroupBox.setLayout(self.sformlayout)

        ## Options
        # Specgram nperseg
        self.specNpersegDropdown = QComboBox()
        self.specNpersegDropdown.addItems([str(2**i) for i in range(3,17)])
        self.sformlayout.addRow("Spectrogram Window Size (samples)", self.specNpersegDropdown)

        # Specgram Noverlap
        nperseg = int(self.specNpersegDropdown.currentText())
        self.specNoverlapSpinbox = QSpinBox()
        self.specNoverlapSpinbox.setRange(0, nperseg-1)
        self.specNpersegDropdown.currentTextChanged.connect(self.onNpersegChanged)
        self.specNoverlapLabel = QLabel("Spectrogram Overlap (samples) [default: %d]" % (nperseg/8) )
        self.sformlayout.addRow(self.specNoverlapLabel, self.specNoverlapSpinbox)

        # Sample Rate
        self.fsEdit = QLineEdit()
        self.sformlayout.addRow("Sample Rate (samples per second)", self.fsEdit)

        # Centre Frequency (this is really just for display purposes)
        self.fcEdit = QLineEdit()
        self.sformlayout.addRow("Centre Frequency (Hz)", self.fcEdit)

        # Frequency shift
        self.freqshiftCheckbox = QCheckBox()
        self.sformlayout.addRow("Apply initial frequency shift?", self.freqshiftCheckbox)
        self.freqshiftEdit = QLineEdit()
        self.freqshiftCheckbox.toggled.connect(self.freqshiftEdit.setEnabled)
        self.sformlayout.addRow("Initial frequency shift (Hz)", self.freqshiftEdit)

        # Filtering
        self.filterCheckbox = QCheckBox()
        self.sformlayout.addRow("Apply filter?", self.filterCheckbox)
        self.numTapsDropdown = QComboBox()
        self.numTapsDropdown.addItems([str(2**i) for i in range(3,15)])
        self.cutoffEdit = QLineEdit()
        self.filterCheckbox.toggled.connect(self.numTapsDropdown.setEnabled)
        self.filterCheckbox.toggled.connect(self.cutoffEdit.setEnabled)
        self.sformlayout.addRow("No. of Filter Taps", self.numTapsDropdown)
        self.sformlayout.addRow("Cutoff Frequency (Hz)", self.cutoffEdit)

        # Downsampling
        self.downsampleCheckbox = QCheckBox()
        self.sformlayout.addRow("Apply downsampling?", self.downsampleCheckbox)
        self.downsampleEdit = QLineEdit()
        self.downsampleCheckbox.toggled.connect(self.downsampleEdit.setEnabled)
        self.sformlayout.addRow("Downsample Rate", self.downsampleEdit)

        # Special type-handling
        if specialType != "":
            self.layout.addWidget(QLabel("Some settings have been automatically filled and/or disabled due to the file type."))
        if specialType == "wav":
            self.layout.addWidget(QLabel("Note that .wav files with more than one channel are averaged into one channel."))
            self.fsEdit.setText(str(wavSamplerate))
            self.fsEdit.setEnabled(False)
            self.formatGroupBox.setEnabled(False)

        # Set UI based on config
        self.configDropdown.setCurrentText(configName)
        self._loadSelectedConfigToUI(configName)

        # Set focus to the most common setting
        self.fsEdit.setFocus()


    def accept(self):
        # Parse types for the settings
        newsettings = {
            "fmt": self.datafmtDropdown.currentText(),
            "headersize": int(self.headersizeEdit.text()),
            "usefixedlen": self.fixedlenCheckbox.isChecked(),
            "fixedlen": int(self.fixedlenEdit.text()) if self.fixedlenEdit.isEnabled() else -1,
            "invSpec": self.invertspecCheckbox.isChecked(),
            ###########################
            'nperseg': int(self.specNpersegDropdown.currentText()),
            'noverlap': self.specNoverlapSpinbox.value(),
            'fs': int(self.fsEdit.text()),
            'fc': float(self.fcEdit.text()),
            'freqshift': float(self.freqshiftEdit.text()) if self.freqshiftCheckbox.isChecked() else None,
            'numTaps': int(self.numTapsDropdown.currentText()) if self.filterCheckbox.isChecked() else None,
            'filtercutoff': float(self.cutoffEdit.text()) if self.filterCheckbox.isChecked() else None,
            'dsr': int(self.downsampleEdit.text()) if self.downsampleCheckbox.isChecked() else None
        }
        self.settingsSignal.emit(newsettings)

        # Before accepting, we check if the current settings match the current config
        loadedConfig = self.config.getConfig(self.configDropdown.currentText()) # This is a config object
        currentConfig = self._packSettings() # This is a dict
        if dict(loadedConfig) == currentConfig:
            # Then we return the currentConfig name
            self.configSignal.emit(self.configDropdown.currentText())
        else:
            print(dict(loadedConfig))
            print(currentConfig)
            # Generate a new 'Custom' config and return that
            self.config.saveConfig('Custom', self._packSettings())
            self.configSignal.emit('Custom')
            
        super().accept()
        
    @Slot(str)
    def onNpersegChanged(self, txt: str):
        # We edit the Noverlapdropdown
        nperseg = int(txt)
        self.specNoverlapSpinbox.setRange(0, nperseg-1)
        self.specNoverlapLabel.setText("Spectrogram Overlap (samples) [default: %d]" % (nperseg/8))
        self.specNoverlapSpinbox.setValue(nperseg/8)

    ########### These methods are related to config wrangling
    @Slot(str)
    def _loadSelectedConfigToUI(self, cfgname: str):
        cfg = self.config.getConfig(cfgname)

        # Data type
        self.datafmtDropdown.setCurrentText(cfg.get('fmt'))

        # Header size
        self.headersizeEdit.setText(cfg.get('headersize'))

        # Fixed Length
        if cfg.getboolean('usefixedlen'):
            self.fixedlenCheckbox.setChecked(True)
            self.fixedlenEdit.setEnabled(True)
            self.fixedlenEdit.setText(cfg.get('fixedlen'))
        else:
            self.fixedlenCheckbox.setChecked(False)
            self.fixedlenEdit.setEnabled(False)

        # Inverted Spectrum
        self.invertspecCheckbox.setChecked(cfg.getboolean('invSpec'))

        #################################
        # Specgram nperseg
        self.specNpersegDropdown.setCurrentText(cfg.get('nperseg'))

        # Specgram Noverlap
        self.specNoverlapSpinbox.setValue(cfg.getint('noverlap'))

        # Sample Rate
        self.fsEdit.setText(cfg.get('fs'))

        # Centre Frequency (this is really just for display purposes)
        self.fcEdit.setText(cfg.get('fc'))

        # Frequency shift
        if cfg.get('freqshift') is not None:
            self.freqshiftCheckbox.setChecked(True)
            self.freqshiftEdit.setEnabled(True)
            self.freqshiftEdit.setText(cfg.get('freqshift'))
        else:
            self.freqshiftCheckbox.setChecked(False)
            self.freqshiftEdit.setEnabled(False)

        # Filtering
        if cfg.get('numTaps') is not None:
            self.filterCheckbox.setChecked(True)
            self.numTapsDropdown.setEnabled(True)
            self.numTapsDropdown.setCurrentText(cfg.get('numTaps'))
            self.cutoffEdit.setEnabled(True)
            self.cutoffEdit.setText(cfg.get('filtercutoff'))
        else:
            self.filterCheckbox.setChecked(False)
            self.numTapsDropdown.setEnabled(False)
            self.cutoffEdit.setEnabled(False)

        # Downsampling
        if cfg.get('dsr') is not None:
            self.downsampleCheckbox.setChecked(True)
            self.downsampleEdit.setEnabled(True)
            self.downsampleEdit.setText(cfg.get('dsr'))
        else:
            self.downsampleCheckbox.setChecked(False)
            self.downsampleEdit.setEnabled(False)

    def _packSettings(self):
        settings = {
            "fmt": self.datafmtDropdown.currentText(),
            "headersize": self.headersizeEdit.text(),
            "usefixedlen": str(self.fixedlenCheckbox.isChecked()),
            "fixedlen": self.fixedlenEdit.text() if self.fixedlenCheckbox.isChecked() else "-1",
            "invSpec": str(self.invertspecCheckbox.isChecked()),
            'nperseg': self.specNpersegDropdown.currentText(),
            'noverlap': str(self.specNoverlapSpinbox.value()),
            'fs': self.fsEdit.text(),
            'fc': self.fcEdit.text(),
            'freqshift': self.freqshiftEdit.text() if self.freqshiftCheckbox.isChecked() else None,
            'numTaps': self.numTapsDropdown.currentText() if self.filterCheckbox.isChecked() else None,
            'filtercutoff': self.cutoffEdit.text() if self.filterCheckbox.isChecked() else None,
            'dsr': self.downsampleEdit.text() if self.downsampleCheckbox.isChecked() else None
        }
        return settings

    def _populateConfigs(self):
        savedcfgs = self.config.getSavedConfigs()
        savedcfgs.insert(0, 'DEFAULT')
        self.configDropdown.clear()
        self.configDropdown.addItems(savedcfgs)

    @Slot()
    def onNewConfig(self):
        # Spawn a dialog
        newcfgname, ok = QInputDialog().getText(self, "Specify config name", "New config name (or overwrite an existing one):")

        # If dialog ok, save to file and repopulate the dropdown
        if ok:
            newcfg = self._packSettings()
            self.config.saveConfig(newcfgname, newcfg)
            self._populateConfigs()
            # Set to the new name
            self.configDropdown.setCurrentText(newcfgname)

