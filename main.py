from PySide6 import QtCore, QtWidgets, QtGui
import sys
import numpy as np

from signalView import SignalView
from fileList import FileListFrame

class ReimageMain(QtWidgets.QMainWindow):
    def __init__(self):
        super().__init__()

        # Some window things
        self.setWindowTitle("Reimage")

        # Main layout
        widget = QtWidgets.QWidget()
        self.layout = QtWidgets.QVBoxLayout()
        widget.setLayout(self.layout)
        self.setCentralWidget(widget)

        # Sublayout 1
        self.workspaceLayout = QtWidgets.QHBoxLayout() # Sublayout 
        self.fileListFrame = FileListFrame()
        self.workspaceLayout.addWidget(self.fileListFrame)
        
        # Add sublayouts to main layout
        self.layout.addLayout(self.workspaceLayout)

        # Testing
        self.sv = SignalView(np.array([1,3,2,4,5])) # sample data
        self.sv.plotAmpTime()
        self.workspaceLayout.addWidget(self.sv)

if __name__ == '__main__':
    app = QtWidgets.QApplication(sys.argv)

    window = ReimageMain()
    window.show()

    app.exec()
