from PySide6.QtWidgets import QMainWindow, QVBoxLayout, QWidget 
from PySide6.QtWidgets import QTextBrowser
from PySide6.QtCore import Qt, Signal, Slot, QRectF
from PySide6.QtGui import QTextDocument

import os

class ReadmeWindow(QMainWindow):
    readmePath = os.path.join(
        os.path.dirname(__file__), "README.md"
    )

    def __init__(self):
        super().__init__()

        # # Change to folder with the README itself, or else
        # # images don't seem to load
        # os.chdir(os.path.dirname(__file__))

        # Aesthetics..
        self.setWindowTitle("Readme")

        # Main layout
        widget = QWidget()
        self.layout = QVBoxLayout()
        widget.setLayout(self.layout)
        self.setCentralWidget(widget)

        # Add the textbrowser and document
        self.readme = QTextDocument()
        
        with open(self.readmePath, "r") as fid:
            readmemd = fid.read()
        self.readme.setMarkdown(
            readmemd
        )
        self.browser = QTextBrowser()
        self.browser.setDocument(self.readme)
        self.layout.addWidget(self.browser)

