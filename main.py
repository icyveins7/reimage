from PySide6 import QtCore, QtWidgets, QtGui
import sys
import numpy as np
import sqlite3 as sq

from signalView import SignalView
from fileList import FileListFrame
from fileSettings import FileSettingsDialog

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

        # # Application global settings
        # QtCore.QCoreApplication.setOrganizationName("Seo")
        # QtCore.QCoreApplication.setApplicationName("ReImage")

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
        self.menubar.addMenu(self.settingsMenu)

    @QtCore.Slot()
    def openFileFormatSettings(self):
        dialog = FileSettingsDialog()
        dialog.exec()
        



if __name__ == '__main__':
    app = QtWidgets.QApplication(sys.argv)

    window = ReimageMain()
    window.show()

    app.exec()
