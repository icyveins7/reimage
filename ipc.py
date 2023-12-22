# This is some alpha work for a library that allows extraction of data to a separate python process.

from multiprocessing.connection import Listener, Client, wait
from PySide6.QtCore import QObject, Signal, Slot, QThread

reimage_default_address = ('localhost', 5000)

#%% Reimage App side
class ReimageListenerThread(QThread):
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
                            print("sending hello")
                            conn.send_bytes(b'hello')
                except EOFError as e:
                    print("EOFError: %s" % (str(e)))
                except Exception as e:
                    print("Unknown error: %s" % (str(e)))
                    
def endReimageListener():
    with Client(reimage_default_address) as conn:
        conn.send_bytes(b'0')

#%% Client side
def getReimageData():
    with Client(reimage_default_address) as conn:
        conn.send_bytes(b'1')
        print(conn.recv_bytes())


#%% Basic testing
if __name__ == "__main__":
    l = ReimageListenerThread()
    l.start()
    input()
    print(l.isRunning())