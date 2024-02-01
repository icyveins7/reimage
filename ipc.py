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
    # Some helpful 'define' constants
    EXIT_COMMAND = b'0'
    EXPORT_COMMAND = b'1'
    EXPORT_RAW_COMMAND = b'2'
    RAW_DTYPE = {
        np.dtype('complex64'): b'0',
        np.dtype('complex128'): b'1'
    }

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

                        if cmd == self.EXIT_COMMAND:
                            print("Exiting gracefully.")
                            end = True
                            break

                        elif cmd == self.EXPORT_COMMAND:
                            print("sending selected data")
                            package = {
                                'time': time.time(),
                                'data': self.reimSelectedData,
                                'filepaths': self.reimSelectedFilepaths,
                                'indices': self.reimSelectedDataIndices
                            }
                            conn.send_bytes(pickle.dumps(package))

                        elif cmd == self.EXPORT_RAW_COMMAND: 
                            # Use this for MATLAB interface since pickle doesn't work
                            print("Sending raw data array alone.")
                            conn.send_bytes(self.RAW_DTYPE[self.reimSelectedData.dtype])
                            conn.send_bytes(self.reimSelectedData.tobytes())

                        else:
                            # Receive data for plotting
                            print("Receiving data.")
                            print(pickle.loads(cmd))

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
    """
    Extracts the data you exported from ReImage.

    Parameters
    ----------
    address : tuple, optional
        Tuple of IP address & port, by default ('localhost', 5000)

    Returns
    -------
    result : dict
        Unpickled dictionary with the following keys:
            'data' : np.ndarray
                The selected data from ReImage.
            'time' : float
                Unix time of export.
            'filepaths': list
                List of strings of the exported filepaths.
            'indices' : list
                List of 2 indices denoting the indices used for the selection.
                Together with the 'filepaths', you should be able to double-check
                that the data you exported is the same as if you had done it manually.
    """
    package = None
    with Client(address) as conn:
        conn.send_bytes(b'1')
        package = pickle.loads(conn.recv_bytes())
        print(package)
    return package

def getReimageDataRaw(address: tuple=reimage_default_address):
    # This shouldn't be the one used when in python
    # It's just here for testing purposes

    data = None
    with Client(address) as conn:
        conn.send_bytes(ReimageListenerThread.EXPORT_RAW_COMMAND)
        dtype = conn.recv_bytes()
        print(dtype)
        parsed_dtypes = {
            b'0': np.complex64,
            b'1': np.complex128
        }
        data = np.frombuffer(conn.recv_bytes(), dtype=parsed_dtypes[dtype])
        print(data)

    return data

def sendReimageData(
    data: np.ndarray,
    fs: float=1.0,
    address: tuple=reimage_default_address
):
    # Pickle the item first
    pickled = pickle.dumps(
        {
            'data': data,
            'fs': fs
        }
    )

    # TODO:
    # 1) Get default config
    # 2) Set the bare minimum; don't allow anything beyond fs/nfft setting
    # 3) Set this config in main
    # 4) Set the new YData in signal view

    # Send it
    with Client(address) as conn:
        conn.send_bytes(pickled)


#%% Basic testing
if __name__ == "__main__":
    l = ReimageListenerThread()
    l.start() # use start to ensure it goes to another thread
    input() # this is just here to make sure the python script doesn't end instantly
    print(l.isRunning())