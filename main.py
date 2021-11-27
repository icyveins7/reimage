from PySide6 import QtCore, QtWidgets, QtGui
import sys
import numpy as np
import sqlite3 as sq

from signalView import SignalView
from fileList import FileListFrame

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

        

    @QtCore.Slot(np.ndarray)
    def onNewData(self, data):
        self.sv.setYData(data) # this calls the plot automatically



if __name__ == '__main__':
    app = QtWidgets.QApplication(sys.argv)

    window = ReimageMain()
    window.show()

    app.exec()
