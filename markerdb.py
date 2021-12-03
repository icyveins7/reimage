import sqlite3 as sq
from PySide6.QtCore import Qt, Signal, Slot, QRectF

'''
Database is designed with just one table called 'markers'.
Columns are 'filepath, samplenumber, label'.
'''

class MarkerDB:
    def __init__(self, filepath="markers.db"):
        self.con = sq.connect(filepath)
        self.cur = self.con.cursor()
        self.initTable()

    def initTable(self):
        self.cur.execute("create table if not exists markers(filepath TEXT, samplenumber INTEGER, label TEXT)")
        self.con.commit()

    def addMarkers(self, filepaths, sampleNumbers, labels):
        self.cur.executemany("insert into markers values(?,?,?)", (filepaths, sampleNumbers, labels))
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
