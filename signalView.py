from PySide6.QtWidgets import QFrame, QVBoxLayout
from PySide6.QtCore import Qt
import pyqtgraph as pg

class SignalView(QFrame):
    def __init__(self, parent=None, f=Qt.WindowFlags()):
        super().__init__(parent, f)

        # Create a graphics view
        self.gv = pg.GraphicsView()

        # Create the main layout
        self.layout = QVBoxLayout()
        self.layout.addWidget(self.gv)
        self.setLayout(self.layout)

        # Test plot
        self.gv.addItem(pg.PlotDataItem([1,3,2,4,5]))


