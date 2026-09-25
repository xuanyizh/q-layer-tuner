# Q Layer Tuner 2.1 — measured calibration fitting

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

## Enter new As or P calibration data

1. Open the **Calibration** tab and find **As & P valve calibrations**.
2. In the As or P section, paste measured pairs into the box, or load a CSV,
   TSV or text file. Select the BEP column units before fitting.
3. Click **Fit & use As curve** or **Fit & use P curve**. The Python core fits
   all powers 5, 4, 3, 2, 1 and 0 by unweighted least squares.
4. Review the plotted points/curve, R², RMSE and residual table. A successful
   fit updates the coefficients, measured valve range, converter and recipe.
5. Click **Save calibrations JSON** to keep both active curves. After reloading,
   use **Load saved calibrations JSON** to restore them.

Example with **Torr** selected (your original As data):

```text
Valve, BEP
30, 0.22e-6
60, 0.514e-6
90, 0.893e-6
120, 1.35e-6
150, 1.77e-6
180, 2.32e-6
210, 2.87e-6
240, 3.52e-6
270, 4.66e-6
```

With **10⁻⁶ Torr** selected, enter `30, 0.22`, `60, 0.514`, etc. Do not also
include `e-6` in that mode. Two-column paste from Excel uses tabs and is accepted.
Comma, whitespace or `=` can separate the two columns. Newlines or semicolons
separate pairs. An optional first header containing Valve and BEP is accepted.
Use a decimal point, not a decimal comma. Comment text after `#` is ignored.

Provide 6–200 rows with at least 6 distinct, nonnegative valve settings and
positive pressures. Repeated valve settings count as separate, equally weighted
measurements. Six points give no residual degrees of freedom: a perfect fit then
is not independent evidence of calibration accuracy.

Draft edits do not change active calculations until Fit & use succeeds. Curves
that turn downward, predict nonpositive BEP, or cannot be fitted stably are not
applied. A mathematically fitted but unusable curve can still be inspected; the
previous active calibration is retained. The valid range is the smallest to
largest measured valve for each active source; extrapolation remains disabled.

Calibration changes are **session-only** until you download the JSON file.
That file contains both sources' applied coefficients and measurements, including
manual coefficient changes. Unfitted draft text is not saved. No calibration is
written into your GitHub repository or onto the local server automatically.
**Reset recipe** preserves the active calibration; each **Restore original**
button restores that source's built-in data, coefficients and range.

## What changed from v2.0

- Added raw As/P pair entry, text/CSV/TSV loading, Python degree-five refitting,
  diagnostics, JSON save/load and independent restoration of each source.
- Calibration ranges and plotted reference data now follow the active dataset.
- Existing composition inference, optical strain switch, source-temperature
  correction and provisional As incorporation model are unchanged.
- The same Python core serves the local launcher and the bundled browser runtime.

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

Built-in ranges: **As 30–270**, **P 5–80**. New fits use their own measured ranges. Extrapolation is disabled. Edited curves
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

## Fit and use a calibration from Python

```python
import copy
import json
from qlayer import calculate, fit_calibration, validate_profile
from qlayer.engine import CALIBRATION

profile = copy.deepcopy(CALIBRATION)
with open("new_as_measurements.txt") as handle:
    fit = fit_calibration("As", text=handle.read(), unit="torr")
if not fit["usable"]:
    raise ValueError(fit["summary"]["validationError"])
profile["sources"]["As"] = fit["record"]
profile = validate_profile(profile)["profile"]
result = calculate({"asValve": 100}, calibrations=profile)
with open("my_calibrations.json", "w") as handle:
    json.dump(profile, handle, indent=2)
```

The `calibrations=` profile supplies coefficients and measured ranges. Explicit
`asC0`…`asC5` / `pC0`…`pC5` values in `settings` override the profile's coefficients,
so omit those settings when you want to use the fitted coefficients directly.

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
calibrations in the canonical files. Recipe inputs reset on reload. Calibration edits can be saved/loaded as JSON.

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
Python runtime, including refitting, JSON restoration and asynchronous UI changes. The DOM harness and Node runtime check are not visual browser QA.
The browser environment blocked access to the local preview, so visual browser QA
was unavailable; DOM interaction tests and the actual browser Python runtime passed.

For GitHub Pages, follow `GITHUB_PAGES.md`; the included workflow builds and
publishes `dist/`. The browser runtime is bundled locally and makes the source
package about 14 MB before ZIP compression. Initial hosted loading downloads
this runtime; calculations then stay in the browser. Local/native requests stay
on the loopback server. The app does not persist user inputs after reload.
