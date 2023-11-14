from PySide6.QtWidgets import QFrame, QVBoxLayout, QHBoxLayout, QPushButton, QFileDialog
from PySide6.QtWidgets import QListWidget, QListWidgetItem, QAbstractItemView, QLineEdit, QMessageBox
from PySide6.QtCore import Qt, Signal, Slot, QEvent
from PySide6.QtGui import QColor, QBrush, QShortcut, QKeySequence
import os
import numpy as np
import scipy.io as sio
import sqlite3 as sq
import operator

#%%
class FileListItem(QListWidgetItem):
    def __init__(self, *args, **kwargs):
        super.__init__(*args, **kwargs)


#%%
class FileListFrame(QFrame):
    dataSignal = Signal(np.ndarray, list, list)
    # sampleRateSignal = Signal(int)
    newFilesSignal = Signal(str, int, list)
    fileListStatusTip = Signal(str)

    def __init__(self, db, parent=None, f=Qt.WindowFlags()):
        super().__init__(parent, f)
        self.setMaximumWidth(380)

        # Enable hover events, for status tips
        self.setAttribute(Qt.WA_Hover)

        # Create the file list widget
        self.flw = QListWidget()
        self.flw.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.flw.setDragEnabled(True)
        self.flw.setSortingEnabled(True)

        # Create the ordering list widget
        self.ow = QListWidget()
        self.ow.setFixedWidth(25)
        self.flw.verticalScrollBar().valueChanged.connect(self.ow.verticalScrollBar().setValue)
        self.ow.verticalScrollBar().hide()
        self.ow.horizontalScrollBar().hide()
        self.ow.verticalScrollBar().setStyleSheet("width: 0px")
        self.ow.horizontalScrollBar().setStyleSheet("height: 0px")
        
        # Need a vertical layout for the orderwidget to align
        self.ovlayout = QVBoxLayout()
        self.ovlayout.addWidget(self.ow)
        self.ovlayout.addStretch()

        # Need a horizontal layout for the two lists
        self.hlayout = QHBoxLayout()
        self.hlayout.setSpacing(0)
        self.hlayout.addWidget(self.flw)
        # self.hlayout.addWidget(self.ow)
        self.hlayout.addLayout(self.ovlayout)
        
        # Sublayout for buttons
        self.btnLayout = QHBoxLayout() # TODO: change layout max width?
        # Some buttons..
        self.prepareFileBtn()
        self.prepareFolderBtn()
        self.prepareClearBtn()
        self.prepareAddBtn()

        # Create a searchbar
        self.searchEdit = QLineEdit()
        self.searchEdit.setPlaceholderText("Filter files..")
        self.searchEdit.textEdited.connect(self.filterFiles)

        # Create the main layout
        self.layout = QVBoxLayout()
        self.layout.addLayout(self.btnLayout) # Buttons at the top
        self.layout.addWidget(self.searchEdit)
        self.layout.addLayout(self.hlayout)
        # self.layout.addWidget(self.flw) # List below it
        self.setLayout(self.layout)

        # Internal memory
        self.filepaths = []
        self.order = {}

        # Create keyboard shortcut for file deletion
        self.delShortcut = QShortcut(QKeySequence("Delete"), self)
        self.delShortcut.activated.connect(self.removeFilesFromList)

        # Create keyboard shortcut for adding files to viewer
        self.addShortcut = QShortcut(QKeySequence("Return"), self)
        self.addShortcut.activated.connect(self.onAddBtnClicked)

        # Allow double-click for opening of single files
        self.flw.itemDoubleClicked.connect(self.doubleClickOpen)

        # Initialize database for the filelist cache
        self.db = db # Sqlite3 connection object
        self.initFileListDBCache()
        self.refreshFileListFromDBCache()

        # File settings
        self.fmt = np.int16
        self.headersize = 0
        self.usefixedlen = False
        self.fixedlen = -1
        self.invSpec = False
        self.sampleStart = 0

    ####################
    @Slot(QListWidgetItem)
    def doubleClickOpen(self, item: QListWidgetItem):
        # Simply pass it over to the standard handler
        self.onAddBtnClicked()

    ####################
    @Slot()
    def removeFilesFromList(self):
        filepaths = [i.text() for i in self.flw.selectedItems()]
        rows = [i.row() for i in self.flw.selectionModel().selectedIndexes()]

        # Raise a dialog to check
        confirmation = QMessageBox.question(self,
            "Confirm files' removal from list",
            "Are you sure you want to remove these %d files?" % len(rows),
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.Yes
        )

        if confirmation == QMessageBox.Yes:
            # Iterate backwards so the row numbers don't change
            for i in range(self.flw.count()-1,-1,-1):
                if i in rows:
                    self.flw.takeItem(i)


    ####################
    @Slot(str)
    def filterFiles(self, txt: str):
        if txt == '':
            # Reload the internal memory
            self.flw.clear()
            self.flw.addItems(self.filepaths)
        else:
            # Query internal memory
            searchFiles = [f for f in self.filepaths if txt in f]
            self.flw.clear()
            self.flw.addItems(searchFiles)
        
        # Reload the order widget based on the file list
        self.initOrderWidget()
        self.refreshOrderWidget()

    ####################
    def getCurrentFilelist(self):
        return [self.flw.item(i).text() for i in range(self.flw.count())]

    @Slot(list)
    def highlightFiles(self, bools: list):
        for i in range(self.flw.count()):
            if bools[i]:
                self.flw.item(i).setForeground(Qt.red)

            else:
                self.flw.item(i).setForeground(Qt.black)

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

        noLongerExist = 0
        for i in range(len(rpaths)):
            item = QListWidgetItem(rpaths[i])
            if os.path.exists(rpaths[i]): # If file still exists
                item.setToolTip("Size: %d bytes" % (os.path.getsize(rpaths[i])))
                self.flw.addItem(item)
            else: # If it doesn't, remove it from the database
                noLongerExist += 1
                cur.execute("delete from filelistcache where path=?", (rpaths[i],)) # TODO: test if this works

        # Update the cache again (in case some files were deleted)
        self.updateFileListDBCache()
        # Set order widget
        self.initOrderWidget()
        # Update internal memory
        self.filepaths.extend(rpaths)

        

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
        # Update internal list
        self.filepaths = []


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
            # self.flw.addItems(fileNames) # DEPRECATED
            for i in range(len(fileNames)):
                item = QListWidgetItem(fileNames[i])
                item.setToolTip("Size: %d bytes" % (os.path.getsize(fileNames[i])))
                self.flw.addItem(item)
        # Update cache
        self.updateFileListDBCache()
        # Set order widget
        self.initOrderWidget()
        # Update internal memory
        self.filepaths.extend(fileNames)

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
            for i in range(len(fileNames)):
                item = QListWidgetItem(fileNames[i])
                item.setToolTip("Size: %d bytes" % (os.path.getsize(fileNames[i])))
                self.flw.addItem(item)
            
        # Update internal memory
        self.filepaths.extend(fileNames)

        # Update cache
        self.updateFileListDBCache()
        # Set order widget
        self.initOrderWidget()
    
    ####################
    def prepareAddBtn(self):
        self.addBtn = QPushButton("Add to Viewer")
        self.btnLayout.addWidget(self.addBtn)

        self.addBtn.clicked.connect(self.onAddBtnClicked)

    '''This now invokes the settings dialog first.'''
    @Slot()
    def onAddBtnClicked(self):
        filepaths = [i.text() for i in self.flw.selectedItems()]
        # We can now handle the case where .wav files are loaded
        if any(".wav" in file for file in filepaths):
            if len(filepaths) > 1:
                # Raise a dialog to check
                wavError = QMessageBox.critical(self,
                    "Wav file support is limited to one at a time.",
                    QMessageBox.Ok,
                    QMessageBox.Ok
                )
            else:
                samplerate, _ = sio.wavfile.read(filepaths[0])
                # self.sampleRateSignal.emit(samplerate)
                self.newFilesSignal.emit("wav", samplerate, filepaths)


        # For everything else, as it used to be
        else:
            self.newFilesSignal.emit("", None, filepaths)


    '''This is now the second step of loading, after settings are confirmed.'''
    @Slot()
    def loadFiles(self):
        filepaths = [i.text() for i in self.flw.selectedItems()]
        rows = [i.row() for i in self.flw.selectionModel().selectedIndexes()]
        print(filepaths)
        print(rows)

        data = []
        sampleStarts = [0]

        ### TODO: have a more structured way of reading wavs
        if any(".wav" in file for file in filepaths):
            # Only load the single wav file
            samplerate, wavdata = sio.wavfile.read(filepaths[0])
            print(samplerate)
            scaling = 2**(wavdata.dtype.itemsize * 8) if not np.issubdtype(wavdata.dtype, np.floating) else 1.0 # Scale appropriately for all integer-based
            print("scaling = %f" % scaling)
            # Compress to single channel and write as floats
            if wavdata.ndim > 1:
                wavdata = np.sum(wavdata.astype(np.float32), axis=1) / scaling
            else:
                wavdata = wavdata.astype(np.float32) / scaling
            assert(np.all(np.abs(wavdata) <= 1.0))
            data.append(wavdata)
            data = np.array(data).flatten()
            print(data.shape)
            self.dataSignal.emit(data, filepaths, sampleStarts)
            # Properly format the order widget
            self.order.clear()
            self.initOrderWidget()
            self.order[filepaths[0]] = 0
            self.refreshOrderWidget()
            return

        ### TODO: end of wav file handling

        if self.usefixedlen:
            cnt = self.fixedlen
        else:
            cnt = -1

        # Reset the order first
        self.order.clear()
        self.initOrderWidget()
        for i in range(len(filepaths)):
            filepath = filepaths[i]
            d = np.fromfile(
                filepath, dtype=self.fmt, count=cnt*2, # x2 for complex samples
                offset=self.headersize + self.sampleStart*self.fmt(1).itemsize*2) # offset from the sample start as well if provided
            data.append(d)
            
            sampleStarts.append(int(d.size/2 + sampleStarts[-1]))

            # Add to internal memory of current files
            self.order[filepath] = i

        self.refreshOrderWidget()

        data = np.array(data).flatten().astype(np.float32).view(np.complex64)
        if self.invSpec:
            data = data.conj()
        self.dataSignal.emit(data, filepaths, sampleStarts)


    ##################
    def initOrderWidget(self):
        self.ow.clear()
        self.ow.addItems(["-" for i in range(self.flw.count())])
        for i in range(self.ow.count()):
            self.ow.item(i).setTextAlignment(Qt.AlignRight)

    def refreshOrderWidget(self):
        # This method assumes the internal memory is set, so use that to repaint the widget
        # Also remember to first call the initOrderWidget() if the file list changes
        for i in range(self.flw.count()):
            if self.flw.item(i).text() in self.order:
                self.ow.item(i).setText(str(self.order[self.flw.item(i).text()]))
        
    ###################
    def event(self, event):
        '''Override events for status tips.'''
        if event.type() == QEvent.HoverEnter:
            if self.flw.count() == 0:
                self.fileListStatusTip.emit(
                    "Populate list with files using 'Open Files'/'Open Folder'.")
            else:
                self.fileListStatusTip.emit(
                    "Select files: (Shift/Ctrl)+LeftClick. Render plots: 'Add To Viewer'. Depopulate list: 'Del' key or 'Clear'."
                )
        # elif event.type() == QEvent.HoverLeave:
        #     print("leave") # TODO: do we need this?
        return super().event(event)

    ####################
    @Slot()
    def onResizedWindow(self):
        # Adjust the two list widgets nicely
        self.ow.resize(
            25, self.flw.height() #  - self.flw.horizontalScrollBar().height()
        )
    

# %%
