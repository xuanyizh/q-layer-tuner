// Python runs in a dedicated worker. There is no JavaScript physics fallback.
import { loadPyodide } from './vendor/pyodide/pyodide.mjs';
const ready = (async () => {
  const py = await loadPyodide({indexURL: new URL('./vendor/pyodide/', import.meta.url).href});
  py.FS.mkdirTree('/app/qlayer');
  for (const name of ['__init__.py', 'engine.py', 'calibration.py', 'parameters.json', 'bep_calibration.json']) {
    const response = await fetch(new URL('./python/qlayer/' + name, import.meta.url));
    if (!response.ok) throw new Error('Unable to load calculation file: ' + name);
    py.FS.writeFile('/app/qlayer/' + name, await response.text());
  }
  py.runPython("import sys, json\nsys.path.insert(0, '/app')\nfrom qlayer.engine import dispatch");
  return py;
})();
self.onmessage = async ({data}) => {
  try {
    const py = await ready;
    py.globals.set('request_json', JSON.stringify(data.payload));
    const result = py.runPython('json.dumps(dispatch(json.loads(request_json)), allow_nan=False)');
    self.postMessage({id: data.id, result: JSON.parse(result)});
  } catch (error) {
    const message = String(error.message || error).split('\n').filter(Boolean).at(-1);
    self.postMessage({id: data.id, error: message.replace(/^InputError:\s*/, '')});
  }
};
