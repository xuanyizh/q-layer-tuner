"""Numerical and state boundaries for user-supplied BEP calibration data."""
from copy import deepcopy
import json
import math
import unittest
from qlayer.calibration import (CALIBRATION, InputError, fit_calibration,
                               parse_measurements, validate_profile, poly_value)
from qlayer.engine import calculate, bep_from_valve, valve_from_bep, dispatch


def linear_rows(lo=40, hi=220, intercept=.25, slope=.012, n=10):
    return [dict(valve=v,bep_torr=(intercept+slope*v)*1e-6)
            for v in (lo+(hi-lo)*i/(n-1) for i in range(n))]


class CalibrationTests(unittest.TestCase):
    def test_original_measurements_reproduce_existing_fits(self):
        for source in ('As','P'):
            old=CALIBRATION['sources'][source]
            r=fit_calibration(source,measurements=old['measurements'])
            self.assertTrue(r['usable'])
            for a,b in zip(old['raw_coefficients_ascending_microtorr'],r['record']['raw_coefficients_ascending_microtorr']):
                self.assertAlmostEqual(a,b,delta=max(abs(a)*1e-10,1e-12))
            self.assertLess(r['summary']['maxRelativePercent'],4)

    def test_exact_fifth_degree_recovery(self):
        c=[.3,.01,2e-5,-4e-8,6e-11,1e-13]
        rows=[dict(valve=v,bep_torr=poly_value(c,v)*1e-6) for v in range(10,301,20)]
        fit=fit_calibration('As',measurements=rows)
        self.assertTrue(fit['usable'])
        for v in (10,73,180,300):
            self.assertAlmostEqual(poly_value(fit['record']['raw_coefficients_ascending_microtorr'],v),poly_value(c,v),delta=1e-11)

    def test_units_and_supported_paste_formats(self):
        comma='Valve,BEP (Torr)\n'+'\n'.join(f'{v}, {v*.01+1:.6f}e-6' for v in range(10,71,10))
        micro='; '.join(f'{v}={v*.01+1:.6f}' for v in range(10,71,10))
        a=fit_calibration('P',comma,'torr')
        b=fit_calibration('P',micro,'microtorr')
        tab='\n'.join(f'{v}\t{v*.01+1:.6f}e-6' for v in range(10,71,10))
        self.assertEqual(parse_measurements(comma),parse_measurements(tab))
        for x,y in zip(a['record']['raw_coefficients_ascending_microtorr'],b['record']['raw_coefficients_ascending_microtorr']):
            self.assertAlmostEqual(x,y,delta=1e-12)

    def test_new_ranges_used_by_recipe_and_both_converters(self):
        profile=deepcopy(CALIBRATION)
        profile['sources']['As']=fit_calibration('As',measurements=linear_rows())['record']
        profile['sources']['P']=fit_calibration('P',measurements=linear_rows(10,90))['record']
        result=calculate({'pValve':85},calibrations=profile)
        self.assertIsNone(result['asError'])
        # Analytical inverse of BEP=.25+.012*V gives an independent recipe expectation.
        expected=(result['asFluxRatio']*(.25+.012*100)-.25)/.012
        self.assertAlmostEqual(result['settings']['As']['full'],expected,places=8)
        self.assertAlmostEqual(result['prediction']['pl'],1197,places=7)
        self.assertEqual(result['calibrations']['As']['range'],[40,220])
        self.assertNotIn('error',result['bep']['P'])
        self.assertAlmostEqual(bep_from_valve('P',85,calibrations=profile),( .25+.012*85)*1e-6,places=15)
        self.assertAlmostEqual(valve_from_bep('P',( .25+.012*85)*1e-6,calibrations=profile),85,places=8)
        with self.assertRaisesRegex(InputError,'40–220'):
            bep_from_valve('As',30,calibrations=profile)

    def test_invalid_or_nonmonotonic_data_does_not_mutate_defaults(self):
        original=json.dumps(CALIBRATION,sort_keys=True)
        for text in ('', '1 2\n2 3', '1 nope', '1 2 3', '1 NaN', '1 -2', '-1 2'):
            with self.assertRaises(InputError): fit_calibration('As',text)
        with self.assertRaisesRegex(InputError,'distinct'):
            fit_calibration('As',measurements=[dict(valve=1,bep_torr=1e-6)]*7)
        rows=[dict(valve=v,bep_torr=(100-v)*1e-6) for v in range(10,71,10)]
        r=fit_calibration('As',measurements=rows)
        self.assertFalse(r['usable'])
        self.assertIn('increase throughout',r['summary']['validationError'])
        profile=deepcopy(CALIBRATION);profile['sources']['As']=r['record']
        with self.assertRaises(InputError): validate_profile(profile)
        self.assertEqual(json.dumps(CALIBRATION,sort_keys=True),original)

    def test_json_round_trip_and_tampered_range(self):
        p=deepcopy(CALIBRATION)
        p['sources']['As']=fit_calibration('As',measurements=linear_rows())['record']
        saved=validate_profile(p)['profile']
        restored=validate_profile(json.loads(json.dumps(saved)))['profile']
        self.assertEqual(saved,restored)
        self.assertEqual(calculate(calibrations=saved)['settings'],calculate(calibrations=restored)['settings'])
        restored['sources']['As']['valid_valve_range']=[0,1000]
        with self.assertRaisesRegex(InputError,'minimum and maximum'): validate_profile(restored)

    def test_repeated_measurements_and_six_point_diagnostic(self):
        rows=linear_rows(n=6)
        self.assertTrue(fit_calibration('As',measurements=rows)['warnings'])
        rows.append(rows[0])
        r=fit_calibration('As',measurements=rows)
        self.assertEqual(r['summary']['pointCount'],7)
        self.assertEqual(r['summary']['uniqueCount'],6)
        self.assertTrue(r['usable'])

    def test_fitting_independent_of_invalid_recipe(self):
        r=dispatch({'action':'fit_calibration','source':'As','measurements':linear_rows(),'settings':{'targetRate':-1}})
        self.assertTrue(r['usable'])
        for payload in ({'action':'fit_calibration','source':'As','text':'bad'},
                        {'action':'validate_calibrations','calibrations':{}},
                        {'action':'fit_calibration','source':'In','measurements':linear_rows()}):
            with self.assertRaises(InputError): dispatch(payload)
