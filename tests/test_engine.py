"""Regression checks for the scientific core; run with unittest discovery."""
import json
from pathlib import Path
import unittest
from qlayer.engine import (DEFAULTS, InputError, calculate, forward,
                           bep_from_valve, valve_from_bep, calibration_summary,
                           corrected_temperature, source_curve)


class EngineTests(unittest.TestCase):
    def close(self, a, b, tol=1e-7):
        self.assertAlmostEqual(a, b, delta=tol)

    def test_48_original_python_forward_fixtures(self):
        fixtures = json.loads(Path(__file__).with_name('reference-fixtures.json').read_text())
        self.assertEqual(len(fixtures['cases']), 48)
        for case in fixtures['cases']:
            settings = {k: case[k] for k in ('plTemp', 'xrdTemp', 'axis')}
            f = forward(case['x'], case['y'], {**settings, 'opticalStrain': 'on'})
            e = case['expected']
            for actual, expected, tolerance in (
                (f['edge'], e['gap_eV'], 1e-12),
                (f['pl'], e['PL_reported_nm'], 1e-8),
                (f['mismatch'], e['mismatch_reported_arcsec'], 1e-6),
                (f['aperp'], e['a_perp_XRD_A'], 1e-12),
                (f['parallel'], e['eps_parallel'], 1e-12),
                (f['split']*1000, e['HH_LH_splitting_meV'], 1e-9)):
                self.close(actual, expected, tolerance)

    def test_optical_toggle_never_disables_coherent_xrd(self):
        for x, y in ((.19, .42), (.22, .45)):
            off = forward(x, y, {'opticalStrain': 'off'})
            on = forward(x, y, {'opticalStrain': 'on'})
            self.assertNotEqual(on['edge'], off['edge'])
            self.close(off['edge'], off['bulkGap'], 1e-12)
            self.close(on['edge']-off['edge'], on['opticalStrainShift'], 1e-12)
            for k in ('aperp', 'a0', 'mismatch', 'parallelXRD'):
                self.assertEqual(on[k], off[k])
            self.assertNotEqual(off['aperp'], off['a0'])

    def test_reference_and_full_zero_corrections_in_both_modes(self):
        for mode in ('off', 'on'):
            for temp in (280, 300, 320):
                base = {'opticalStrain': mode, 'plTemp': temp}
                r = calculate(base)
                self.close(r['target']['x'], .2)
                self.close(r['target']['y'], .4379668808441717)
                self.close(r['target']['pl'], 1197)
                self.close(r['prediction']['pl'], 1197)
                self.close(r['prediction']['mismatch'], 0)
                self.close(r['prediction']['rate'], 1)
                z = calculate({**base, 'inStep': 0, 'gaStep': 0, 'asStep': 0})
                self.close(z['prediction']['pl'], 1190)
                self.close(z['prediction']['mismatch'], 40)
                m = calculate({**base, 'measuredPL': 1197, 'mismatch': 0})
                for setting in m['settings'].values():
                    self.close(setting['current'], setting['full'])
            alternate = calculate({'opticalStrain': mode, 'targetPL': 1220})
            self.close(alternate['target']['y'], r['target']['y'])
            self.close(alternate['target']['pl'], 1220)

    def test_user_example_with_new_bep_fits(self):
        for mode, ga, arsenic in (('off', 1000.30329156114, 101.191482723),
                                  ('on', 1000.702674650466, 101.736311238873)):
            r = calculate({'opticalStrain': mode})
            self.close(r['settings']['Ga']['full'], ga)
            self.close(r['settings']['As']['full'], arsenic)
            self.assertIsNone(r['asError'])

    def test_xrd_conventions_and_known_rate(self):
        a = calculate()
        for settings in ({'axis': 'two_theta', 'mismatch': 80},
                         {'sign': 'substrate_minus_film', 'mismatch': -40},
                         {'zero': 20, 'mismatch': 60}):
            b = calculate(settings)
            for k in ('x', 'y'):
                self.close(a['current'][k], b['current'][k])
        b = calculate({'knownElement': 'Ga', 'knownRate': a['rates']['Ga']['current']})
        self.close(a['total'], b['total'])
        self.close(a['settings']['Ga']['full'], b['settings']['Ga']['full'])

    def test_synthetic_tensile_and_compressive_inverse(self):
        for mode in ('off', 'on'):
            base = calculate({'opticalStrain': mode})
            for x, y in ((.19, .42), (.22, .45), (.15, .32), (.25, .55)):
                f = forward(x, y, {'opticalStrain': mode}, offset=base['offset'])
                r = calculate({'opticalStrain': mode, 'measuredPL': f['pl'], 'mismatch': f['mismatch']})
                self.close(r['current']['x'], x, 1e-6)
                self.close(r['current']['y'], y, 1e-6)

    def test_flux_fit_quality_inverse_and_bounds(self):
        for source, lo, hi, expected_r2 in (('As', 30, 270, .9998069478365443),
                                           ('P', 5, 80, .9999792717242217)):
            summary = calibration_summary(source)
            self.close(summary['rSquared'], expected_r2, 1e-12)
            for v in (lo, (lo+hi)/2, hi):
                self.close(valve_from_bep(source, bep_from_valve(source, v)), v)
            for v in (lo-.1, hi+.1):
                with self.assertRaisesRegex(InputError, 'extrapolation'):
                    bep_from_valve(source, v)
            with self.assertRaisesRegex(InputError, 'extrapolation'):
                valve_from_bep(source, bep_from_valve(source, hi)*1.01)

    def test_p_is_reported_and_held_fixed(self):
        a, b = calculate(), calculate({'pValve': 40})
        self.assertEqual(a['settings'], b['settings'])
        self.assertTrue(b['bep']['P']['heldFixed'])
        self.close(b['bep']['P']['current'], bep_from_valve('P', 40), 1e-15)
        self.assertEqual(b['bep']['P']['current'], b['bep']['P']['applied'])
        self.assertIn('error', calculate({'pValve': 81})['bep']['P'])

    def test_invalid_or_out_of_range_as_preserves_iii(self):
        for settings in ({'asValve': 29}, {'asValve': 270},
                         {f'asC{j}': 0. for j in range(6)}):
            r = calculate(settings)
            self.assertIn('Ga', r['settings'])
            self.assertNotIn('As', r['settings'])
            self.assertIsNone(r['prediction'])
            self.assertTrue(r['asError'])
        # Positive endpoint slopes do not excuse a negative slope inside the range.
        settings = {f'asC{j}': 0. for j in range(6)}
        settings.update(asC0=1e7, asC1=9000, asC2=-100, asC3=1/3)
        with self.assertRaisesRegex(InputError, 'increase throughout'):
            source_curve('As', settings)

    def test_group_iii_temperature_formula(self):
        self.close(corrected_temperature(1014.9, 13248, .2/.1913), 1017.32340919605, 1e-9)
        a, b = calculate(), calculate({'inA': 15, 'gaA': 20})
        self.assertEqual(a['settings']['Ga'], b['settings']['Ga'])

    def test_invalid_inputs(self):
        for settings in ({'targetRate': 0}, {'knownRate': 0}, {'inRatio': 0},
                         {'gaRatio': 5}, {'measuredPL': float('nan')},
                         {'plTemp': 500}, {'inStep': 101}, {'axis': 'rocking'},
                         {'opticalStrain': 'maybe'}, {'unknown': 10}, {'pValve': 'abc'}):
            with self.assertRaises(InputError):
                calculate(settings)


if __name__ == '__main__':
    unittest.main()
