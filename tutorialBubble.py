from PySide6.QtWidgets import QDialog, QLabel, QMessageBox, QVBoxLayout, QWidget, QHBoxLayout, QPushButton
from PySide6.QtCore import Qt
from PySide6.QtGui import QPainterPath


class TutorialBubble(QMessageBox): # QDialog): # (QMessageBox):
    def __init__(self, text: str, parent=None):
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

        # This seems like a decent way to get it working... 
        # Taken from https://forum.qt.io/topic/61117/setting-border-radius-does-not-clip-the-background/3
        self.painterPath = QPainterPath()
        self.painterPath.addRoundedRect(0, 0, self.width(), self.height(), 10, 10)
        self.setMask(self.painterPath.toFillPolygon().toPolygon()) # TODO: handle all 4 edges?



