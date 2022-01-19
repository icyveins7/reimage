from PySide6 import QtCore, QtWidgets, QtGui
import sys
import numpy as np
import sqlite3 as sq

from signalView import SignalView
from fileList import FileListFrame
from fileSettings import FileSettingsDialog
from signalSettings import SignalSettingsDialog
from predetections import PredetectAmpDialog

class ReimageMain(QtWidgets.QMainWindow):
    def __init__(self):
        super().__init__()

        # Databases
        self.cachedb = sq.connect('cache.db')

        # Some window things
        self.setWindowTitle("Reimage")

        # Main layout
        widget = QtWidgets.QWidget()
        self.layout = QtWidgets.QVBoxLayout()
        widget.setLayout(self.layout)
        self.setCentralWidget(widget)

        # Sublayout 1
        self.workspaceLayout = QtWidgets.QHBoxLayout() # Sublayout 
        self.fileListFrame = FileListFrame(db=self.cachedb)
        self.workspaceLayout.addWidget(self.fileListFrame)
        
        # Add sublayouts to main layout
        self.layout.addLayout(self.workspaceLayout)

        # Testing
        self.sv = SignalView(np.zeros(100) + 100000) # sample data
        self.sv.plotAmpTime()
        self.workspaceLayout.addWidget(self.sv)

        # Connections
        self.fileListFrame.dataSignal.connect(self.onNewData)

        # Application global settings
        QtCore.QCoreApplication.setOrganizationName("Seo")
        QtCore.QCoreApplication.setApplicationName("ReImage")
        # File Format Settings
        self.filesettings = {
            "fmt": "complex int16",
            "headersize": 0,
            "usefixedlen": False,
            "fixedlen": -1
        } # TODO: add cached settings instead of defaults, and load from a global place
        # Signal settings
        self.signalsettings = {
            'nperseg': 256,
            'noverlap': 256/8,
            'fs': 1,
            'freqshift': None, 
            'numTaps': None, 
            'filtercutoff': None,
            'dsr': None
        }

        # Menu
        self.setupMenu()

        

    @QtCore.Slot(np.ndarray, list, list)
    def onNewData(self, data, filelist, sampleStarts):
        self.sv.setYData(data, filelist, sampleStarts) # this calls the plot automatically

    def setupMenu(self):
        self.menubar = QtWidgets.QMenuBar()
        self.setMenuBar(self.menubar)

        self.settingsMenu = QtWidgets.QMenu("Settings", self)
        self.fileFormatSettings = self.settingsMenu.addAction("File Formats")
        self.fileFormatSettings.triggered.connect(self.openFileFormatSettings)

        self.signalViewSettings = self.settingsMenu.addAction("Signal Viewer")
        self.signalViewSettings.triggered.connect(self.openSignalViewSettings)

        self.menubar.addMenu(self.settingsMenu)
        # ===========
        self.predetectMenu = QtWidgets.QMenu("Predetect", self)
        self.predetectAmp = self.predetectMenu.addAction("Via Amplitude")
        self.predetectAmp.triggered.connect(self.openPredetectAmp)

        self.menubar.addMenu(self.predetectMenu)

    @QtCore.Slot()
    def openPredetectAmp(self):
        dialog = PredetectAmpDialog()
        dialog.exec()


    @QtCore.Slot()
    def openSignalViewSettings(self):
        dialog = SignalSettingsDialog(self.signalsettings)
        dialog.signalsettingsSignal.connect(self.saveSignalSettings)
        dialog.exec()

    @QtCore.Slot()
    def openFileFormatSettings(self):
        dialog = FileSettingsDialog(self.filesettings)
        dialog.filesettingsSignal.connect(self.saveFileFormatSettings)
        dialog.exec()

    @QtCore.Slot(dict)
    def saveSignalSettings(self, newsettings):
        self.signalsettings = newsettings
        # Apply to signal view 
        self.sv.nperseg = self.signalsettings['nperseg']
        self.sv.noverlap = self.signalsettings['noverlap']
        self.sv.fs = self.signalsettings['fs']
        self.sv.freqshift = self.signalsettings['freqshift']
        self.sv.numTaps = self.signalsettings['numTaps']
        self.sv.filtercutoff = self.signalsettings['filtercutoff']
        self.sv.dsr = self.signalsettings['dsr']

    @QtCore.Slot(dict)
    def saveFileFormatSettings(self, newsettings):
        self.filesettings = newsettings
        # Set the file list widget attributes
        formatsToDtype = {
            'complex int16': np.int16,
            'complex float32': np.float32,
            'complex float64': np.float64
        } # TODO: keep this somewhere common
        self.fileListFrame.fmt = formatsToDtype[self.filesettings['fmt']]
        self.fileListFrame.headersize = self.filesettings['headersize']
        self.fileListFrame.usefixedlen = self.filesettings['usefixedlen']
        self.fileListFrame.fixedlen = self.filesettings['fixedlen']
        



if __name__ == '__main__':
    app = QtWidgets.QApplication(sys.argv)

    window = ReimageMain()
    window.show()

    app.exec()
