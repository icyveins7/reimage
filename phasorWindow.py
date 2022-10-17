from PySide6.QtWidgets import QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QFormLayout
from PySide6.QtWidgets import QPushButton, QLabel, QLineEdit, QApplication, QMenu, QInputDialog, QMessageBox, QSlider
from PySide6.QtCore import Qt, Signal, Slot, QRectF, QEvent
import pyqtgraph as pg
import numpy as np
import scipy.signal as sps

class PhasorWindow(QMainWindow):
    changeSampBufferSignal = Signal(int)

    def __init__(self, sampbuffer: int, parent=None):
        super().__init__(parent)
        self.setAttribute(Qt.WA_DeleteOnClose) # Ensure deletion so that no further updates are polled

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

        # Control UI
        self.prepareControls(sampbuffer)

    #################### UI Preparation Methods
    def preparePhasorPlot(self):
        self.glw = pg.GraphicsLayoutWidget()
        self.layout.addWidget(self.glw)
        self.p = self.glw.addPlot()
        self.pitem = self.p.plot([0],[0])
        self.parrow = self.p.plot([0], [0], pen='y')
        
    def prepareControls(self, sampbuffer: int):
        self.controlLayout = QFormLayout()
        self.layout.addLayout(self.controlLayout)

        # Buffer controls how many samples ahead/behind to display
        self.bufferLabel = QLabel()
        self.setSampBufferLabel(sampbuffer)
        self.bufferSlider = QSlider(Qt.Horizontal)
        self.bufferSlider.setMinimum(1)
        self.bufferSlider.setValue(sampbuffer)
        self.bufferSlider.valueChanged.connect(self.changeSampBuffer)
        self.controlLayout.addRow(self.bufferLabel, self.bufferSlider)

    #################### Plotting methods
    @Slot(np.ndarray, int)
    def updateData(self, data: np.ndarray, centreIdx: int):
        # This comes in as complex data (enforce complex128 for simplicity)
        self.data = data.astype(np.complex128)
        # View as reals, pack into rows of (x,y)
        self.data = self.data.view(np.float64).reshape((-1,2))
        # Plot the data
        self.plot(centreIdx)

    def plot(self, centreIdx: int):
        # Expected that the array that arrives already has appropriate length
        self.pitem.setData(
            self.data[:,0],
            self.data[:,1]
        )
        self.parrow.setData(
            [0, self.data[centreIdx, 0]],
            [0, self.data[centreIdx, 1]]
        )
        # Make sure the axis limits are fixed and centred
        axisLim = 1.1 * np.max(np.abs(self.data.reshape(-1)))
        self.p.setLimits(xMin=-axisLim, xMax=axisLim, yMin=-axisLim, yMax=axisLim)
        self.p.setXRange(-axisLim, axisLim)
        self.p.setYRange(-axisLim, axisLim)



    #################### For controlling sample buffers
    @Slot(int)
    def changeSampBuffer(self, value: int):
        # Emits back to the main window
        self.changeSampBufferSignal.emit(value)
        
    def setSampBufferLabel(self, sampbuffer: int):
        '''
        Convenience method to update the label with current buffer value.
        This should be called by the main window to maintain consistency.
        '''
        self.bufferLabel.setText("Sample Buffer (%d)" % sampbuffer)

        
