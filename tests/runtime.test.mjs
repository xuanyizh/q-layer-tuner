// Exercise the actual bundled WebAssembly Python runtime, without a JS physics copy.
import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {fileURLToPath} from 'node:url';
import {loadPyodide} from '../dist/vendor/pyodide/pyodide.mjs';

test('bundled browser Python loads and computes both optical modes and P inversion', async()=>{
  const py=await loadPyodide({indexURL:fileURLToPath(new URL('../dist/vendor/pyodide/',import.meta.url))});
  py.FS.mkdirTree('/app/qlayer');
  for(const name of ['__init__.py','engine.py','parameters.json','bep_calibration.json']){
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
  assert.equal(run({action:'metadata'}).version,'2.0.0');
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
