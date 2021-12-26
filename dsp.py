'''
Excerpts from my own icyveins7/pydsproutines. 
Did not want to include as submodule as some dependencies there are unnecessary.
Also, some methods may have variations from the original versions.
'''

import numpy as np
import scipy as sp
import scipy.signal as sps

def makeFreq(length, fs):
    freq = np.zeros(length)
    for i in range(length):
        freq[i] = i/length * fs
        if freq[i] >= fs/2:
            freq[i] = freq[i] - fs
    return freq

def estimateBaud(x: np.ndarray, fs: float):
    '''
    Estimates baud rate of signal. (CM21)

    Parameters
    ----------
    x : np.ndarray
        Signal vector.
    fs : float
        Sample rate.

    Returns
    -------
    estBaud : float
        Estimated baudrate.
    idx1
        First index of fft vector used. The index is a peak that was found after
        applying fftshift to the fft of the signal. That is, the peak value should
        be "fftshift(fft(abs(signal)))[idx1]".
    idx2
        Second index of fft vector used. Similar to the first.
    Xf
        fftshift(fft(abs(signal))) i.e. the FFT of the abs signal, described in idx1.
    freq
        freq vector (fft shifted) to apply the indices idx1 and idx2 to directly.

    '''
    Xf = np.fft.fftshift(np.fft.fft(np.abs(x)))
    Xfabs = np.abs(Xf)
    freq = np.fft.fftshift(makeFreq(x.size, fs))
    # Find the peaks
    peaks, _ = sps.find_peaks(Xfabs)
    prominences = sps.peak_prominences(Xfabs, peaks)[0]
    # Sort prominences
    si = np.argsort(prominences)
    peaks = peaks[si]
    b1 = freq[peaks[-2]] # 2nd highest, 1st highest is the centre
    b2 = freq[peaks[-3]] # 3rd highest

    # Average the 2
    estBaud = (np.abs(b1) + np.abs(b2)) / 2
    
    return estBaud, peaks[-2], peaks[-3], Xf, freq