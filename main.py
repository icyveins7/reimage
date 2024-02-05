from importlib.abc import Loader
from PySide6 import QtCore, QtWidgets, QtGui
import os
os.environ['PYQTGRAPH_QT_LIB'] = 'PySide6' # Set this to force ReImage to use PySide6
import platform

import sys
import numpy as np
import sqlite3 as sq

from signalView import SignalView
from fileList import FileListFrame
from predetections import PredetectAmpDialog
from loaderSettings import LoaderSettingsDialog
from sidebarSettings import SidebarSettings
from readmeWindow import ReadmeWindow
from ipc import ReimageListenerThread

from tutorialBubble import TutorialBubble

class ReimageMain(QtWidgets.QMainWindow):
    resizedSignal = QtCore.Signal()
    exportToImageSignal = QtCore.Signal(float)

    def __init__(self):
        super().__init__()

        # We change the directory to the one containing this file
        # This has several uses:
        # 1) all databases/configs stay in the same folder, instead of
        #    where the user's working folder might be at the time
        # 2) for README window, the images are rendered correctly
        os.chdir(os.path.dirname(__file__))

        # Icon setting (doesn't do anything for MacOS?)
        self.setWindowIcon(QtGui.QIcon(os.path.join(os.path.dirname(__file__), 'icon.png')))

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
        self.exportToImageSignal.connect(self.sv.exportToImageSlot)

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
        # Exporter settings
        self.exportResolutionScaleFactor = 2.0

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

        # Experimental tutorial bubbles
        self.tb = TutorialBubble("Welcome to ReImage!", self) # The bubble will show itself internally

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
        self.menubar.addMenu(self.predetectMenu)
        # ===========
        self.exportMenu = QtWidgets.QMenu("Export", self)
        self.exportMenuAction = self.exportMenu.addAction("To Image")
        self.exportMenuAction.triggered.connect(self.exportToImage)
        self.exportSettingsAction = self.exportMenu.addAction("Resolution Settings")
        self.exportSettingsAction.triggered.connect(self.openExportSettings)
        self.menubar.addMenu(self.exportMenu)
        # ===========
        self.helpMenu = QtWidgets.QMenu("Help", self)
        self.readmeMenuAction = self.helpMenu.addAction("View README")
        self.readmeMenuAction.triggered.connect(self.viewReadme)
        self.menubar.addMenu(self.helpMenu)

    ##### Menu bar slots
    @QtCore.Slot()
    def viewReadme(self):
        self.readmeWindow = ReadmeWindow()
        self.readmeWindow.show()

    @QtCore.Slot()
    def exportToImage(self):
        # Just fire the signal for now
        self.exportToImageSignal.emit(self.exportResolutionScaleFactor)

    @QtCore.Slot()
    def openExportSettings(self):
        # Simple setting of 1 value
        newResolutionScale, ok = QtWidgets.QInputDialog.getDouble(
            self, "Set Export Resolution Scale Factor",
            "Resolution Scale Factor: ", self.exportResolutionScaleFactor,
            0.1, 10.0
        )
        if ok and newResolutionScale is not None:
            self.exportResolutionScaleFactor = newResolutionScale


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

    ###### End of menu bar slots

    ##### Status bar
    def setupStatusBar(self):
        # Permanent help message
        self.statusbar = QtWidgets.QStatusBar()
        if platform.system() == 'Darwin':
            self.helperStatus = QtWidgets.QLabel(
                "Cmd-Rightclick on the plots to see signal processing options.")
        else:
            self.helperStatus = QtWidgets.QLabel(
                "Ctrl-Rightclick on the plots to see signal processing options.")
        self.statusbar.addPermanentWidget(self.helperStatus)

        # Widget specific help messages
        self.sv.SignalViewStatusTip.connect(self.statusbar.showMessage)
        self.fileListFrame.fileListStatusTip.connect(self.statusbar.showMessage)

        self.setStatusBar(self.statusbar)


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
