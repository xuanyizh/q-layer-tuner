# Q Layer Tuner 2.0 — Python core

A web interface for estimating source adjustments for coherent, bulk-like
InGaAsP on InP (001), using measured PL, symmetric 004 XRD and an independently
known In or Ga incorporated rate. No growth hardware is controlled.

## Start on your computer

1. Extract the entire ZIP into one folder. Install Python 3.11 or newer if needed.
2. On Windows, double-click `run_local.bat`. Alternatively, open a terminal in
   this folder and run `python server.py` (`python3 server.py` on some systems).
3. Open **http://127.0.0.1:8000/** in a browser. Keep the terminal open while using
   the app. Stop with Ctrl+C. Use `--port 8001` if port 8000 is occupied.

No pip packages, NumPy, Node or internet connection are required for local use.
Do not open `dist/index.html` directly with a file URL.

## What changed

- The scientific implementation is now `qlayer/engine.py`, using only Python's
  standard library. JavaScript handles the interface and transport.
- As and P use your measured, full fifth-degree valve-to-BEP fits, including
  powers 5, 4, 3, 2, 1 and 0. All coefficients are editable in Calibration.
- The **Bandgap strain correction** selector offers **Off — bulk bandgap
  estimate** (default) and **On — strain-corrected bandgap**.
- Coherent elastic strain in XRD remains active in both modes. The optical
  reference is anchored separately in the selected mode.
- The As recommendation converts the requested BEP through the new fit's bounded
  inverse. An optional P valve reports its BEP; P remains fixed for this recipe
  correction. Both curves have a standalone forward/inverse converter and plots.
- The hosted version runs the same Python package through bundled Pyodide 0.27.7
  in a worker. No Python server is needed for GitHub Pages. The native launcher
  instead sends calculations to Python on your own computer.

## Your current example

Target In/Ga = 0.8/0.2, target PL = 1197 nm, total III rate = 1,
measured PL = 1190 nm, known In rate = 0.8, Ga = 1000 °C, As valve = 100.
Mismatch = +40 arcsec on the theta/omega axis, **film minus substrate**.
All correction steps = 100%; As incorporation exponent n = 1.

| Optical bandgap strain | New Ga temperature | New As valve |
| --- | ---: | ---: |
| Off — bulk estimate | 1000.30329 °C | 101.19148 |
| On — hydrostatic + HH/LH | 1000.70267 °C | 101.73631 |

These are model outputs with the new measured fits, not an exact reconstruction
of the lab application's As 101.3 / Ga 1000.2 result. Confirm the scan axis and
sign convention before comparing numbers. The example defaults load on reset.

## BEP fits and units

`BEP_Torr(V) = 1e-6 * (a5*V^5 + a4*V^4 + a3*V^3 + a2*V^2 + a1*V + a0)`.
The supplied pressure numbers are interpreted as Torr. Valve settings use the
instrument's native numerical units; no conversion to percent is assumed.

| Power | As coefficient | P coefficient |
| --- | ---: | ---: |
| 5 | 1.756885090218417e-11 | -5.934093375573504e-8 |
| 4 | -1.062152867708418e-8 | 1.193629761361735e-5 |
| 3 | 2.303375636708951e-6 | -8.645181786825931e-4 |
| 2 | -1.888671976171941e-4 | 2.694050627382798e-2 |
| 1 | 1.663215617715586e-2 | 1.120292023591050e-1 |
| 0 | -1.661666666666546e-1 | -1.035140340772323e-1 |

Valid ranges: **As 30–270**, **P 5–80**. Extrapolation is disabled. Edited curves
must be positive and strictly increasing over the full measured range.
The fit R² values are 0.99980695 (As) and 0.99997927 (P); maximum absolute
relative residuals at the measurements are 2.26% and 3.98%. These residuals are
not uncertainty bounds. Raw measurements and full-precision coefficients are
in `qlayer/bep_calibration.json`.

## Use the Python core directly

```python
from qlayer import calculate
from qlayer.engine import bep_from_valve, valve_from_bep

r = calculate({
    "targetPL": 1197, "measuredPL": 1190, "mismatch": 40,
    "inRatio": 0.8, "gaRatio": 0.2,
    "knownElement": "In", "knownRate": 0.8,
    "gaTemp": 1000, "asValve": 100,
    "opticalStrain": "off",  # change to "on" for optical strain
    "inStep": 100, "gaStep": 100, "asStep": 100,
})
print(r["settings"]["Ga"]["applied"], r["settings"]["As"]["applied"])
pressure = bep_from_valve("P", 40)  # return value is in Torr
print(pressure, valve_from_bep("P", pressure))
```

`calculate()` merges supplied settings with `DEFAULTS`. `InputError` reports
invalid recipe inputs or an unresolved composition. Invalid As conversion
returns `asError`, retains In/Ga results, and suppresses the As recommendation
and applied prediction. A missing P valve is `None`, not zero. An invalid P
valve generates a notice and no P BEP, while the fixed-P recipe assumption remains.

## Scientific scope

See `MODEL_NOTES.md` for the equations and assumptions. In particular, **BEP
calibration does not establish incorporation efficiency**. The As recipe step
retains a provisional local response `r_As ∝ BEP_As^n`, initially n = 1, with P
supply and growth conditions fixed. The new P curve does not by itself justify
using `BEP_As/(BEP_As+BEP_P)` as the incorporated As fraction.

All growth rates must share the same atomic or III-equivalent basis. The
numerical units of the original source calibration are unverified. No raw
binary thickness-rate conversion is silently applied. The app is a coherent
bulk direct-gap estimate, not a quantum-well or partially relaxed film model.

## Modify, test, and deploy

Canonical Python files are under `qlayer/`. Run `python tools/build.py` after
changing them; this copies them into `dist/python/qlayer/` for static hosting.
The local launcher performs this copy automatically. Change defaults or permanent
calibrations in the canonical files. Form edits last until reload/reset.

Run the checks with Python and Node 20+ available:

```sh
python tools/build.py
python -m unittest discover -s tests -p 'test_*.py' -v
node --test tests/*.test.mjs
```

`npm test` runs the same sequence; no npm installation is needed. Checks cover
48 original Python forward fixtures, both optical modes, full/zero correction,
axis/sign/zero equivalence, inverse recovery, bounded BEP conversion, invalid
inputs, native HTTP endpoints, UI wiring and the actual bundled WebAssembly
Python runtime. The DOM harness and Node runtime check are not visual browser QA.
A real-browser visual check was unavailable in this execution environment.

For GitHub Pages, follow `GITHUB_PAGES.md`; the included workflow builds and
publishes `dist/`. The browser runtime is bundled locally and makes the source
package about 14 MB before ZIP compression. Initial hosted loading downloads
this runtime; calculations then stay in the browser. Local/native requests stay
on the loopback server. The app does not persist user inputs after reload.
