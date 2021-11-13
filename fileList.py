from PySide6.QtWidgets import QFrame, QVBoxLayout, QHBoxLayout, QPushButton, QFileDialog
from PySide6.QtWidgets import QListWidget, QListWidgetItem
from PySide6.QtCore import Qt, Signal, Slot
import os

#%%
class FileListItem(QListWidgetItem):
    def __init__(self, *args, **kwargs):
        super.__init__(*args, **kwargs)


#%%
class FileListFrame(QFrame):
    def __init__(self, parent=None, f=Qt.WindowFlags()):
        super().__init__(parent, f)

        # Create the file list widget
        self.flw = QListWidget()
        # Sublayout for buttons
        self.btnLayout = QHBoxLayout()
        # Some buttons..
        self.prepareFileBtn()
        self.prepareFolderBtn()

        # Create the main layout
        self.layout = QVBoxLayout()
        self.layout.addLayout(self.btnLayout) # Buttons at the top
        self.layout.addWidget(self.flw) # List below it
        self.setLayout(self.layout)

    ####################
    def prepareFileBtn(self):
        self.oFileBtn = QPushButton("Open File(s)")
        self.btnLayout.addWidget(self.oFileBtn)

        self.oFileBtn.clicked.connect(self.onFileBtnClicked)

    @Slot()
    def onFileBtnClicked(self):
        fileNames, selectedFilter = QFileDialog.getOpenFileNames(self,
            "Open Complex Data Files", ".", "Complex Data Files (*.bin *.dat);;All Files (*)")
        if len(fileNames) > 0: # When cancelled, it returns an empty list
            self.flw.addItems(fileNames)

    ####################
    def prepareFolderBtn(self):
        self.oFolderBtn = QPushButton("Open Folder")
        self.btnLayout.addWidget(self.oFolderBtn)

        self.oFolderBtn.clicked.connect(self.onFolderBtnClicked)

    @Slot()
    def onFolderBtnClicked(self):
        folderName = QFileDialog.getExistingDirectory()
        folderFiles = os.listdir(folderName)
        fileNames = [os.path.join(folderName, i) for i in folderFiles]
        self.flw.addItems(fileNames)
    
