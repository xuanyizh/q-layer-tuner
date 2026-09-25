# 2.1.0

- Add independent As/P measured-pair inputs and CSV/TSV/text loading.
- Add full degree-five fitting in the standard-library Python core using scaled
  Householder QR. Preserve original coefficients until a valid fit is applied.
- Use each accepted dataset's measured range in recipes and forward/inverse BEP
  conversion, with no extrapolation.
- Show measured/fitted curves, R², RMSE, relative residuals and a comparison table.
- Save/load applied calibration profiles as JSON, including manual coefficients.
- Keep calibrations when resetting recipe inputs; provide separate original As/P
  restoration controls. Calibrations otherwise last for the current session.
- Reject malformed profiles, unstable fits and nonpositive/nonmonotonic curves;
  discard stale asynchronous fit/conversion responses.
- Keep original PL/XRD physics and selectable optical strain correction unchanged.
