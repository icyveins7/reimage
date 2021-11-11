from PySide6 import QtCore, QtWidgets, QtGui
import sys

class ReimageMain(QtWidgets.QMainWindow):
    def __init__(self):
        super().__init__()

        # Placeholder
        self.hello = 'hello'
        self.helloLabel = QtWidgets.QLabel(self.hello)

        # Main layout
        widget = QtWidgets.QWidget()
        self.layout = QtWidgets.QHBoxLayout()
        widget.setLayout(self.layout)
        self.setCentralWidget(widget)

        # Add to layout
        self.layout.addWidget(self.helloLabel)

if __name__ == '__main__':
    app = QtWidgets.QApplication(sys.argv)

    window = ReimageMain()
    window.show()

    app.exec_()
