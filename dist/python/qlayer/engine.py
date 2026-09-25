"""InGaAsP recipe inference and measured As/P BEP calibrations.

Standard library only. No source hardware is controlled. Optical strain can be
disabled independently of the coherent elastic correction in the XRD model.
"""
import json
import math
from pathlib import Path

VERSION = "2.0.0"
HC = 1239.8419843320026
RAD = math.pi / 648000
ROOT = Path(__file__).resolve().parent
PARAMETERS = json.loads((ROOT / "parameters.json").read_text())
CALIBRATION = json.loads((ROOT / "bep_calibration.json").read_text())
DEFAULTS = dict(
    inRatio=.8, gaRatio=.2, targetPL=1197., targetRate=1., measuredPL=1190.,
    mismatch=40., knownElement="In", knownRate=.8, inTemp=999.7, gaTemp=1000.,
    asValve=100., pValve=None, inA=8.5435, inB=10785., gaA=9.727, gaB=13248.,
    asExponent=1., inStep=100., gaStep=100., asStep=100., axis="theta",
    sign="film_minus_substrate", zero=0., plTemp=300., xrdTemp=300.,
    xray=1.54056, sigmaPL=1., sigmaXRD=10., opticalStrain="off",
)
for _element in ("As", "P"):
    for _j, _value in enumerate(CALIBRATION["sources"][_element]["raw_coefficients_ascending_microtorr"]):
        DEFAULTS[f"{_element.lower()}C{_j}"] = _value


class InputError(ValueError):
    """A user input or requested conversion is outside the model."""


def require(condition, message):
    if not condition:
        raise InputError(message)


def finite(value):
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)


def settings_with_defaults(settings=None):
    require(settings is None or isinstance(settings, dict), "Settings must be an object.")
    settings = settings or {}
    require(not set(settings) - set(DEFAULTS), "Unsupported recipe input(s): " + ", ".join(sorted(set(settings) - set(DEFAULTS))))
    return {**DEFAULTS, **settings}


def validate(s):
    for key, value in DEFAULTS.items():
        if isinstance(value, (int, float)):
            require(finite(s[key]), f"Enter a finite number for {key}.")
    require(s["inRatio"] > 0 and s["gaRatio"] > 0, "Both target In and Ga ratio weights must be positive.")
    require(s["targetRate"] > 0 and s["knownRate"] > 0, "Target and known incorporation rates must be positive.")
    require(s["knownElement"] in ("In", "Ga"), "Select In or Ga as the known rate.")
    for key in ("targetPL", "measuredPL"):
        require(650 <= s[key] <= 2200, "PL wavelengths must be between 650 and 2200 nm.")
    for key in ("plTemp", "xrdTemp"):
        require(250 <= s[key] <= 350, "Measurement temperatures must be between 250 and 350 K.")
    for key in ("inTemp", "gaTemp"):
        require(0 < s[key] < 2000, "Source temperatures must be between 0 and 2000 °C.")
    require(s["inB"] > 0 and s["gaB"] > 0, "Source B coefficients must be positive.")
    require(s["asExponent"] > 0, "The As response exponent must be positive.")
    for key in ("inStep", "gaStep", "asStep"):
        require(0 <= s[key] <= 100, "Applied correction percentages must be between 0 and 100.")
    require(abs(s["mismatch"]) <= 10000 and abs(s["zero"]) <= 1000, "Check the XRD separation or zero offset.")
    require(s["axis"] in ("theta", "two_theta"), "Select θ/ω or 2θ for the XRD axis.")
    require(s["sign"] in ("film_minus_substrate", "substrate_minus_film"), "Select a valid XRD sign convention.")
    require(s["opticalStrain"] in ("off", "on"), "Select whether to include strain in the bandgap.")
    require(.3 <= s["xray"] <= 2.5, "X-ray wavelength must be between 0.3 and 2.5 Å.")
    require(s["sigmaPL"] > 0 and s["sigmaXRD"] > 0, "Measurement uncertainties must be positive.")
    require(s["pValve"] is None or finite(s["pValve"]), "P valve must be a number or blank.")


def lattice(binary, temperature):
    return binary["a300_A"] + binary["da_dT_A_K"] * (temperature - 300)


def binary_gap(binary, temperature):
    if binary["temperature_model"] == "bose_einstein":
        return binary["Eg0_eV"] + binary["bose_amplitude_eV"] * (1 - 1 / math.tanh(binary["bose_temperature_K"] / temperature))
    return binary["Eg0_eV"] - binary["varshni_alpha_eV_K"] * temperature**2 / (temperature + binary["varshni_beta_K"])


def material(x, y, temperature, parameters=None):
    p = parameters or PARAMETERS
    weights = dict(GaAs=x*y, GaP=x*(1-y), InAs=(1-x)*y, InP=(1-x)*(1-y))
    m = {key: sum(w * p["binaries"][b][key] for b, w in weights.items())
         for key in ("C11_GPa", "C12_GPa", "ac_eV", "av_eV", "b_eV", "delta_so_eV")}
    m["a0"] = sum(w * lattice(p["binaries"][b], temperature) for b, w in weights.items())
    m["as"] = lattice(p["binaries"]["InP"], temperature)
    m["parallel"] = m["as"] / m["a0"] - 1
    m["zz"] = -2 * m["C12_GPa"] / m["C11_GPa"] * m["parallel"]
    m["aperp"] = m["a0"] * (1 + m["zz"])
    m["weights"] = weights
    return m


def forward(x, y, settings=None, parameters=None, offset=0.):
    s = settings_with_defaults(settings)
    p = parameters or PARAMETERS
    m = material(x, y, s["plTemp"], p)
    mx = material(x, y, s["xrdTemp"], p)
    terms = (1, x, y, x*x, y*y, x*y, x*x*y, x*y*y)
    gap = sum(c*t for c, t in zip(p["gap_polynomials_300K"]["InGaAsP"], terms))
    gap += sum(w * (binary_gap(p["binaries"][b], s["plTemp"]) - binary_gap(p["binaries"][b], 300)) for b, w in m["weights"].items())
    trace = 2*m["parallel"] + m["zz"]
    hydro = m["av_eV"] * trace
    q = m["b_eV"] * (m["zz"] - m["parallel"])
    d = m["delta_so_eV"]
    hh = hydro-q
    lh = hydro + (q-d+math.sqrt(d*d+2*d*q+9*q*q))/2
    strain_shift = m["ac_eV"] * trace - max(hh, lh)
    edge = gap + (strain_shift if s["opticalStrain"] == "on" else 0.)
    # XRD ALWAYS includes coherent elastic strain, regardless of optical mode.
    theta_s = math.asin(2*s["xray"]/mx["as"])
    theta_f = math.asin(2*s["xray"]/mx["aperp"])
    mismatch = (theta_f-theta_s)/RAD * (2 if s["axis"] == "two_theta" else 1)
    if s["sign"] == "substrate_minus_film":
        mismatch = -mismatch
    energy = edge+offset
    return dict(x=x, y=y, In=1-x, Ga=x, As=y, P=1-y, edge=edge, bulkGap=gap,
                opticalStrainShift=strain_shift, opticalStrainApplied=s["opticalStrain"] == "on",
                energy=energy, pl=HC/energy if energy > 0 else -1,
                mismatch=mismatch+s["zero"], aperp=mx["aperp"], a0=mx["a0"],
                parallel=m["parallel"], parallelXRD=mx["parallel"], split=abs(hh-lh))


def target_composition(s, p):
    x = s["gaRatio"] / (s["inRatio"]+s["gaRatio"])
    a = lambda b: lattice(p["binaries"][b], s["xrdTemp"])
    no_as = x*a("GaP")+(1-x)*a("InP")
    all_as = x*a("GaAs")+(1-x)*a("InAs")
    y = (a("InP")-no_as)/(all_as-no_as)
    require(0 <= y <= 1, "This In/Ga ratio cannot be lattice matched to InP with an As/P alloy.")
    return x, y


def infer(s, p, offset):
    theta_s = math.asin(2*s["xray"]/lattice(p["binaries"]["InP"], s["xrdTemp"]))
    dt = (s["mismatch"]-s["zero"])/(2 if s["axis"] == "two_theta" else 1)
    if s["sign"] == "substrate_minus_film":
        dt = -dt
    theta_f = theta_s+dt*RAD
    require(0 < theta_f < math.pi/2, "XRD input does not give a physical Bragg angle.")
    aperp = 2*s["xray"]/math.sin(theta_f)
    energy = HC/s["measuredPL"]
    def residual(x, y):
        f = forward(x, y, s, p, offset)
        return [(f["energy"]-energy)/.01, (f["aperp"]-aperp)/.001]
    norm = lambda r: r[0]**2+r[1]**2
    roots = []
    for x0 in (.03, .25, .5, .75, .97):
        for y0 in (.03, .25, .5, .75, .97):
            x, y = x0, y0
            for _ in range(75):
                r = residual(x, y)
                if norm(r) < 1e-18:
                    break
                h = 1e-5
                xp, xm, yp, ym = min(1, x+h), max(0, x-h), min(1, y+h), max(0, y-h)
                rxp, rxm, ryp, rym = residual(xp,y), residual(xm,y), residual(x,yp), residual(x,ym)
                a, c = [(rxp[j]-rxm[j])/(xp-xm) for j in (0,1)]
                b, d = [(ryp[j]-rym[j])/(yp-ym) for j in (0,1)]
                det = a*d-b*c
                if not math.isfinite(det) or abs(det) < 1e-14:
                    break
                dx, dy = (-d*r[0]+b*r[1])/det, (c*r[0]-a*r[1])/det
                scale = 1.
                accepted = False
                while scale > 1e-7:
                    xn, yn = min(1,max(0,x+scale*dx)), min(1,max(0,y+scale*dy))
                    if norm(residual(xn,yn)) < norm(r):
                        x,y,accepted = xn,yn,True
                        break
                    scale *= .5
                if not accepted:
                    break
            f = forward(x,y,s,p,offset)
            if (abs(f["pl"]-s["measuredPL"]) < 1e-4 and abs(f["mismatch"]-s["mismatch"]) < 1e-3
                and abs(f["parallel"]) < .02 and abs(f["parallelXRD"]) < .02
                and not any(math.hypot(o["x"]-x,o["y"]-y)<1e-5 for o in roots)):
                roots.append(f)
    return roots


def corrected_temperature(old_c, slope_b, ratio):
    require(finite(ratio) and ratio > 0, "Requested source rate is not positive and finite.")
    inv = 1/(old_c+273.15)-math.log10(ratio)/slope_b
    require(inv > 0, "Requested source rate lies outside temperature calibration.")
    value = 1/inv-273.15
    require(math.isfinite(value) and 0 < value < 2000, "Requested source temperature is outside 0–2000 °C.")
    return value


def poly_value(coefficients, x):
    value = 0.
    for c in reversed(coefficients):
        value = value*x+c
    return value


def poly_derivative(c):
    return [j*c[j] for j in range(1, len(c))]


def interval_roots(c, low, high):
    """Isolate real polynomial roots using derivative critical points."""
    c = list(c)
    while len(c) > 1 and c[-1] == 0:
        c.pop()
    if len(c) <= 1:
        return []
    if len(c) == 2:
        root = -c[0]/c[1]
        return [root] if low < root < high else []
    cuts = [low] + interval_roots(poly_derivative(c), low, high) + [high]
    roots = []
    for v in cuts[1:-1]:
        if abs(poly_value(c,v)) < 1e-12:
            roots.append(v)
    for a,b in zip(cuts,cuts[1:]):
        fa,fb = poly_value(c,a),poly_value(c,b)
        if fa*fb < 0:
            for _ in range(65):
                mid = (a+b)/2
                fm = poly_value(c,mid)
                if fa*fm <= 0:
                    b,fb = mid,fm
                else:
                    a,fa = mid,fm
            roots.append((a+b)/2)
    return sorted(set(roots))


def source_curve(source, settings=None):
    require(source in ("As", "P"), "Select As or P.")
    s = settings_with_defaults(settings)
    c = [s[f"{source.lower()}C{j}"] for j in range(6)]
    require(all(finite(v) for v in c), f"{source} coefficients must be finite numbers.")
    low,high = CALIBRATION["sources"][source]["valid_valve_range"]
    derivative = poly_derivative(c)
    candidates = [low,high]+interval_roots(poly_derivative(derivative),low,high)
    require(min(poly_value(derivative,v) for v in candidates) > 0,
            f"{source} polynomial must increase throughout valve {low:g}–{high:g}.")
    require(poly_value(c,low) > 0, f"{source} polynomial must predict positive BEP throughout its range.")
    return c,low,high


def bep_from_valve(source, valve, settings=None):
    c,low,high = source_curve(source,settings)
    require(finite(valve) and low <= valve <= high, f"{source} valve must be within measured range {low:g}–{high:g}; extrapolation is disabled.")
    return poly_value(c,valve)*1e-6


def valve_from_bep(source, bep_torr, settings=None):
    c,low,high = source_curve(source,settings)
    bmin,bmax = poly_value(c,low)*1e-6,poly_value(c,high)*1e-6
    require(finite(bep_torr) and bmin <= bep_torr <= bmax,
            f"Requested {source} BEP is outside the fitted range {bmin:.6g}–{bmax:.6g} Torr; no extrapolation.")
    for _ in range(70):
        mid = (low+high)/2
        if poly_value(c,mid)*1e-6 < bep_torr:
            low = mid
        else:
            high = mid
    return (low+high)/2


def calibration_summary(source, settings=None):
    c,low,high = source_curve(source,settings)
    data = CALIBRATION["sources"][source]["measurements"]
    measured = [r["bep_torr"] for r in data]
    fitted = [poly_value(c,r["valve"])*1e-6 for r in data]
    residual = [a-b for a,b in zip(fitted,measured)]
    mean = sum(measured)/len(measured)
    return dict(source=source, range=[low,high], coefficients=c,
                rSquared=1-sum(r*r for r in residual)/sum((v-mean)**2 for v in measured),
                rmse=math.sqrt(sum(r*r for r in residual)/len(residual)),
                maxRelativePercent=max(abs(r/v)*100 for r,v in zip(residual,measured)),
                measurements=[dict(valve=r["valve"],bep=r["bep_torr"]) for r in data],
                curve=[dict(valve=low+(high-low)*j/80,bep=poly_value(c,low+(high-low)*j/80)*1e-6) for j in range(81)])


def uncertainty(current,s,p,offset):
    x,y = current["x"],current["y"]
    if min(x,y,1-x,1-y) < 1e-5:
        return None
    h = 1e-6
    xp,xm,yp,ym = forward(x+h,y,s,p,offset),forward(x-h,y,s,p,offset),forward(x,y+h,s,p,offset),forward(x,y-h,s,p,offset)
    a,b = (xp["pl"]-xm["pl"])/(2*h),(yp["pl"]-ym["pl"])/(2*h)
    c,d = (xp["mismatch"]-xm["mismatch"])/(2*h),(yp["mismatch"]-ym["mismatch"])/(2*h)
    det = a*d-b*c
    if abs(det)<1e-10:
        return None
    return dict(ga=math.hypot(d*s["sigmaPL"],b*s["sigmaXRD"])/abs(det),
                **{"as": math.hypot(c*s["sigmaPL"],a*s["sigmaXRD"])/abs(det)})


def calculate(settings=None, parameters=None):
    s = settings_with_defaults(settings)
    validate(s)
    p = parameters or PARAMETERS
    tx,ty = target_composition(s,p)
    raw_target = forward(tx,ty,s,p)
    # Re-anchor separately in each optical mode. Never add kBT/2 again.
    offset = HC/s["targetPL"]-raw_target["edge"]
    target = forward(tx,ty,s,p,offset)
    roots = infer(s,p,offset)
    require(len(roots)>0, "No coherent bulk composition reproduces both PL and XRD. Check the axis, sign, reference, or film relaxation/confinement.")
    require(len(roots)==1, "Multiple compositions reproduce PL and XRD; an independent composition constraint is required.")
    current = roots[0]
    fraction = current[s["knownElement"]]
    require(fraction>1e-6, "Known-element fraction is too small to establish the rate scale.")
    total = s["knownRate"]/fraction
    rates = {n:dict(current=current[n]*total,target=target[n]*s["targetRate"]) for n in ("In","Ga")}
    partial = lambda old,new,step: old+(new-old)*step/100
    settings_result = {}
    for n,prefix in (("In","in"),("Ga","ga")):
        full = corrected_temperature(s[prefix+"Temp"],s[prefix+"B"],rates[n]["target"]/rates[n]["current"])
        settings_result[n] = dict(current=s[prefix+"Temp"],full=full,applied=partial(s[prefix+"Temp"],full,s[prefix+"Step"]))
    as_full = as_error = as_ratio = None
    bep = {"As":{},"P":{}}
    try:
        current_bep = bep_from_valve("As",s["asValve"],s)
        bep["As"]["current"] = current_bep
        require(current["y"]>1e-6 and target["y"]>1e-6,"As correction is undefined at zero As composition.")
        as_ratio = (target["y"]*s["targetRate"]/(current["y"]*total))**(1/s["asExponent"])
        target_bep = current_bep*as_ratio
        bep["As"]["fullRequested"] = target_bep
        as_full = valve_from_bep("As",target_bep,s)
        applied = partial(s["asValve"],as_full,s["asStep"])
        settings_result["As"] = dict(current=s["asValve"],full=as_full,applied=applied)
        bep["As"]["applied"] = bep_from_valve("As",applied,s)
    except InputError as error:
        as_error = str(error)
    if s["pValve"] is not None:
        try:
            pbep = bep_from_valve("P",s["pValve"],s)
            bep["P"] = dict(valve=s["pValve"],current=pbep,full=pbep,applied=pbep,heldFixed=True)
        except InputError as error:
            bep["P"] = dict(error=str(error))
    else:
        bep["P"] = dict(valve=None,current=None,heldFixed=True)
    def predict(ti,tg,valve):
        rin = rates["In"]["current"]*10**(s["inB"]*(1/(s["inTemp"]+273.15)-1/(ti+273.15)))
        rga = rates["Ga"]["current"]*10**(s["gaB"]*(1/(s["gaTemp"]+273.15)-1/(tg+273.15)))
        rate = rin+rga
        y = current["y"]*total/rate*(bep_from_valve("As",valve,s)/bep["As"]["current"])**s["asExponent"]
        if not math.isfinite(y) or not 0<=y<=1:
            return None
        f = forward(rga/rate,y,s,p,offset)
        if abs(f["parallel"])>.02 or abs(f["parallelXRD"])>.02 or f["energy"]<=0:
            return None
        return {**f,"rate":rate}
    prediction = None
    trajectory = []
    if as_full is not None:
        prediction = predict(settings_result["In"]["applied"],settings_result["Ga"]["applied"],settings_result["As"]["applied"])
        for j in range(25):
            t = j/24
            f = predict(s["inTemp"]+t*(settings_result["In"]["full"]-s["inTemp"]),
                        s["gaTemp"]+t*(settings_result["Ga"]["full"]-s["gaTemp"]),s["asValve"]+t*(as_full-s["asValve"]))
            if f:
                trajectory.append(f)
    notices = []
    if s["opticalStrain"]=="on" and current["split"]<.005:
        notices.append("HH/LH edges are close; treating PL as a single band edge can be less reliable.")
    if abs(current["parallel"])>.005:
        notices.append("Inferred strain exceeds 0.5%; verify coherence before using this correction.")
    if abs(offset)>.1:
        notices.append("PL reference requires an offset above 100 meV; check the reference composition and bulk-film assumption.")
    if max(abs(settings_result[n]["full"]-settings_result[n]["current"]) for n in ("In","Ga"))>10:
        notices.append("A full group-III correction exceeds 10 °C; verify calibration validity over this change.")
    if as_full is not None and not prediction:
        notices.append("Selected partial steps predict a composition outside this model; no applied prediction is shown.")
    if prediction and abs(prediction["pl"]-s["targetPL"])>abs(current["pl"]-s["targetPL"])+.01:
        notices.append("Selected partial steps predict PL farther from its reference; review the independent step percentages.")
    if bep["P"].get("error"):
        notices.append(bep["P"]["error"])
    summaries = {}
    for source in ("As","P"):
        try:
            summaries[source] = calibration_summary(source,s)
        except InputError as error:
            summaries[source] = dict(error=str(error))
    return dict(version=VERSION,inputs=s,target=target,current=current,offset=offset,total=total,
                rates=rates,settings=settings_result,asError=as_error,asFluxRatio=as_ratio,
                prediction=prediction,trajectory=trajectory,uncertainty=uncertainty(current,s,p,offset),
                notices=notices,bep=bep,calibrations=summaries,
                nominalRates={"In":10**(s["inA"]-s["inB"]/(s["inTemp"]+273.15)),
                              "Ga":10**(s["gaA"]-s["gaB"]/(s["gaTemp"]+273.15))})


def dispatch(payload):
    require(isinstance(payload,dict),"Request must be an object.")
    action = payload.get("action","calculate")
    if action == "metadata":
        return dict(version=VERSION,defaults=DEFAULTS,calibration=CALIBRATION)
    if action == "calculate":
        return calculate(payload.get("settings"))
    if action == "convert_bep":
        source = payload.get("source")
        s = settings_with_defaults(payload.get("settings"))
        if payload.get("direction") == "valve_to_bep":
            v = payload.get("value")
            return dict(source=source,valve=v,bepTorr=bep_from_valve(source,v,s))
        require(payload.get("direction")=="bep_to_valve","Choose valve-to-BEP or BEP-to-valve.")
        b = payload.get("value")
        return dict(source=source,bepTorr=b,valve=valve_from_bep(source,b,s))
    raise InputError("Unknown calculation action.")
