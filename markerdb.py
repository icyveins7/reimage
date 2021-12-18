import sqlite3 as sq
from PySide6.QtCore import Qt, Signal, Slot, QRectF

'''
Database is designed with just one table called 'markers'.
Columns are 'filepath, samplenumber, label'.

Note that samplenumber here is with respect to a sample rate of 1.
This is akin to saving (time) * (fs) as the sample rate.
If markers are added/deleted from the database while the signal viewer
has a different sample rate (due to settings of fs, dsr) then it should be
scaled back to the sample rate of 1 (by multiplying with the fs alone) first.
'''

class MarkerDB:
    def __init__(self, filepath="markers.db"):
        self.con = sq.connect(filepath)
        self.cur = self.con.cursor()
        self.initTable()

    def initTable(self):
        self.cur.execute("create table if not exists markers(filepath TEXT, samplenumber REAL, label TEXT, UNIQUE(filepath, samplenumber))")
        self.con.commit()

    def addMarkers(self, filepaths, sampleNumbers, labels):
        insertList = [(filepaths[i], sampleNumbers[i], labels[i]) for i in range(len(filepaths))]
        self.cur.executemany("insert into markers values(?,?,?)", insertList)
        self.con.commit()

    def getMarkers(self, filepaths):
        self.cur.execute("select * from markers where filepath in (%s)" % ','.join('?'*len(filepaths)), filepaths)
        r = self.cur.fetchall()
        sfilepaths = [i[0] for i in r]
        sampleNumbers = [i[1] for i in r]
        labels = [i[2] for i in r]

        return sfilepaths, sampleNumbers, labels

    def delMarkers(self, filepaths, sampleNumbers):
        for i in range(len(filepaths)):
            self.cur.execute("delete from markers where filepath=? and samplenumber=?", (filepaths[i], sampleNumbers[i]))
        self.con.commit()

    def checkMarkers(self, filepaths, sampleNumbers):
        blist = []
        for i in range(len(filepaths)):
            # Retrieve the existing pairs
            self.cur.execute("select * from markers where filepath = ? and samplenumber = ?", (filepaths[i], sampleNumbers[i]))
            r = self.cur.fetchone()
            if r is None:
                blist.append(False)
            else:
                blist.append(True)

        return blist