# Model notes

Composition notation: In_(1−x)Ga_x As_y P_(1−y). The target x comes from the
normalized requested Ga share, and target y solves a0(x,y,T_XRD) = a_InP(T_XRD)
using the original binary lattice parameters and Vegard interpolation.

## Coherent lattice and XRD — active in both optical modes

For a (001) coherent layer:

- epsilon_parallel = a_InP / a0 − 1
- epsilon_zz = −2 (C12/C11) epsilon_parallel
- a_perp = a0 (1 + epsilon_zz)
- theta_004 = asin(2 lambda_Xray / a_perp)

The elastic constants are composition-interpolated. The measured separation
uses the chosen theta/omega or 2theta axis, sign, and angular zero. Turning off
optical strain does not replace a_perp with the relaxed lattice constant a0.

## Optical model and reference

The bulk gap polynomial and temperature dependence are preserved from the
supplied composition model. Off mode uses that bulk gap. On mode adds the
conduction hydrostatic shift and subtracts the higher valence-band edge,
including HH/LH mixing:

- trace = 2 epsilon_parallel + epsilon_zz
- Q = b (epsilon_zz − epsilon_parallel)
- E_HH = a_v trace − Q
- E_LH = a_v trace + (Q − Delta_so + sqrt(Delta_so² + 2 Delta_so Q + 9 Q²))/2
- optical shift = a_c trace − max(E_HH, E_LH)

PL and XRD temperatures can differ. For each selected optical mode, the model
is anchored at the target composition by

`offset = hc / target_PL − E_model(target)`.

The same constant energy offset is then applied to the grown layer. No separate
kBT/2 term is added. Simultaneous PL and coherent-XRD inversion uses 25 bounded,
damped Newton starts and forward residual checks. Zero or multiple distinct
solutions stop recipe recommendations. This finite search is not a uniqueness
proof. A reference offset does not validate composition slopes.

## Rate and source corrections

The independently known incorporated In or Ga rate sets total current rate:
`R_current = known_rate / inferred_known_fraction`.
Target partial rates are the target fractions multiplied by target total rate.
The cell model is `log10 R = A − B/T_K`, re-anchored at the measured/inferred
current partial rate. Therefore

`1/T_new,K = 1/T_old,K − log10(R_target/R_current)/B`.

The A coefficient cancels from the correction. Its unanchored rate is displayed
for context only. The original photographed Ga example 0.1913 → 0.2000 and
1014.9 °C gives 1017.323409 °C at B = 13248 K.

For As, the existing provisional local incorporation response gives

`BEP_new/BEP_current = [(y_target R_target)/(y_current R_current)]^(1/n)`.

The measured fifth-degree BEP polynomial is inverted by bisection within
the active measured valve range (originally As 30–270). Each partial step interpolates the physical valve or temperature.
The applied prediction recomputes rates and composition using those actual
settings. P stays fixed; the active P fit (originally valve 5–80) supports reporting and a separate
forward/inverse converter. It is not used to infer a new incorporation law.

## Data and limitations

`qlayer/parameters.json` preserves the supplied composition app's material
profile. `tests/reference-fixtures.json` retains 48 outputs and the original
Python model's SHA-256. Literature basis recorded in that profile includes:

- Minch et al. (1999): https://doi.org/10.1109/3.760325
- Vurgaftman et al. (2001): https://doi.org/10.1063/1.1368156

The As/P fits are ordinary, unweighted degree-five least squares fits to the
user's measured pairs. Full data, coefficients and fit diagnostics remain in
`qlayer/bep_calibration.json`. Their response depends on the measurement/gauge
and source conditions; BEP alone is not an incorporated composition.

Scope: coherent bulk-like direct-Gamma emission, measurement temperatures
250–350 K, no partial relaxation or confinement. Current PL/XRD uncertainty is
propagated by a local Jacobian; reference, source, BEP-fit and material-model
uncertainties are excluded. Exact source limits and settling times are not
modeled. This is not a reproduction of the lab's proprietary Q CAL algorithm.

## User refitting in v2.1

`qlayer/calibration.py` implements unweighted degree-five least squares with
all six powers. Valve values are mapped to [-1, 1]; pressures are scaled by their
maximum. Householder QR solves the Vandermonde least-squares problem without
forming normal equations. The normalized polynomial is transformed back to the
existing ascending a0…a5 coefficient convention in microtorr. A grid comparison
checks that the raw-power representation retains numerical precision. This
implementation uses only the Python standard library, including in Pyodide.

A profile records both sources' raw measurements, coefficients and measured
ranges. The server/worker receives the active profile with each request; there
is no mutable process-global user calibration. A file load validates both
sources before the UI replaces either one. Fit failures retain the active
calibration. Editing a draft during fitting prevents that stale fit being applied.

Only finite positive pressures and nonnegative finite valve values are accepted.
At least six distinct valve values are required. Duplicate valves are repeated,
equally weighted measurements. Curves must be positive and have positive slope
throughout the measured range, checked at endpoints and derivative extrema.
Range endpoints must equal the minimum and maximum recorded measurements.
No extrapolation or automatic lower-order fallback is performed.

R², RMS residual and maximum relative residual summarize agreement with the
measurements, not predictive uncertainty. Six rows leave zero residual degrees
of freedom. A high R² does not prove reproducibility or validate incorporation.
The fitting controls do not alter the provisional relation between BEP and
incorporated As, and P remains fixed in recipe corrections.
