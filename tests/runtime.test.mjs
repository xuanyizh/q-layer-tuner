// Exercise the actual bundled WebAssembly Python runtime, without a JS physics copy.
import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {fileURLToPath} from 'node:url';
import {loadPyodide} from '../dist/vendor/pyodide/pyodide.mjs';

test('bundled browser Python loads and computes both optical modes and P inversion', async()=>{
  const py=await loadPyodide({indexURL:fileURLToPath(new URL('../dist/vendor/pyodide/',import.meta.url))});
  py.FS.mkdirTree('/app/qlayer');
  for(const name of ['__init__.py','engine.py', 'calibration.py','parameters.json','bep_calibration.json']){
    const src=readFileSync(new URL('../qlayer/'+name,import.meta.url));
    const bundled=readFileSync(new URL('../dist/python/qlayer/'+name,import.meta.url));
    assert.deepEqual(src,bundled,'Build must contain current Python source');
    py.FS.writeFile('/app/qlayer/'+name,bundled);
  }
  py.runPython("import sys,json\nsys.path.insert(0,'/app')\nfrom qlayer.engine import dispatch");
  const run=payload=>{
    py.globals.set('request_json',JSON.stringify(payload));
    return JSON.parse(py.runPython('json.dumps(dispatch(json.loads(request_json)), allow_nan=False)'));
  };
  const metadata=run({action:'metadata'});
  assert.equal(metadata.version,'2.1.0');
  const asFit=run({action:'fit_calibration',source:'As',measurements:metadata.calibration.sources.As.measurements});
  assert.ok(asFit.usable);assert.ok(Math.abs(asFit.summary.rSquared-.9998069478365443)<1e-12);
  const profile=structuredClone(metadata.calibration);
  profile.sources.As=asFit.record;
  const restored=run({action:'validate_calibrations',calibrations:profile}).profile;
  const refitted=run({action:'calculate',calibrations:restored});
  assert.ok(Math.abs(refitted.settings.As.full-101.191482723)<1e-7);
  const pFit=run({action:'fit_calibration',source:'P',unit:'microtorr',text:['10 1','20 2','30 3','40 4','50 5','60 6','70 7'].join('\n')});
  assert.ok(pFit.usable);

  for(const [mode,ga] of [['off',1000.30329156114],['on',1000.702674650466]]){
    const r=run({settings:{opticalStrain:mode}});
    assert.ok(Math.abs(r.settings.Ga.full-ga)<1e-7);
    assert.ok(Math.abs(r.prediction.pl-1197)<1e-7);
  }
  const p=run({action:'convert_bep',source:'P',direction:'valve_to_bep',value:40});
  const v=run({action:'convert_bep',source:'P',direction:'bep_to_valve',value:p.bepTorr});
  assert.ok(Math.abs(v.valve-40)<1e-8);
  assert.throws(()=>run({action:'convert_bep',source:'P',direction:'valve_to_bep',value:90}),/extrapolation/);
});
