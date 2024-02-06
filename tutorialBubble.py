from PySide6.QtWidgets import QDialog, QLabel, QMessageBox, QVBoxLayout, QWidget, QHBoxLayout, QPushButton
from PySide6.QtCore import Qt
from PySide6.QtGui import QPainterPath, QGuiApplication


class TutorialBubble(QMessageBox): 
    def __init__(self, text: str, parent: QWidget=None, relativeToParent: tuple=None):
        """
        Instantiate the bubble dialog with some text.

        Parameters
        ----------
        text : str
            The bubble dialog's text.
        
        parent : QWidget, optional
            Parent widget. Defaults to None.
            Use this to help center the widget, or if it should be placed
            relative to it using relativeToParent.

        relativeToParent : tuple, optional
            (x, y) coordinates with respect to the parent widget. Defaults to None.
        """
        self.parent = parent
        super().__init__(parent=parent)

        # QMessageBox implementation
        self.setText(text)

        # Set frameless
        self.setWindowFlag(Qt.WindowType.FramelessWindowHint, True)
        # Set attributes for rounded corners
        # self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        # self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        # self.setAttribute(Qt.WidgetAttribute.WA_NoSystemBackground, True)
        # Set stylesheet for rounded corners
        self.setStyleSheet(
            """
            QMessageBox { 
                border-radius: 10px; 
                border: 2px solid rgb(0,0,0);
                background-color: rgba(255, 255, 255, 255);
            }
            QMessageBox QLabel {
                color: #000000;
            }
            """
        )

       
        # You must show first, before the .width()/.height() is properly evaluated
        # self.setModal(True) # Doing this makes it flicker back and forth, just set parent and it should work
        self.show()

        # # Move to center of screen
        self.centerPos()
 
        # This seems like a decent way to get it working... 
        # Taken from https://forum.qt.io/topic/61117/setting-border-radius-does-not-clip-the-background/3
        self.painterPath = QPainterPath()
        self.painterPath.addRoundedRect(0, 0, self.width(), self.height(), 10, 10)
        self.setMask(self.painterPath.toFillPolygon().toPolygon()) # TODO: handle all 4 edges?


    def centerPos(self):
        # Taken from https://stackoverflow.com/questions/12432740/pyqt4-what-is-the-best-way-to-center-dialog-windows
        # Note that QGuiApplication is used now in PySide6 
        # This works the best out of all the googled methods!
        qr = self.frameGeometry()
        cp = QGuiApplication.primaryScreen().availableGeometry().center()
        qr.moveCenter(cp)
        self.move(qr.topLeft())

