from PySide6.QtWidgets import QFrame, QVBoxLayout, QHBoxLayout, QPushButton, QFileDialog
from PySide6.QtWidgets import QListWidget, QListWidgetItem, QAbstractItemView
from PySide6.QtCore import Qt, Signal, Slot
import os
import numpy as np
import sqlite3 as sq
import operator

#%%
class FileListItem(QListWidgetItem):
    def __init__(self, *args, **kwargs):
        super.__init__(*args, **kwargs)


#%%
class FileListFrame(QFrame):
    dataSignal = Signal(np.ndarray, list, list)

    def __init__(self, db, parent=None, f=Qt.WindowFlags()):
        super().__init__(parent, f)
        self.setMaximumWidth(380)

        # Create the file list widget
        self.flw = QListWidget()
        self.flw.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.flw.setDragEnabled(True)
        
        # Sublayout for buttons
        self.btnLayout = QHBoxLayout() # TODO: change layout max width?
        # Some buttons..
        self.prepareFileBtn()
        self.prepareFolderBtn()
        self.prepareClearBtn()
        self.prepareAddBtn()

        # Create the main layout
        self.layout = QVBoxLayout()
        self.layout.addLayout(self.btnLayout) # Buttons at the top
        self.layout.addWidget(self.flw) # List below it
        self.setLayout(self.layout)

        # Initialize database for the filelist cache
        self.db = db # Sqlite3 connection object
        self.initFileListDBCache()
        self.refreshFileListFromDBCache()

    ####################
    def initFileListDBCache(self):
        cur = self.db.cursor()
        cur.execute("create table if not exists filelistcache(idx INTEGER primary key, path TEXT NOT NULL UNIQUE);")
        self.db.commit()

    def updateFileListDBCache(self):
        cur = self.db.cursor()
        cur.execute("delete from filelistcache")
        filepaths = [self.flw.item(i).text() for i in range(self.flw.count())]
        cachelist = [(i, filepaths[i]) for i in range(len(filepaths))]
        cur.executemany("insert into filelistcache values(?,?)", cachelist)
        self.db.commit()

    def refreshFileListFromDBCache(self):
        cur = self.db.cursor()
        cur.execute("select * from filelistcache")
        r = cur.fetchall()
        r = sorted(r, key=operator.itemgetter(0)) # sort by the index, which is the first value in the tuples
        rpaths = [i[1] for i in r]
        self.flw.addItems(rpaths)
        
    ####################
    def prepareClearBtn(self):
        self.clearBtn = QPushButton("Clear")
        self.clearBtn.setMaximumWidth(40)
        self.btnLayout.addWidget(self.clearBtn)

        self.clearBtn.clicked.connect(self.onClearBtnClicked)

    @Slot()
    def onClearBtnClicked(self):
        self.flw.clear()
        # Update cache
        self.updateFileListDBCache()


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
        # Update cache
        self.updateFileListDBCache()

    ####################
    def prepareFolderBtn(self):
        self.oFolderBtn = QPushButton("Open Folder")
        self.btnLayout.addWidget(self.oFolderBtn)

        self.oFolderBtn.clicked.connect(self.onFolderBtnClicked)

    @Slot()
    def onFolderBtnClicked(self):
        folderName = QFileDialog.getExistingDirectory()
        if folderName is not None and len(folderName)>0:
            folderFiles = os.listdir(folderName)
            fileNames = [os.path.join(folderName, i) for i in folderFiles]
            self.flw.addItems(fileNames)
        # Update cache
        self.updateFileListDBCache()
    
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
        sampleStarts = [0]
        for filepath in filepaths:
            d = np.fromfile(filepath, dtype=np.int16) # TODO: Make type variable later
            data.append(d)
            sampleStarts.append(d.size + sampleStarts[-1])

        data = np.array(data).flatten().astype(np.float32).view(np.complex64) # TODO: and change this to variable...
        self.dataSignal.emit(data, filepaths, sampleStarts)




    
