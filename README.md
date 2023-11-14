# ReImage 

![PyInstaller CI/CD](https://github.com/icyveins7/reimage/actions/workflows/main.yaml/badge.svg)

ReImage is a Python 3 + PySide6 + PyQtGraph app for quickly visualizing recorded RF data in the form of real and imaginary samples. Think of it as Adobe Audition or Audacity, but for raw complex samples.

The goals for this project are to provide quick, offline ways of examining recorded data. As such, it is not meant to do everything DSP-related. It is aimed to be used after performing test recordings to verify that the recordings will be useful for further processing later on. In particular, ReImage attempts to maximise smoothness (frames-per-second) of plots via caching of successive downsampled versions of the data, for a better user experience. This alleviates the 'laggy plot' issue often encountered when using Matplotlib to visualise raw signal data with over about 1 million points, and when using PyQtGraph with over about 10-100M points.

## Installation and Usage (From Source)

To run it from source, it is advisable to create a new virtual environment first; many of the PySide vs PyQt libraries do not play well with each other, so this is highly advised.

Clone this repository with

```bash
git clone https://github.com/icyveins7/reimage.git
```

and then - while in the new virtual environment - install the required libraries with

```bash
pip install -r requirements.txt
```

Note that the requirements file is based on a Python 3.11 install, and may not work exactly if the Python version is different (and especially if it is too old).

If you are using a different Python version and the above doesn't work, you may try

```bash
pip install numpy scipy Pillow pyqtgraph PySide6 sounddevice
```

To run the app,

```bash
python main.py
```

## Usage (From Binaries)

The pre-built binaries in the Releases section are created using [PyInstaller](https://github.com/pyinstaller/pyinstaller). Simply download the tar.gz relevant to your OS and unzip where desired. Then run the 'main' executable.

Alternatively, you may want to look for the latest CI/CD automatic builds in [Actions](https://github.com/icyveins7/reimage/actions) by downloading the artifacts in one of the latest passing workflows.

## Quick-start

![](screenshot.jpg)

Most users should find that the tooltips at the bottom-left and bottom-right of the windows suffice as guidance.

1. Populate the file list via 'Open File(s)' or 'Open Folder'.
2. Select some files in the file list (via Ctrl-Click or Shift-Click). Clear the entire list with the 'Clear' button or specific files via the Delete key.
4. Click 'Add to Viewer' to open the files and view the Amplitude-Time (top) and Spectrogram (bottom) plots. You can also press Enter after selecting the files, or double-click a single file.
5. Scroll in/out using mouse wheel and/or use Left-Click to drag the plots.
6. Use Ctrl-RightClick on the plots to see additional options.

## Issues

This is a personal project and is a constant work-in-progress. As such, there are likely to be many bugs; I will try to attend to any issues posted ASAP but don't count on it being fixed expeditiously. However, if you have ideas on what functionalities you'd like to see, I'd be happy to consider them.

