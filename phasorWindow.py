from PySide6.QtWidgets import QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QFormLayout
from PySide6.QtWidgets import QPushButton, QLabel, QLineEdit, QApplication, QMenu, QInputDialog, QMessageBox, QSlider
from PySide6.QtCore import Qt, Signal, Slot, QRectF, QEvent
import pyqtgraph as pg
import numpy as np
import scipy.signal as sps

class PhasorWindow(QMainWindow):
    def __init__(self, parent=None):
        super().__init__(parent)

        # Aesthetics..
        self.setWindowTitle("View Phasor")

        # Main layout
        widget = QWidget()
        self.layout = QVBoxLayout()
        widget.setLayout(self.layout)
        self.setCentralWidget(widget)

        # Prepare the main plot interface
        self.data = None # Placeholder for the incoming data
        # Plot UI
        self.preparePhasorPlot()

        # And some controls
        self.sampbuffer = 1
        # Control UI
        self.prepareControls()

    #################### UI Preparation Methods
    def preparePhasorPlot(self):
        self.glw = pg.GraphicsLayoutWidget()
        self.layout.addWidget(self.glw)
        self.p = self.glw.addPlot()
        
    def prepareControls(self):
        self.controlLayout = QFormLayout()
        self.layout.addLayout(self.controlLayout)

        # Buffer controls how many samples ahead/behind to display
        self.bufferLabel = QLabel()
        self.setSampBufferLabel()
        self.bufferSlider = QSlider(Qt.Horizontal)
        self.bufferSlider.valueChanged.connect(self.changeSampBuffer)
        self.controlLayout.addRow(self.bufferLabel, self.bufferSlider)

    #################### Plotting methods
    @Slot(np.ndarray)
    def updateData(self, data: np.ndarray):
        # This comes in as complex data (enforce complex128 for simplicity)
        self.data = data.astype(np.complex128)
        # View as reals, pack into rows of (x,y)
        self.data = self.data.view(np.float64).reshape((-1,2))
        # Plot the data
        self.plot()

    def plot(self):
        # TODO
        pass



    #################### For controlling sample buffers
    @Slot(int)
    def changeSampBuffer(self, value: int):
        self.sampbuffer = value
        self.setSampBufferLabel()
        
    def setSampBufferLabel(self):
        '''Convenience method to update the label with current buffer value.'''
        self.bufferLabel.setText("Sample Buffer (%d)" % self.sampbuffer)

        
