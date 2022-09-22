'''
Excerpts from my own icyveins7/pydsproutines. 
Did not want to include as submodule as some dependencies there are unnecessary.
Also, some methods may have variations from the original versions.
'''

import numpy as np
import scipy as sp
import scipy.signal as sps
import warnings

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


#%% Excerpt from icyveins7/pydsproutines, extracted at 80ddeed.
# Changes:
# 1. Timer class commented out.
# 2. Numba calls exchanged with original pythonic loop.

# Generic simple demodulators
class SimpleDemodulatorPSK:
    '''
    Generic demodulator implementation for BPSK/QPSK/8PSK.
    This uses a dot product method to detect which symbol in the constellation is present.
    
    The default constellation-bit mappings are provided as gray-mapped bits,
    but this can be changed.
    '''
    
    # These default psk constellations are provided only for the basic class.
    # The specialised classes use their own constellations which are optimised for demodulation.
    pskdicts = { # This is a monotonically increasing index for each increase in angle
        2: np.array([1.0, -1.0], dtype=np.complex128),
        4: np.array([1.0, 1.0j, -1.0, -1.0j], dtype=np.complex128),
        8: np.array([1.0,
                     np.sqrt(2)/2 * (1+1j),
                     1.0j,
                     np.sqrt(2)/2 * (-1+1j),
                     -1.0,
                     np.sqrt(2)/2 * (-1-1j),
                     -1.0j,
                     np.sqrt(2)/2 * (1-1j)], dtype=np.complex128)
    }
    # This is a specific bit mapping for each corresponding index i.e. each angle, in increasing order
    # E.g. QPSK/8PSK are gray mapped.
    pskbitmaps = { 
        2: np.array([0b1, 0b0], dtype=np.uint8),
        4: np.array([0b11, 0b01, 0b00, 0b10], dtype=np.uint8),
        8: np.array([0b000,
                     0b001,
                     0b011,
                     0b010,
                     0b110,
                     0b111,
                     0b101,
                     0b100], dtype=np.uint8)
    }
    
    def __init__(self, m: int, bitmap: np.ndarray=None, cluster_threshold: float=0.1):
        self.m = m
        self.const = self.pskdicts[self.m]
        self.normVecs = self.const.view(np.float64).reshape((-1,2))
        self.bitmap = self.pskbitmaps[self.m] if bitmap is None else bitmap
        self.cluster_threshold = cluster_threshold
        
        # Interrim output
        self.xeo = None # Selected eye-opening resample points
        self.xeo_i = None # Index of eye-opening
        self.eo_metric = None # Metrics of eye-opening
        self.reimc = None # Phase-locked to constellation (complex array)
        self.svd_metric = None # SVD metric for phase lock
        self.angleCorrection = None # Angle correction used in phase lock
        self.syms = None # Output mapping to each symbol (0 to M-1)
        self.matches = None # Output from amble rotation search
        
        
    def getEyeOpening(self, x: np.ndarray, osr: int, abs_x: np.ndarray=None):
        if abs_x is None:
            abs_x = np.abs(x) # Provide option for pre-computed (often used elsewhere anyway)
        x_rs_abs = abs_x.reshape((-1, osr))
        self.eo_metric = np.mean(x_rs_abs, axis=0)
        i = np.argmax(self.eo_metric)
        x_rs = x.reshape((-1, osr))
        return x_rs[:,i], i
        
    def mapSyms(self, reimc: np.ndarray):
        '''
        Maps symbols to values from 0 to m-1. Note that this may not correspond to the 
        bit values desired e.g. gray mapping. In such scenarios, the bitmap should be amended.

        This method does not need to be called directly; it is called as part of demod().
        
        See symsToBits() for actual bit mapping.

        Parameters
        ----------
        reimc : np.ndarray
            Correct eye-opening, frequency corrected and phase-locked complex-valued input.

        Returns
        -------
        syms : np.ndarray
            Output array corresponding to the symbol values 0 to m-1.

        '''
        reimcr = reimc.view(np.float32).reshape((-1,2)).T
        constmetric = self.normVecs @ reimcr
        # Pick the arg max for each column
        syms = np.argmax(constmetric, axis=0).astype(np.uint8)
        
        return syms
    
    def lockPhase(self, reim: np.ndarray):
        # Power into BPSK
        powerup = self.m // 2
        reimp = reim**powerup
        
        # Form the square product
        reimpr = reimp.view(np.float32).reshape((-1,2)).T
        reimsq = reimpr @ reimpr.T
        
        # SVD
        u, s, vh = np.linalg.svd(reimsq) # Don't need vh technically
        # Check the svd metrics
        svd_metric = s[-1] / s[:-1] # Deal with this later when there is residual frequency
        if np.any(svd_metric > self.cluster_threshold):
            warnings.warn("Constellation not well clustered. There may be residual frequency shifts.")
        # Angle correction
        angleCorrection = np.arctan2(u[1,0], u[0,0])
        reimc = self.correctPhase(reim, -angleCorrection/powerup)
        
        return reimc, svd_metric, angleCorrection
    
    def correctPhase(self, reim: np.ndarray, phase: float):
        return reim * np.exp(1j * phase)
        
    
    def demod(self, x: np.ndarray, osr: int, abs_x: np.ndarray=None, verb: bool=True):
        if x.dtype != np.complex64:
            raise TypeError("Input array must be complex64.")
        
        # timer = Timer()
        # timer.start()
        
        # Get eye-opening first
        xeo, xeo_i = self.getEyeOpening(x, osr, abs_x)
        # timer.evt("Eye-opening")
        
        # Correct the global phase first
        reim = np.ascontiguousarray(xeo)
        self.reimc, self.svd_metric, self.angleCorrection = self.lockPhase(reim)
        # timer.evt("lockPhase")
        
        # Generic method: dot product with the normalised vectors
        self.syms = self.mapSyms(self.reimc)
        # timer.evt("mapSyms")
        
        # if verb:
        #     timer.rpt()
        
        return self.syms
    
    def ambleRotate(self, amble: np.ndarray, search: np.ndarray=None, syms: np.ndarray=None):
        if syms is None:
            syms = self.syms
        
        if search is None:
            search = np.arange(syms.size - amble.size + 1)
            
        # Naive loop
        length = amble.size
        m_amble = amble + self.m # Scale it up in order to do uint8 math
        
        # Pythonic loop
        self.matches = np.zeros((search.size, self.m), dtype=np.uint32)
        for i, mi in enumerate(search):
            diff = (m_amble - syms[mi:mi+length]) % self.m
            for k in range(self.m):
                self.matches[i, k] = np.sum(diff == k)
        
        # # Numba loop
        # self.matches = self._ambleSearch(m_amble, search, self.m, syms, length)
        
        # # Numba loop v2
        # self.matches = self._ambleSearch(amble, search, self.m, syms, length)
                
        s, rotation = argmax2d(self.matches)
        sample = search[s] # Remember to reference the searched indices
        self.syms = (syms + rotation) % self.m
        
        return self.syms, sample, rotation
    
    # @staticmethod
    # @njit('uint32[:,:](uint8[:], int32[:], intc, uint8[:], intc)', cache=True, nogil=True)
    # def _ambleSearch(m_amble, search, m, syms, length):
    #     matches = np.zeros((search.size, m), dtype=np.uint32)
    #     for i in np.arange(search.size): # Use np.arange instead of range
    #         mi = search[i]
    #         diff = np.mod((m_amble - syms[mi:mi+length]), m)
            
    #         # One-pass loop
    #         for k in np.arange(diff.size):
    #             matches[i, diff[k]] += 1
        
    #     return matches
    
    # @staticmethod
    # @njit(cache=True, nogil=True) # not well tested yet
    # def _ambleSearchv2(m_amble, search, m, syms, length):
    #     matches = np.zeros((search.size, m), dtype=np.uint32)
    #     for i in np.arange(search.size): # Use np.arange instead of range
    #         mi = search[i]
    #         diff = np.bitwise_xor(amble, syms[mi:mi+length])
    #         # One-pass loop
    #         for k in np.arange(diff.size):
    #             matches[i, -1-diff[k]] += 1
        
    #     return matches
        
    def symsToBits(self, syms: np.ndarray=None, phaseSymShift: int=0):
        '''
        Maps each symbol (integer array denoting the angle) to its own bit sequence,
        as specified by the bitmap.

        Parameters
        ----------
        syms : np.ndarray, uint8, optional
            Input symbol sequence. The default is None, which will use the last internally saved
            syms array output.
            
        phaseSymShift : int
            Number of symbols to rotate the bit mapping by.
            Example: m = 4.
                Current bitmap is [3,1,0,2].
                Rotating by 2 symbols equates to a phase shift of pi 
                (or equivalently, phase shift of syms by -pi).

        Returns
        -------
        bits : np.ndarray
            Bit sequence stored as individual bytes i.e. length of this array = length of syms.

        '''
        if syms is None:
            syms = self.syms
        
        return np.roll(self.bitmap, phaseSymShift)[syms]


    
    def unpackToBinaryBytes(self, packed: np.ndarray):
        '''
        Turns an integer valued output from mapSyms()/demod()/symsToBits() into
        a binary-valued array with each row corresponding to the binary value
        of the integer.
        
        Specifically, that means that each bit now occupies one byte in memory,
        hence the name of the method. Contrast this with the packBinaryBytesToBits()
        method which tends to follow.
        
        Example:
            m = 4.
            Input array [0,1,2,3].
            Output is [[0,0],
                       [0,1],
                       [1,0],
                       [1,1]].

        Parameters
        ----------
        packed : np.ndarray
            Integer valued array.

        Returns
        -------
        unpacked : np.ndarray
            Matrix of N x k binary values, where N is the original length of 'packed',
            and k is the number of bits used to represent each value of 'packed',
            given by log2(m).

        '''

        bitsPerVal = int(np.log2(self.m))
        # Unpack as usual
        unpacked = np.unpackbits(packed).reshape((-1,8))
        # Slice the ending bits (default is big-endian)
        unpacked = unpacked[:,-bitsPerVal:]
        
        return unpacked
    
    def packBinaryBytesToBits(self, unpacked: np.ndarray):
        '''
        This is a simple wrapper around numpy's packbits().
        In this context, it takes the unpacked matrix from unpackToBinaryBytes()
        and then compresses it to occupy the minimum requirement of bytes storage.
        
        Example:
            Input (QPSK) array [[0,0],
                                [0,1],
                                [1,0],
                                [1,1]].
            This is compressed to a single byte corresponding to 
            [0,0,0,1,1,0,1,1], which is then returned as array([27]).

        Parameters
        ----------
        unpacked : np.ndarray
            Input unpacked bits, usually from unpackToBinaryBytes().

        Returns
        -------
        packed : np.ndarray
            Packed bits storage of the input.
        '''
        return np.packbits(unpacked.reshape(-1))
        
    
###############
class SimpleDemodulatorBPSK(SimpleDemodulatorPSK):
    '''
    Faster demodulator implementation specifically for BPSK.
    '''
    def __init__(self, bitmap: np.ndarray=None, cluster_threshold: float=0.1):
        super().__init__(2, bitmap, cluster_threshold)
        
    def mapSyms(self, reimc: np.ndarray):
        # Simply get the real
        re = np.real(reimc)
        
        # And check sign
        syms = (re < 0).astype(np.uint8)
        
        return syms
        
    
    
###############
class SimpleDemodulatorQPSK(SimpleDemodulatorPSK):
    '''
    Faster demodulator implementation specifically for QPSK.
    '''
    def __init__(self, bitmap: np.ndarray=None, cluster_threshold: float=0.1):
        super().__init__(4, bitmap, cluster_threshold)
    
        self.gray4 = np.zeros((2,2), dtype=np.uint8)
        self.gray4[1,1] = 0
        self.gray4[0,1] = 1
        self.gray4[0,0] = 2
        self.gray4[1,0] = 3
        # This is X,Y > 0 gray encoded
        
    def mapSyms(self, reimc: np.ndarray):
        # Reshape
        reimd = reimc.view(np.float32).reshape((-1,2))
        
        # # Compute comparators
        # xp = (reimd[:,0] > 0).astype(np.uint8)
        # yp = (reimd[:,1] > 0).astype(np.uint8)
        
        # # Now map
        # idx = np.vstack((xp,yp))
        # # Convert to constellation integers
        # syms = self.gray4[tuple(idx)]
        
        # New one-liner, prevents multiple comparator calls hence faster?
        syms = self.gray4[tuple((reimd > 0).T.astype(np.uint8))]
        
        return syms
    
    def correctPhase(self, reim: np.ndarray, phase: float):
        # For gray-coding comparators, we move to the box
        return reim * np.exp(1j*(phase + np.pi/4)) 

################
class SimpleDemodulator8PSK(SimpleDemodulatorPSK):
    '''
    Faster demodulator implementation specifically for 8PSK.
    '''
    def __init__(self, bitmap: np.ndarray=None, cluster_threshold: float=0.1):
        super().__init__(8, bitmap, cluster_threshold)
        
        # For the custom constellation, we don't map to a number but rather to the N-D index,
        # mirroring the actual bits.
        self.map8 = np.zeros((2,2,2), dtype=np.uint8)
        self.map8[1,1,1] = 0
        self.map8[0,1,1] = 1
        self.map8[1,0,1] = 2
        self.map8[0,0,1] = 3
        self.map8[1,1,0] = 4
        self.map8[0,0,0] = 5
        self.map8[1,0,0] = 6
        self.map8[0,1,0] = 7
        
    def mapSyms(self, reimc: np.ndarray):
        # 8PSK specific, add dimensions
        reimd = reimc.view(np.float32).reshape((-1,2))
        scaling = np.max(self.eo_metric) # Assumes eye-opening has been done
        reim_thresh = np.abs(np.abs(np.cos(np.pi/8)*scaling) - np.abs(np.sin(np.pi/8)*scaling))
        # Compute |X| - |Y|
        xmy = np.abs(reimd[:,0]) - np.abs(reimd[:,1])
        # And then | |X| - |Y| | + c, this transforms into QPSK box below XY plane
        # with the new QPSK diamond above XY plane
        z = np.abs(xmy) - reim_thresh # Do not stack into single array, no difference anyway
        
        # C1: Check Z > 0; if + check even (diamond), if - check odd (QPSK, box)
        c1z = z > 0
        
        # C2: Z+ check XY and end, Z- check |X|-|Y| and C3
        cx2 = reimd[:,0] > 0
        cy2 = reimd[:,1] > 0
        cxmy2 = xmy > 0

        # C3: + check X, - check Y
        cx3 = np.logical_and(cxmy2, cx2)
        cy3 = np.logical_and(np.logical_not(cxmy2), cy2)
        
        # Build backwards
        idx1 = cxmy2
        idx2 = np.logical_or(cx3, cy3)
        
        idx1 = np.logical_or(np.logical_and(c1z, idx1), np.logical_and(np.logical_not(c1z), cx2))
        idx2 = np.logical_or(np.logical_and(c1z, idx2), np.logical_and(np.logical_not(c1z), cy2))
        
        idx0 = c1z
        
        # Now map
        idx = np.vstack((idx0.astype(np.uint8),idx1.astype(np.uint8),idx2.astype(np.uint8)))
        # Converts to the default demodulator constellation integers
        syms = self.map8[tuple(idx)] # Needs to be vstack, and need the tuple(); need each value to be a column of indices
        
        return syms