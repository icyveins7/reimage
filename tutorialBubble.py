from PySide6.QtWidgets import QDialog, QLabel, QMessageBox, QVBoxLayout, QWidget, QHBoxLayout, QPushButton, QCheckBox
from PySide6.QtCore import Qt
from PySide6.QtGui import QPainterPath, QGuiApplication

import configparser
import os

class TutorialBubble(QMessageBox): 
    tutorialIniFile = "reimage.ini"

    def __init__(self, 
                 text: str, 
                 parent: QWidget=None, 
                 relativeToParent: tuple=None,
                 key: str=None):
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

        key : str, optional
            Key to identify the type of bubble dialog.
            Used to check whether to show it depending on whether the user
            has previously selected to hide further tutorial bubbles.
            Defaults to None, which will always show it.
        """
        self.key = key
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
        # self.setStyleSheet(
        #     """
        #     QMessageBox { 
        #         border-radius: 10px; 
        #         border: 2px solid rgb(0,0,0);
        #         background-color: rgba(255, 255, 255, 255);
        #     }
        #     QMessageBox QLabel {
        #         color: #000000;
        #     }
        #     QMessageBox QPushButton#Don't Show Again {
        #         background-color: blue;
        #         color: white;
        #     }
        #     """
        # )

        # If key is present we display an additional checkbox
        shouldShow = True
        if key is not None:
            # Try to open the ini file and see the state
            try:
                cfg = configparser.ConfigParser()
                cfg.read(TutorialBubble.tutorialIniFile)
                shouldShow = cfg['tutorials'].getboolean(self.key)
                print("ini file: {}".format(shouldShow))
            except Exception as e:
                print("Error reading ini file: {}".format(e))
                shouldShow = True

            if shouldShow:
                self.rejectBtn = self.addButton("Don't Show Again", QMessageBox.ButtonRole.RejectRole)
                self.rejectBtn.clicked.connect(self.reject) # Must do this for the custom button, or else reject() doesn't get called
                self.addButton(QMessageBox.StandardButtons.Ok)

        if relativeToParent is None:
            # Move to center of screen
            self.centerPos()
        else:
            self.moveRelativeToParent(relativeToParent)
       
        # You must show first, before the .width()/.height() is properly evaluated
        # self.setModal(True) # Doing this makes it flicker back and forth, just set parent and it should work
        if shouldShow:
            self.show()

        # This seems like a decent way to get it working... 
        # Taken from https://forum.qt.io/topic/61117/setting-border-radius-does-not-clip-the-background/3
        self.painterPath = QPainterPath()
        self.painterPath.addRoundedRect(0, 0, self.width(), self.height(), 10, 10)
        self.setMask(self.painterPath.toFillPolygon().toPolygon()) # TODO: handle all 4 edges?


    def centerPos(self):
        """Centre in the middle of the screen, not the parent widget."""
        # Taken from https://stackoverflow.com/questions/12432740/pyqt4-what-is-the-best-way-to-center-dialog-windows
        # Note that QGuiApplication is used now in PySide6 
        # This works the best out of all the googled methods!
        qr = self.frameGeometry()
        cp = QGuiApplication.primaryScreen().availableGeometry().center()
        qr.moveCenter(cp)
        self.move(qr.topLeft())

    def moveRelativeToParent(self, pixelsRelativeToParent):
        """
        Move relative to top left corner of parent widget,
        accounting for current size of the bubble? 
        """
        self.move(
            self.parent.x()-self.frameGeometry().width()+pixelsRelativeToParent[0], 
            self.parent.y()-self.frameGeometry().height()+pixelsRelativeToParent[1]
        )

    # Overload reject()
    def reject(self):
        print("Custom TutorialBubble.reject()")
        cfg = configparser.ConfigParser()
        if not os.path.exists(self.tutorialIniFile):
            print("No .ini file found. Creating one...")
            cfg['tutorials'] = {
                self.key: False
            }
            with open(self.tutorialIniFile, "w") as f:
                cfg.write(f)

        else:
            cfg.read(self.tutorialIniFile)
            cfg['tutorials'][self.key] = 'False' # TODO: doesn't like me setting bools
            with open(self.tutorialIniFile, "w") as f:
                cfg.write(f)

        super().reject()

