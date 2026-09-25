# Q Layer Tuner v2.1 for Windows

## Run

1. Extract the downloaded ZIP.
2. Double-click Q_Layer_Tuner_v2.1_Windows_x64.exe.
3. The app opens in your default browser. Keep the small launcher window open.
4. Click Quit in the launcher when finished.

Windows 10/11, 64-bit x64. A current Edge, Chrome or Firefox browser is required.
Python and the calculation engine are included. No Python installation, administrator
access or internet connection is needed. The browser address is local to your computer.
If the browser does not open automatically, click Open app or copy the address displayed
in the launcher. The first launch can take a few seconds to unpack the included files.

The Recipe, Calibration and measured As/P fitting functions match the v2.1 website.
Calculations run in bundled native Python. Each launch starts a new session: use Save
calibrations JSON before closing and Load saved calibrations JSON next time.
This app does not control growth hardware.

This personal build is not digitally signed. Windows may display a publisher/reputation
warning. SHA256SUMS.txt identifies the exact executable produced by the build.

## Rebuild from source

On Windows x64 with Python 3.12 installed:

    py -3.12 -m pip install pyinstaller==6.16.0
    py -3.12 build_windows.py

The executable and ZIP appear in windows-dist/. The build runs the packaged executable
from a different working directory and checks its launcher, assets, recipe calculation,
As/P fitting and calibration JSON round trip. See windows-smoke-test.json for results.

GitHub Actions also builds it using the Build Windows executable workflow.
Scientific calculations and the GitHub Pages deployment are unchanged.
