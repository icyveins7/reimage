# This is some alpha work for a library that allows extraction of data to a separate python process.

from multiprocessing.connection import Listener, Client, wait
from PySide6.QtCore import QObject, Signal, Slot, QThread
import time
import pickle
import numpy as np

# TODO: make editable port
reimage_default_address = ('localhost', 5000)

#%% Reimage App side
class ReimageListenerThread(QThread):
    # Going to leave the attached data here instead of as an instance variable
    # since it doesn't really matter..
    reimSelectedData = None
    reimSelectedFilepaths = []
    reimSelectedDataIndices = []

    @Slot(list, list, np.ndarray)
    def setSelectedData(self, filepaths, indices, data):
        self.reimSelectedData = data
        self.reimSelectedFilepaths = filepaths
        self.reimSelectedDataIndices = indices

    def run(self):
        with Listener(reimage_default_address) as listener:
            end = False
            while not end:
                # waited = wait([listener], timeout=1.0) # doesn't work as you'd think
                # print(waited)
                try:
                    with listener.accept() as conn:
                        print('connection accepted from', listener.last_accepted)
                        cmd = conn.recv_bytes()

                        if cmd == b'0':
                            print("Exiting gracefully.")
                            end = True
                            break
                        elif cmd == b'1':
                            print("sending selected data")
                            package = {
                                'time': time.time(),
                                'data': self.reimSelectedData,
                                'filepaths': self.reimSelectedFilepaths,
                                'indices': self.reimSelectedDataIndices
                            }
                            conn.send_bytes(pickle.dumps(package))
                except EOFError as e:
                    print("EOFError: %s" % (str(e)))
                except Exception as e:
                    print("Unknown error: %s" % (str(e)))

    def graceful_kill(self):
        # should i make this a staticmethod?
        with Client(reimage_default_address) as conn:
            conn.send_bytes(b'0')

#%% Client side
def getReimageData(address: tuple=reimage_default_address):
    package = None
    with Client(address) as conn:
        conn.send_bytes(b'1')
        package = pickle.loads(conn.recv_bytes())
        print(package)
    return package


#%% Basic testing
if __name__ == "__main__":
    l = ReimageListenerThread()
    l.start() # use start to ensure it goes to another thread
    input() # this is just here to make sure the python script doesn't end instantly
    print(l.isRunning())