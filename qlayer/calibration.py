"""Measured BEP calibration: parsing and degree-five least squares, stdlib only."""
import json
import math
from pathlib import Path
import re

CALIBRATION = json.loads(Path(__file__).with_name('bep_calibration.json').read_text())
MAX_POINTS = 200


class InputError(ValueError):
    """A user input or requested conversion is outside the model."""


def require(condition, message):
    if not condition:
        raise InputError(message)


def finite(value):
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)


def poly_value(coefficients, x):
    value = 0.
    for c in reversed(coefficients):
        value = value*x+c
    return value


def poly_derivative(c):
    return [j*c[j] for j in range(1, len(c))]


def interval_roots(c, low, high):
    """Isolate real polynomial roots by splitting at derivative critical points."""
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


def measurements_checked(data):
    require(isinstance(data,list) and 6 <= len(data) <= MAX_POINTS,
            f'Enter 6–{MAX_POINTS} measured pairs for a fifth-degree fit.')
    rows = []
    for i, row in enumerate(data,1):
        require(isinstance(row,dict),f'Pair {i} must contain valve and bep_torr.')
        v,b = row.get('valve'),row.get('bep_torr')
        require(finite(v) and v >= 0,f'Pair {i}: valve must be a finite, nonnegative number.')
        require(finite(b) and b > 0,f'Pair {i}: BEP must be a finite, positive number.')
        rows.append(dict(valve=float(v),bep_torr=float(b)))
    rows.sort(key=lambda r:r['valve'])
    require(len({r['valve'] for r in rows}) >= 6,'A fifth-degree fit needs at least 6 distinct valve settings.')
    return rows


def parse_measurements(text, unit='torr'):
    require(unit in ('torr','microtorr'),'Choose Torr or 10⁻⁶ Torr for the measured BEP column.')
    require(isinstance(text,str) and len(text) <= 50000,'Enter up to 50,000 characters of measured pairs.')
    rows = []
    # Newlines or semicolons separate pairs. Comma, tab, whitespace or = separate columns.
    for i,line in enumerate(re.split(r'[\n;]',text.lstrip('\ufeff')),1):
        line = line.split('#',1)[0].strip()
        if not line:
            continue
        if not rows and re.match(r'^valve\b',line,re.I) and re.search(r'\bbep\b',line,re.I):
            continue
        columns = re.split(r'[\s,=]+',line)
        require(len(columns)==2,f'Row {i}: enter exactly two columns: valve and BEP.')
        try:
            valve,bep = map(float,columns)
        except ValueError:
            raise InputError(f'Row {i}: use numbers such as 30, 0.22e-6. Select the BEP units above.') from None
        rows.append(dict(valve=valve,bep_torr=bep*(1e-6 if unit=='microtorr' else 1)))
    return measurements_checked(rows)


def record_checked(source, record):
    require(source in ('As','P'),'Select As or P.')
    require(isinstance(record,dict),f'{source} calibration must be an object.')
    rows = measurements_checked(record.get('measurements'))
    c = record.get('raw_coefficients_ascending_microtorr')
    require(isinstance(c,list) and len(c)==6 and all(finite(v) for v in c),
            f'{source} calibration needs six finite polynomial coefficients, a0 through a5.')
    bounds = [rows[0]['valve'],rows[-1]['valve']]
    supplied = record.get('valid_valve_range',bounds)
    require(isinstance(supplied,list) and len(supplied)==2 and supplied==bounds,
            f'{source} valid range must match the minimum and maximum measured valves.')
    return dict(source=source,degree=5,valid_valve_range=bounds,
                raw_coefficients_ascending_microtorr=list(c),measurements=rows)


def get_record(source, profile=None):
    require(source in ('As','P'),'Select As or P.')
    if profile is None:
        return CALIBRATION['sources'][source]
    require(isinstance(profile,dict) and isinstance(profile.get('sources'),dict),'Calibration profile must contain sources.')
    require(source in profile['sources'],f'The calibration profile is missing {source}.')
    return record_checked(source,profile['sources'][source])


def curve_error(source, coefficients, low, high):
    derivative = poly_derivative(coefficients)
    candidates = [low,high]+interval_roots(poly_derivative(derivative),low,high)
    slopes = [poly_value(derivative,v) for v in candidates]
    ends = [poly_value(coefficients,v) for v in (low,high)]
    if not all(math.isfinite(v) for v in slopes+ends):
        return f'{source} curve exceeds the numerical range; check the values and units.'
    if min(slopes) <= 0:
        return f'{source} polynomial must increase throughout valve {low:g}–{high:g}. The fitted curve turns or has a nonpositive slope.'
    if min(ends) <= 0:
        return f'{source} polynomial must predict positive BEP throughout its measured range.'
    return None


def summarize(source, record, coefficients=None):
    r = record_checked(source,record)
    c = coefficients if coefficients is not None else r['raw_coefficients_ascending_microtorr']
    require(len(c)==6 and all(finite(v) for v in c),f'{source} coefficients must be finite numbers.')
    low,high = r['valid_valve_range']
    measured = [row['bep_torr'] for row in r['measurements']]
    fitted = [poly_value(c,row['valve'])*1e-6 for row in r['measurements']]
    residual = [f-m for f,m in zip(fitted,measured)]
    require(all(math.isfinite(v) for v in fitted+residual),'Polynomial values overflow; check the calibration values.')
    mean = math.fsum(measured)/len(measured)
    ssr = math.fsum(v*v for v in residual)
    sst = math.fsum((v-mean)**2 for v in measured)
    error = curve_error(source,c,low,high)
    return dict(source=source,range=[low,high],coefficients=c,pointCount=len(measured),
                uniqueCount=len({row['valve'] for row in r['measurements']}),
                rSquared=1-ssr/sst if sst>0 else None,
                rmse=math.sqrt(ssr/len(measured)),
                maxRelativePercent=max(abs(r/v)*100 for r,v in zip(residual,measured)),
                usable=error is None,validationError=error,
                measurements=[dict(valve=row['valve'],bep=row['bep_torr'],fitted=f,residual=e)
                              for row,f,e in zip(r['measurements'],fitted,residual)],
                curve=[dict(valve=low+(high-low)*j/100,bep=poly_value(c,low+(high-low)*j/100)*1e-6) for j in range(101)])


def least_squares_qr(a, b):
    """Householder QR on a scaled Vandermonde matrix (no normal equations)."""
    a,b = [list(row) for row in a],list(b)
    n,m = len(a),len(a[0])
    diagonal = []
    for k in range(m):
        v = [a[i][k] for i in range(k,n)]
        norm = math.hypot(*v)
        require(norm > 1e-10*math.sqrt(n),'Valve settings are too clustered for a stable fifth-degree fit; spread the measurements across the range.')
        v[0] += math.copysign(norm,v[0])
        length = math.hypot(*v)
        v = [x/length for x in v]
        for j in range(k,m):
            dot = 2*math.fsum(v[i-k]*a[i][j] for i in range(k,n))
            for i in range(k,n):
                a[i][j] -= dot*v[i-k]
        dot = 2*math.fsum(v[i-k]*b[i] for i in range(k,n))
        for i in range(k,n):
            b[i] -= dot*v[i-k]
        diagonal.append(abs(a[k][k]))
    require(min(diagonal)>max(diagonal)*1e-10,'Valve settings do not support a stable fifth-degree fit.')
    c = [0.]*m
    for i in range(m-1,-1,-1):
        c[i] = (b[i]-math.fsum(a[i][j]*c[j] for j in range(i+1,m)))/a[i][i]
    return c


def fit_calibration(source, text=None, unit='torr', measurements=None):
    require(source in ('As','P'),'Select As or P.')
    rows = measurements_checked(measurements) if measurements is not None else parse_measurements(text,unit)
    low,high = rows[0]['valve'],rows[-1]['valve']
    center,scale = (low+high)/2,(high-low)/2
    require(scale>max(abs(center),1)*1e-7,'The measured valve range is too narrow for a stable raw-power polynomial.')
    pressure_scale = max(r['bep_torr'] for r in rows)
    z = [(r['valve']-center)/scale for r in rows]
    normalized = least_squares_qr([[v**j for j in range(6)] for v in z],
                                  [r['bep_torr']/pressure_scale for r in rows])
    # Convert from z=(V-center)/scale to the existing a0..a5 microtorr convention.
    c = [math.fsum(normalized[k]*math.comb(k,j)*(-center/scale)**(k-j)/scale**j
                   for k in range(j,6))*pressure_scale*1e6 for j in range(6)]
    require(all(finite(v) for v in c),'Fit coefficients exceed the numerical range; check the values and units.')
    for j in range(101):
        valve=low+(high-low)*j/100
        expected=poly_value(normalized,(valve-center)/scale)*pressure_scale
        actual=poly_value(c,valve)*1e-6
        require(abs(expected-actual)<=pressure_scale*1e-7,
                'Raw-power coefficients lose precision for this valve range. Use more widely spaced measurements.')
    record = dict(source=source,degree=5,measurements=rows,valid_valve_range=[low,high],
                  raw_coefficients_ascending_microtorr=c)
    summary = summarize(source,record)
    warnings = []
    if len(rows)==6:
        warnings.append('Six points exactly determine six coefficients; residual agreement does not independently validate the curve.')
    return dict(record=record,summary=summary,usable=summary['usable'],warnings=warnings,
                method='Unweighted degree-five least squares; scaled valves and Householder QR')


def validate_profile(profile):
    require(isinstance(profile,dict) and type(profile.get('schema_version')) is int and profile.get('schema_version') in (1,2),'Unsupported calibration file schema.')
    require(isinstance(profile.get('sources'),dict) and set(profile['sources'])=={'As','P'},'Calibration files must contain both As and P sources.')
    require(profile.get('bep_units','Torr')=='Torr','Saved calibration pressures must use Torr.')
    sources,summaries = {},{}
    for source in ('As','P'):
        record=get_record(source,profile)
        summary=summarize(source,record)
        require(summary['usable'],summary['validationError'] or 'Invalid calibration.')
        sources[source],summaries[source]=record,summary
    return dict(profile=dict(schema_version=2,bep_units='Torr',sources=sources),summaries=summaries)
