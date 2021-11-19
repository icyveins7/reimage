from PySide6.QtWidgets import QFrame, QVBoxLayout, QHBoxLayout, QPushButton, QFileDialog
from PySide6.QtWidgets import QListWidget, QListWidgetItem, QAbstractItemView
from PySide6.QtCore import Qt, Signal, Slot
import os
import numpy as np

#%%
class FileListItem(QListWidgetItem):
    def __init__(self, *args, **kwargs):
        super.__init__(*args, **kwargs)


#%%
class FileListFrame(QFrame):
    dataSignal = Signal(np.ndarray)

    def __init__(self, parent=None, f=Qt.WindowFlags()):
        super().__init__(parent, f)

        # Create the file list widget
        self.flw = QListWidget()
        self.flw.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.flw.setDragEnabled(True)
        self.flw.setMaximumWidth(360)
        # Sublayout for buttons
        self.btnLayout = QHBoxLayout() # TODO: change layout max width?
        # Some buttons..
        self.prepareFileBtn()
        self.prepareFolderBtn()
        self.prepareAddBtn()

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
    
    ####################
    def prepareAddBtn(self):
        self.addBtn = QPushButton("Add to Viewer")
        self.btnLayout.addWidget(self.addBtn)

        self.addBtn.clicked.connect(self.onAddBtnClicked)

    @Slot()
    def onAddBtnClicked(self):
        filepaths = [i.text() for i in self.flw.selectedItems()]
        print(filepaths)

        data = []
        for filepath in filepaths:
            d = np.fromfile(filepath, dtype=np.int16) # TODO: Make type variable later
            data.append(d)

        data = np.array(data).flatten().astype(np.float32).view(np.complex64) # TODO: and change this to variable...
        self.dataSignal.emit(data)




    
