from PySide6.QtWidgets import QFrame, QVBoxLayout
from PySide6.QtCore import Qt
import pyqtgraph as pg
import numpy as np

class SignalView(QFrame):
    def __init__(self, ydata, parent=None, f=Qt.WindowFlags()):
        super().__init__(parent, f)

        # Create a graphics view
        self.glw = pg.GraphicsLayoutWidget()
        self.p = self.glw.addPlot(row=0,col=0)

        # Create the main layout
        self.layout = QVBoxLayout()
        self.layout.addWidget(self.glw)
        self.setLayout(self.layout)

        # Attach the data (hopefully this doesn't copy)
        self.ydata = ydata

        # Placeholder for xdata
        self.xdata = None

    def plotAmpTime(self):
        if self.xdata is None:
            self.p.plot(np.abs(self.ydata))
            
