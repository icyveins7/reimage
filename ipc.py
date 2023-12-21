# This is some alpha work for a library that allows extraction of data to a separate python process.

from multiprocessing.connection import Listener, Client
from PySide6.QtCore import QObject, Signal, Slot, QThread

reimage_default_address = ('localhost', 5000)

#%% Reimage App side
class ReimageListenerThread(QThread):
    def run(self):
        with Listener(reimage_default_address, authkey=b'secret') as listener:
            while True:
                with listener.accept() as conn:
                    print('connection accepted from', listener.last_accepted)

                    conn.send_bytes(b'hello')
                    


#%% Client side
def getReimageData():
    client = Client(reimage_default_address, authkey=b'secret')
    print(client.writable)
    with Client(reimage_default_address) as conn:
        print(conn.recv_bytes())
