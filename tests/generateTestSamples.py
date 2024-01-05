import numpy as np
import os
import scipy.signal as sps

# Create folder testdata/ one level up
testdataDir = os.path.join(os.path.dirname(os.path.realpath(__file__)), '..', 'testdata')
if not os.path.exists(testdataDir):
    os.makedirs(testdataDir)

# Create a simple bpsk signal and displace it
baud = int(10e6)
bits = np.random.randint(0,2,baud)*2-1
syms = sps.resample_poly(bits.astype(np.complex64), 10, 1) # 10x OSR
print(syms)
sig = syms + (np.random.randn(syms.size)+np.random.randn(syms.size)*1j) * np.sqrt(2 * 0.01)
sig = sig * 10000 # some scaling for integer precision later
sig = sig.astype(np.complex64).view(np.float32).astype(np.int16)
print(sig)

# Save the signal
sig.tofile(os.path.join(testdataDir, 'bpsk_100MSps.dat'))

