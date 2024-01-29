from importlib.abc import Loader
from PySide6 import QtCore, QtWidgets, QtGui
import os
os.environ['PYQTGRAPH_QT_LIB'] = 'PySide6' # Set this to force ReImage to use PySide6

import sys
import numpy as np
import sqlite3 as sq
import pyqtgraph.exporters as exporters

from signalView import SignalView
from fileList import FileListFrame
from predetections import PredetectAmpDialog
from loaderSettings import LoaderSettingsDialog
from sidebarSettings import SidebarSettings
from ipc import ReimageListenerThread

class ReimageMain(QtWidgets.QMainWindow):
    resizedSignal = QtCore.Signal()

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

        # Add signal viewer
        self.sv = SignalView(np.zeros(100) + 100000) # sample data
        self.sv.plotAmpTime()
        self.workspaceLayout.addWidget(self.sv)

        # Add the side toolbar
        self.sidebar = SidebarSettings()
        self.workspaceLayout.addWidget(self.sidebar)

        # Connections
        self.fileListFrame.dataSignal.connect(self.onNewData)
        self.fileListFrame.newFilesSignal.connect(self.newFilesHandler)
        # self.fileListFrame.sampleRateSignal.connect(self.setSampleRate)

        self.sidebar.addSmaSignal.connect(self.sv.addSma)
        self.sidebar.deleteSmaSignal.connect(self.sv.delSma)
        self.sidebar.changeSmaColourSignal.connect(self.sv.colourSma)
        self.sidebar.changeToAmpPlotSignal.connect(self.sv.changeToAmpPlot)
        self.sidebar.changeToReimPlotSignal.connect(self.sv.changeToReimPlot)

        self.sidebar.changeSpecgramContrastSignal.connect(self.sv.adjustSpecgramContrast)
        self.sidebar.changeSpecgramLogScaleSignal.connect(self.sv.adjustSpecgramLog)

        self.sidebar.showHideAmpPlotSignal.connect(self.sv.showHideAmpPlot)

        self.fileListFrame.dataSignal.connect(self.sidebar.reset) # Clear all settings on new data
        
        self.resizedSignal.connect(self.fileListFrame.onResizedWindow)

        # Application global settings
        QtCore.QCoreApplication.setOrganizationName("Seo")
        QtCore.QCoreApplication.setApplicationName("ReImage")
        # # File Format Settings
        # self.filesettings = {
        #     "fmt": "complex int16",
        #     "headersize": 0,
        #     "usefixedlen": False,
        #     "fixedlen": -1,
        #     "invSpec": False
        # } # TODO: add cached settings instead of defaults, and load from a global place
        # # Signal settings
        # self.signalsettings = {
        #     'nperseg': 128,
        #     'noverlap': 128/8,
        #     'fs': 1,
        #     'fc': 0.0,
        #     'freqshift': None, 
        #     'numTaps': None, 
        #     'filtercutoff': None,
        #     'dsr': None
        # }
        # Configuration handling
        self.currentConfig = 'DEFAULT' # This is the default one

        # Menu
        self.setupMenu()

        # Add a status-bar for help
        self.setupStatusBar()

        # Add the side-thread for export/import of data
        self.listenerThread = ReimageListenerThread()
        self.sv.DataSelectionSignal.connect(self.listenerThread.setSelectedData)
        self.listenerThread.start()

    def closeEvent(self, event):
        """QWidget handler for the destructor. Do not use __del__ for this!"""
        # Handle listener thread cleanup
        print("Handling listenerThread cleanup...")
        self.listenerThread.graceful_kill()
        self.listenerThread.wait()

    @QtCore.Slot(np.ndarray, list, list)
    def onNewData(self, data, filelist, sampleStarts):
        self.sv.setYData(data, filelist, sampleStarts) # this calls the plot automatically

    def setupMenu(self):
        self.menubar = QtWidgets.QMenuBar()
        self.setMenuBar(self.menubar)
        
        # ===========
        self.predetectMenu = QtWidgets.QMenu("Predetect", self)
        self.predetectAmp = self.predetectMenu.addAction("Via Amplitude")
        self.predetectAmp.triggered.connect(self.openPredetectAmp)
        # ===========
        self.exportMenu = QtWidgets.QMenu("Export", self)
        self.exportMenuAction = self.exportMenu.addAction("To Image")
        self.exportMenuAction.triggered.connect(self.exportToImage)

        self.menubar.addMenu(self.predetectMenu)

    def setupStatusBar(self):
        # Permanent help message
        self.statusbar = QtWidgets.QStatusBar()
        self.helperStatus = QtWidgets.QLabel(
            "Ctrl-Rightclick on the plots to see signal processing options.")
        self.statusbar.addPermanentWidget(self.helperStatus)

        # Widget specific help messages
        self.sv.SignalViewStatusTip.connect(self.statusbar.showMessage)
        self.fileListFrame.fileListStatusTip.connect(self.statusbar.showMessage)

        self.setStatusBar(self.statusbar)

    @QtCore.Slot()
    def exportToImage(self):
        # TODO: trigger Pyqtgraph's inbuilt export on the signalView
        raise NotImplementedError("Not yet implemented")

    @QtCore.Slot()
    def openPredetectAmp(self):
        dialog = PredetectAmpDialog(
            self.fileListFrame.getCurrentFilelist(),
            {
                'fmt': self.fileListFrame.fmt,
                'headersize': self.fileListFrame.headersize,
                'usefixedlen': self.fileListFrame.usefixedlen,
                'fixedlen': self.fileListFrame.fixedlen
            }
            ) # TODO: write getter for this
        dialog.predetectAmpSignal.connect(self.fileListFrame.highlightFiles)
        dialog.exec()

    # @QtCore.Slot(int)
    # def setSampleRate(self, samplerate: int):
    #     # Main use-case is to DISPLAY sample rate for to-be-loaded .wav files
    #     self.wavSamplerate = samplerate
    #     print("Set wav sample rate to %d" % self.wavSamplerate)

    @QtCore.Slot(str, int)
    def newFilesHandler(self, specialType: str="", wavSamplerate: int=None, filepaths: list=None):
        # We spawn the new amalgamated loader settings
        dialog = LoaderSettingsDialog(specialType, configName=self.currentConfig, wavSamplerate=wavSamplerate, filepaths=filepaths)
        dialog.settingsSignal.connect(self.saveSettings)
        dialog.configSignal.connect(self.saveConfigName)
        dialog.accepted.connect(self.fileListFrame.loadFiles) # If accepted then we load files
        dialog.exec()

    @QtCore.Slot(str)
    def saveConfigName(self, newconfigname):
        # Updates the last used config name so that subsequent opens use it
        self.currentConfig = newconfigname

    @QtCore.Slot(dict)
    def saveSettings(self, newsettings):
        # Combine both setters here
        self.sv.nperseg = newsettings['nperseg']
        self.sv.noverlap = newsettings['noverlap']
        self.sv.fs = newsettings['fs']
        self.sv.fc = newsettings['fc']
        self.sv.freqshift = newsettings['freqshift']
        self.sv.numTaps = newsettings['numTaps']
        self.sv.filtercutoff = newsettings['filtercutoff']
        self.sv.dsr = newsettings['dsr']
        ####################
        formatsToDtype = {
            'complex int16': np.int16,
            'complex float32': np.float32,
            'complex float64': np.float64
        }
        self.fileListFrame.fmt = formatsToDtype[newsettings['fmt']]
        self.fileListFrame.headersize = newsettings['headersize']
        self.fileListFrame.usefixedlen = newsettings['usefixedlen']
        self.fileListFrame.fixedlen = newsettings['fixedlen']
        self.fileListFrame.invSpec = newsettings['invSpec']
        self.fileListFrame.sampleStart = newsettings['sampleStart']

    def resizeEvent(self, event):
        self.resizedSignal.emit()
        super().resizeEvent(event)
        



if __name__ == '__main__':
    app = QtWidgets.QApplication(sys.argv)

    window = ReimageMain()
    window.show()

    app.exec()
