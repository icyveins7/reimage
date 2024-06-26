'''
Reworked Settings Dialog.
Should now spawn upon loading of a file, not as a pre-set.
This gives more clarity as to what the current settings are,
and allows use-cases such as .wav file automatic sample rate filling.
'''

from PySide6.QtWidgets import QDialog, QVBoxLayout, QLineEdit, QFormLayout
from PySide6.QtWidgets import QComboBox, QDialogButtonBox, QCheckBox
from PySide6.QtWidgets import QGroupBox, QMessageBox
from PySide6.QtWidgets import QSpinBox, QLabel, QHBoxLayout
from PySide6.QtWidgets import QPushButton, QInputDialog, QSlider
from PySide6.QtCore import Qt, Signal, Slot
# import numpy as np
import configparser
import os

# %% Define the configs here


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
        c.optionxform = lambda option: option  # Ensure upper case is preserved
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
            "swapEndian": "False",
            "headersize": "0",
            "usefixedlen": "False",
            "fixedlen": "-1",
            "invSpec": "False",
            #####
            'nperseg': "128",
            'noverlap': "16",  # Note this is 128//8
            'fs': "1",
            'fc': "0.0",
            'freqshift': None,
            'numTaps': None,
            'filtercutoff': None,
            'dsr': None,
            'sampleStart': "0"
        }
        # Write it if it doesn't exist
        if not os.path.exists(self.loaderSettingsFile):
            print("Generating default config for the first time.")
            self._write(cfg)


# %%
class LoaderSettingsDialog(QDialog):
    settingsSignal = Signal(dict)
    configSignal = Signal(str)

    bytesPerSample = {
        "complex int16": 4,
        "complex float32": 8,
        "complex float64": 16
    }

    def __init__(self, specialType: str = "", configName: str = "DEFAULT", wavSamplerate: int = None, filepaths: list = None):
        super().__init__()
        self.setWindowTitle("Settings")

        # Calculate the filesizes for each file, to be used in further calculations later
        self.filesizes = [os.path.getsize(filepath) for filepath in filepaths]

        # New config file source
        self.config = LoaderSettingsConfig()

        # Layout
        self.layout = QVBoxLayout()
        self.configLayout = QHBoxLayout()
        self.layout.addLayout(self.configLayout)
        self.formatGroupBox = QGroupBox("File Format")
        self.layout.addWidget(self.formatGroupBox)
        self.viewerGroupBox = QGroupBox("Signal Viewer")
        self.layout.addWidget(self.viewerGroupBox)
        self.setLayout(self.layout)

        # Buttons
        buttonBox = QDialogButtonBox(
            QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttonBox.accepted.connect(self.accept)
        buttonBox.rejected.connect(self.reject)
        self.layout.addWidget(buttonBox)

        # Configurations
        self.configDropdown = QComboBox()
        # Use textActivated so it doesn't fire on construction
        self.configDropdown.textActivated.connect(self._loadSelectedConfigToUI)
        self._populateConfigs()
        self.configLayout.addWidget(self.configDropdown)

        self.addConfigBtn = QPushButton("Save Config")
        self.addConfigBtn.setFixedWidth(100)
        self.addConfigBtn.clicked.connect(self.onNewConfig)
        self.configLayout.addWidget(self.addConfigBtn)

        # File Format Layout
        self.formlayout = QFormLayout()
        self.formatGroupBox.setLayout(self.formlayout)

        # Options
        # Data type
        self.datafmtDropdown = QComboBox()
        dataformats = [key for key in self.bytesPerSample]
        self.datafmtDropdown.addItems(dataformats)
        self.datafmtDropdown.currentTextChanged.connect(self.onDataFmtChanged)
        self.formlayout.addRow("File Data Type", self.datafmtDropdown)

        # Endianness
        self.endiannessCheckBox = QCheckBox()
        self.formlayout.addRow("Swap endian-ness", self.endiannessCheckBox)

        # Header size
        self.headersizeEdit = QLineEdit()
        self.headersizeEdit.textEdited.connect(self.onHeaderSizeChanged)
        self.formlayout.addRow("Header Length (bytes)", self.headersizeEdit)

        # New sliders (only show when there is only 1 file)
        if len(self.filesizes) == 1:
            self.sliderMax = self.filesizes[0] // self.bytesPerSample[self.datafmtDropdown.currentText()]
            # The Qt widgets only accept up to signed integers, so we use this as an arbitrary limit
            self.sliderMax = 1000000000 if self.sliderMax > 1000000000 else self.sliderMax

            self.sampleRangeLabel = QLabel("-")
            self.sampleStartEdit = QLineEdit()
            self.sampleEndEdit = QLineEdit()
            # Connect backwards to sliders as well
            self.sampleStartEdit.textEdited.connect(
                self.onSampleStartTextEdited)
            self.sampleEndEdit.textEdited.connect(self.onSampleEndTextEdited)

            # Stack these 3 into 1 cell
            self.sampleDisplayLayout = QHBoxLayout()
            self.sampleDisplayLayout.addWidget(self.sampleStartEdit)
            self.sampleDisplayLayout.addWidget(self.sampleRangeLabel)
            self.sampleDisplayLayout.addWidget(self.sampleEndEdit)

            self.sampleStartSlider = QSlider()
            self.sampleStartSlider.setOrientation(Qt.Horizontal)
            self.sampleStartSlider.setMinimum(0)
            # We set maximums at the end
            self.sampleStartSlider.valueChanged.connect(
                self.onSampleStartChanged)
            self.formlayout.addRow("Start Sample", self.sampleStartSlider)

            self.sampleEndSlider = QSlider()
            self.sampleEndSlider.setOrientation(Qt.Horizontal)
            self.sampleEndSlider.setMinimum(1)
            # We set maximums at the end
            self.sampleEndSlider.valueChanged.connect(self.onSampleEndChanged)
            # Call the updater here
            self._updateSampleSliderMax()
            # Default to selecting all of it
            self.sampleEndSlider.setValue(self.sampleEndSlider.maximum())
            self.formlayout.addRow("End Sample", self.sampleEndSlider)

            self.updateSampleRangeLabel()
            # self.formlayout.addRow("Sample Range", self.sampleRangeLabel)
            self.formlayout.addRow("Sample Range", self.sampleDisplayLayout)
        else:
            # Fixed Length
            self.fixedlenCheckbox = QCheckBox()
            self.fixedlenEdit = QLineEdit()
            self.fixedlenCheckbox.toggled.connect(self.fixedlenEdit.setEnabled)
            self.formlayout.addRow(
                "Use Fixed Length Per File", self.fixedlenCheckbox)
            self.formlayout.addRow(
                "Data Length Per File (samples)", self.fixedlenEdit)

        # Inverted Spectrum
        self.invertspecCheckbox = QCheckBox()
        self.formlayout.addRow("Inverted Spectrum?", self.invertspecCheckbox)

        # Signal Viewer Layout
        self.sformlayout = QFormLayout()
        self.viewerGroupBox.setLayout(self.sformlayout)

        # Options
        # Specgram nperseg
        self.specNpersegDropdown = QComboBox()
        self.specNpersegDropdown.addItems([str(2**i) for i in range(3, 17)])
        self.sformlayout.addRow(
            "Spectrogram Window Size (samples)", self.specNpersegDropdown)

        # Specgram Noverlap
        nperseg = int(self.specNpersegDropdown.currentText())
        self.specNoverlapSpinbox = QSpinBox()
        self.specNoverlapSpinbox.setRange(0, nperseg-1)
        self.specNpersegDropdown.currentTextChanged.connect(
            self.onNpersegChanged)
        self.specNoverlapLabel = QLabel(
            "Spectrogram Overlap (samples) [default: %d]" % (nperseg/8))
        self.sformlayout.addRow(self.specNoverlapLabel,
                                self.specNoverlapSpinbox)

        # Sample Rate
        self.fsEdit = QLineEdit()
        self.sformlayout.addRow(
            "Sample Rate (samples per second)", self.fsEdit)

        # Centre Frequency (this is really just for display purposes)
        self.fcEdit = QLineEdit()
        self.fcEdit.setToolTip(
            "This is used for display purposes only.\n "
            "To actually shift the centre frequency of the signal, \n"
            "use the frequency shift options below."
        )
        self.sformlayout.addRow("Centre Frequency of Recording (Hz)",
                                self.fcEdit)

        # Frequency shift
        self.freqshiftCheckbox = QCheckBox()
        self.sformlayout.addRow(
            "Apply initial frequency shift?", self.freqshiftCheckbox)
        self.freqshiftEdit = QLineEdit()
        self.freqshiftCheckbox.toggled.connect(self.freqshiftEdit.setEnabled)
        self.sformlayout.addRow(
            "Initial frequency shift (Hz)", self.freqshiftEdit)
        self.finalFcEdit = QLineEdit()
        self.finalFcEdit.setEnabled(False)
        self.freqshiftEdit.textEdited.connect(self.onFreqShiftChanged)
        self.sformlayout.addRow(
            "Final centre frequency (Hz)", self.finalFcEdit)

        # Filtering
        self.filterCheckbox = QCheckBox()
        self.sformlayout.addRow("Apply filter?", self.filterCheckbox)
        self.numTapsDropdown = QComboBox()
        self.numTapsDropdown.addItems([str(2**i) for i in range(3, 15)])
        self.cutoffEdit = QLineEdit()
        self.filterCheckbox.toggled.connect(self.numTapsDropdown.setEnabled)
        self.filterCheckbox.toggled.connect(self.cutoffEdit.setEnabled)
        self.sformlayout.addRow("No. of Filter Taps", self.numTapsDropdown)
        self.sformlayout.addRow("Cutoff Frequency (Hz)", self.cutoffEdit)

        # Downsampling
        self.downsampleCheckbox = QCheckBox()
        self.sformlayout.addRow("Apply downsampling?", self.downsampleCheckbox)
        self.downsampleEdit = QLineEdit()
        self.downsampleEdit.textEdited.connect(self.onDownsampleChanged)
        self.downsampleCheckbox.toggled.connect(self.downsampleEdit.setEnabled)
        self.sformlayout.addRow("Downsample Rate", self.downsampleEdit)
        self.fsAfterDownsampleEdit = QLineEdit()
        self.fsAfterDownsampleEdit.setEnabled(False)
        self.sformlayout.addRow(
            "Sample Rate After Downsampling", self.fsAfterDownsampleEdit)

        # Special type-handling
        if specialType != "":
            self.layout.addWidget(QLabel(
                "Some settings have been automatically filled and/or disabled due to the file type."))
        if specialType == "wav":
            self.layout.addWidget(QLabel(
                "Note that .wav files with more than one channel are averaged into one channel."))
            self.fsEdit.setText(str(wavSamplerate))
            self.fsEdit.setEnabled(False)
            self.formatGroupBox.setEnabled(False)

        # Set UI based on config
        self.configDropdown.setCurrentText(configName)
        self._loadSelectedConfigToUI(configName)

        # Set focus to the most common setting
        self.fsEdit.setFocus()

    ############################################
    # These methods are used to deal with single long
    # files and the slider/label widgets

    @Slot(str)
    def onDataFmtChanged(self, text: str):
        # Redirect to the updater
        self._updateSampleSliderMax()
        self.updateSampleRangeLabel()

    @Slot(str)
    def onHeaderSizeChanged(self, text: str):
        # Redirect to the updater
        self._updateSampleSliderMax()
        self.updateSampleRangeLabel()

    def _updateSampleSliderMax(self):
        headerBytes = int(self.headersizeEdit.text()
                          ) if self.headersizeEdit.text() != "" else 0
        expectedSamples = self.parseExpectedSamplesInFiles(
            headerBytes,
            self.bytesPerSample[self.datafmtDropdown.currentText()]
        )

        # Amend the maximum sample ranges
        self.sliderMax = expectedSamples[0]
        # The Qt widgets only accept up to signed integers, so we use this as an arbitrary limit
        self.sliderMax = 1000000000 if self.sliderMax > 1000000000 else self.sliderMax

        self.sampleStartSlider.setMaximum(self.sliderMax)
        self.sampleEndSlider.setMaximum(self.sliderMax)

    def updateSampleRangeLabel(self):
        span = self.sampleStartSlider.maximum() - self.sampleStartSlider.minimum()
        # Yes, yes this is repeated.. TODO
        headerBytes = int(self.headersizeEdit.text()
                          ) if self.headersizeEdit.text() != "" else 0
        expectedSamples = self.parseExpectedSamplesInFiles(
            headerBytes,
            self.bytesPerSample[self.datafmtDropdown.currentText()]
        )
        # We print the actual samples used, even though the slider is limited to int32 range
        start = float(self.sampleStartSlider.value()) / \
            span * expectedSamples[0]
        print(start)
        print("%d/%d" % (self.sampleStartSlider.value(),
              self.sampleStartSlider.maximum()))
        end = float(self.sampleEndSlider.value()) / span * expectedSamples[0]
        print(end)
        print("%d/%d" % (self.sampleEndSlider.value(),
              self.sampleEndSlider.maximum()))

        self.sampleStartEdit.setText(str(int(start)))
        self.sampleEndEdit.setText(str(int(end)))

    @Slot(str)
    def onSampleStartTextEdited(self, text: str):
        span = self.sampleStartSlider.maximum() - self.sampleStartSlider.minimum()
        # Yes, yes this is repeated.. TODO
        headerBytes = int(self.headersizeEdit.text()
                          ) if self.headersizeEdit.text() != "" else 0
        expectedSamples = self.parseExpectedSamplesInFiles(
            headerBytes,
            self.bytesPerSample[self.datafmtDropdown.currentText()]
        )

        if text != '':
            if int(text) < 0:
                self.sampleStartEdit.setText('0')
                self.sampleStartSlider.setValue(
                    self.sampleStartSlider.minimum())
            else:
                value = int(text) / expectedSamples[0] * span
                oldstate = self.sampleStartSlider.blockSignals(True)
                self.sampleStartSlider.setValue(value)
                self.sampleStartSlider.blockSignals(oldstate)

    @Slot(str)
    def onSampleEndTextEdited(self, text: str):
        span = self.sampleStartSlider.maximum() - self.sampleStartSlider.minimum()
        # Yes, yes this is repeated.. TODO
        headerBytes = int(self.headersizeEdit.text()
                          ) if self.headersizeEdit.text() != "" else 0
        expectedSamples = self.parseExpectedSamplesInFiles(
            headerBytes,
            self.bytesPerSample[self.datafmtDropdown.currentText()]
        )

        if text != '':
            if int(text) > expectedSamples[0]:
                self.sampleEndEdit.setText(str(expectedSamples[0]))
                self.sampleEndSlider.setValue(self.sampleEndSlider.maximum())
            else:
                value = int(text) / expectedSamples[0] * span
                oldstate = self.sampleEndSlider.blockSignals(True)
                self.sampleEndSlider.setValue(value)
                self.sampleEndSlider.blockSignals(oldstate)

    @Slot(int)
    def onSampleStartChanged(self, value: int):
        # Not allowed to go past the maximum slider value
        if self.sampleStartSlider.value() > self.sampleEndSlider.value():
            self.sampleEndSlider.setValue(self.sampleStartSlider.value()+1)

        # Update the label
        self.updateSampleRangeLabel()

    @Slot()
    def onSampleEndChanged(self):
        # Not allowed to go past the minimum slider value
        if self.sampleEndSlider.value() < self.sampleStartSlider.value():
            self.sampleStartSlider.setValue(self.sampleEndSlider.value()-1)

        # Update the label
        self.updateSampleRangeLabel()

    def parseExpectedSamplesInFiles(self, headerBytes: int, bytesPerSample: int):
        """
        Parse the expected number of samples in each file.
        """
        return [(i-headerBytes) // bytesPerSample for i in self.filesizes]

    ########################################################################
    def parseSettings(self) -> dict:
        # Parse types for the settings
        newsettings = {
            "fmt": self.datafmtDropdown.currentText(),
            "headersize": int(self.headersizeEdit.text()),

            # "usefixedlen": self.fixedlenCheckbox.isChecked(),
            # "fixedlen": int(self.fixedlenEdit.text()) if self.fixedlenEdit.isEnabled() else -1,
            "swapEndian": self.endiannessCheckBox.isChecked(),
            "invSpec": self.invertspecCheckbox.isChecked(),
            ###########################
            'nperseg': int(self.specNpersegDropdown.currentText()),
            'noverlap': self.specNoverlapSpinbox.value(),
            'fs': int(float(self.fsEdit.text())),
            'fc': float(self.fcEdit.text()) + float(self.freqshiftEdit.text()) if self.freqshiftCheckbox.isChecked() else 0,
            'freqshift': float(self.freqshiftEdit.text()) if self.freqshiftCheckbox.isChecked() else None,
            'numTaps': int(self.numTapsDropdown.currentText()) if self.filterCheckbox.isChecked() else None,
            'filtercutoff': float(self.cutoffEdit.text()) if self.filterCheckbox.isChecked() else None,
            'dsr': int(self.downsampleEdit.text()) if self.downsampleCheckbox.isChecked() else None
        }
        # Special cases depending on number of files
        if len(self.filesizes) == 1:  # For a single file, we always use a fixed length
            span = self.sampleStartSlider.maximum() - self.sampleStartSlider.minimum()
            expectedSamples = self.parseExpectedSamplesInFiles(
                newsettings['headersize'],
                self.bytesPerSample[self.datafmtDropdown.currentText()]
            )

            newsettings['usefixedlen'] = True
            # Extract values from the text boxes (rather than slider) as this is a number the user sees directly
            newsettings['fixedlen'] = int(
                self.sampleEndEdit.text()) - int(self.sampleStartEdit.text())
            newsettings['sampleStart'] = int(self.sampleStartEdit.text())

        else:  # For multiple files, we assume 0 offset from after the header
            newsettings['usefixedlen'] = self.fixedlenCheckbox.isChecked()
            newsettings['fixedlen'] = int(
                self.fixedlenEdit.text()) if self.fixedlenEdit.isEnabled() else -1
            newsettings['sampleStart'] = 0

        return newsettings

    def _packSettings(self, settings: dict) -> dict:
        # This is a stringifyed version of the settings dictionary.
        strSettings = {
            key: str(val) if val is not None else "" for key, val in settings.items()
        }

        return strSettings

    def accept(self):
        # Get the new candidate settings
        newsettings = self.parseSettings()

        # Before we even do anything, check if number of samples is too large
        sampleCountCheck = QMessageBox.Ok
        totalSampleCount = sum(self.parseExpectedSamplesInFiles(
            newsettings['headersize'],
            self.bytesPerSample[self.datafmtDropdown.currentText()]
        ))
        if totalSampleCount >= 100e6:
            sampleCountCheck = QMessageBox.warning(
                self,
                "High number of loaded samples",
                "You are about to load %d samples.\nThis may lag your computer significantly depending on your RAM budget. Are you sure?" % totalSampleCount,
                QMessageBox.Ok | QMessageBox.Cancel, QMessageBox.Ok
            )

        if sampleCountCheck != QMessageBox.Ok:
            return

        # Continue with using settings
        self.settingsSignal.emit(newsettings)

        # Before accepting, we check if the current settings match the current config
        loadedConfig = self.config.getConfig(
            self.configDropdown.currentText())  # This is a config object
        currentConfig = self._packSettings(newsettings)  # This is a dict
        if dict(loadedConfig) == currentConfig:
            # Then we return the currentConfig name
            self.configSignal.emit(self.configDropdown.currentText())
        else:
            print(dict(loadedConfig))
            print(currentConfig)
            # Generate a new 'Custom' config and return that
            self.config.saveConfig('Custom', currentConfig)
            self.configSignal.emit('Custom')

        super().accept()

    @Slot(str)
    def onNpersegChanged(self, txt: str):
        # We edit the Noverlapdropdown
        nperseg = int(txt)
        self.specNoverlapSpinbox.setRange(0, nperseg-1)
        self.specNoverlapLabel.setText(
            "Spectrogram Overlap (samples) [default: %d]" % (nperseg/8))
        self.specNoverlapSpinbox.setValue(nperseg/8)

    @Slot(str)
    def onDownsampleChanged(self, txt: str):
        if len(txt) > 0:
            dsr = int(txt)
            self.fsAfterDownsampleEdit.setText(
                str(float(self.fsEdit.text()) / dsr)
            )
        else:
            self.fsAfterDownsampleEdit.setText("")

    @Slot(str)
    def onFreqShiftChanged(self, txt: str):
        if len(txt) > 0:
            finalFc = float(self.fcEdit.text()) + float(
                self.freqshiftEdit.text()
            )
            self.finalFcEdit.setText(str(finalFc))
        else:
            self.finalFcEdit.setText("")

    # =========================================
    # These methods are related to config wrangling

    @Slot(str)
    def _loadSelectedConfigToUI(self, cfgname: str):
        cfg = self.config.getConfig(cfgname)

        try:
            # Data type
            self.datafmtDropdown.setCurrentText(cfg.get('fmt'))

            # Endianness
            self.endiannessCheckBox.setChecked(cfg.getboolean('swapEndian'))

            # Header size
            self.headersizeEdit.setText(cfg.get('headersize'))

            if len(self.filesizes) == 1:
                sampleStart = cfg.getint('sampleStart')
                span = self.sampleStartSlider.maximum() - self.sampleStartSlider.minimum()
                # Yes, yes this is repeated.. TODO
                headerBytes = int(self.headersizeEdit.text()
                                  ) if self.headersizeEdit.text() != "" else 0
                expectedSamples = self.parseExpectedSamplesInFiles(
                    headerBytes,
                    self.bytesPerSample[self.datafmtDropdown.currentText()]
                )
                # We must scale it to the slider values
                self.sampleStartEdit.setText(str(int(sampleStart)))
                oldstate = self.sampleStartSlider.blockSignals(
                    True)  # Remember to block slider signals
                self.sampleStartSlider.setValue(
                    int(sampleStart/expectedSamples[0] * span))
                self.sampleStartSlider.blockSignals(oldstate)
                # Only set the ending if the fixedlen is specified
                if cfg.getint('fixedlen') >= 0:
                    sampleEnd = sampleStart + cfg.getint('fixedlen')
                    self.sampleEndEdit.setText(str(int(sampleEnd)))
                    oldstate = self.sampleEndSlider.blockSignals(
                        True)  # Remember to block slider signals
                    self.sampleEndSlider.setValue(
                        int(sampleEnd/expectedSamples[0] * span))
                    self.sampleEndSlider.blockSignals(oldstate)

            else:
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
            if cfg.get('freqshift') is not None and cfg.get('freqshift') != "":
                self.freqshiftCheckbox.setChecked(True)
                self.freqshiftEdit.setEnabled(True)
                self.freqshiftEdit.setText(cfg.get('freqshift'))
            else:
                self.freqshiftCheckbox.setChecked(False)
                self.freqshiftEdit.setEnabled(False)

            # Filtering
            if cfg.get('numTaps') is not None and cfg.get('numTaps') != "":
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
            if cfg.get('dsr') is not None and cfg.get('dsr') != "":
                self.downsampleCheckbox.setChecked(True)
                self.downsampleEdit.setEnabled(True)
                self.downsampleEdit.setText(cfg.get('dsr'))
            else:
                self.downsampleCheckbox.setChecked(False)
                self.downsampleEdit.setEnabled(False)

        except Exception as e:
            # This usually occurs when you change the loadersettings, then
            # the old file will not have the correct keys.
            # Easiest way to deal with this is to just regenerate the default file
            self.config = None  # Reset it
            os.remove(LoaderSettingsConfig.loaderSettingsFile)  # Delete
            self.config = LoaderSettingsConfig()
            # Recursively call self?
            self._loadSelectedConfigToUI(cfgname)

    def _populateConfigs(self):
        savedcfgs = self.config.getSavedConfigs()
        savedcfgs.insert(0, 'DEFAULT')
        self.configDropdown.clear()
        self.configDropdown.addItems(savedcfgs)

    @Slot()
    def onNewConfig(self):
        # Spawn a dialog
        newcfgname, ok = QInputDialog().getText(self, "Specify config name",
                                                "New config name (or overwrite an existing one):")

        # If dialog ok, save to file and repopulate the dropdown
        if ok:
            newcfg = self._packSettings(self.parseSettings())
            self.config.saveConfig(newcfgname, newcfg)
            self._populateConfigs()
            # Set to the new name
            self.configDropdown.setCurrentText(newcfgname)
