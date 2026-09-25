"""Offline desktop launcher. Package with build_windows.py on Windows."""
import argparse
from functools import partial
from http.server import ThreadingHTTPServer
import json
import math
from pathlib import Path
import sys
from threading import Thread
import traceback
from urllib.request import Request, urlopen
import webbrowser

from server import Handler, ROOT
from qlayer.engine import VERSION


class DesktopHandler(Handler):
    # Windowed executables have no stderr; the base handler logs there.
    def log_message(self, *_args):
        pass


class LocalApp:
    def __init__(self):
        self.server = ThreadingHTTPServer(
            ('127.0.0.1', 0), partial(DesktopHandler, directory=str(ROOT / 'dist')))
        self.url = f'http://127.0.0.1:{self.server.server_port}/'
        self.thread = Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()

    def close(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=5)


def self_test(report_path, check_gui=True):
    """Exercise the installed bundle through its actual local HTTP API."""
    checks = []
    report = {'version': VERSION, 'frozen': bool(getattr(sys, 'frozen', False)),
              'platform': sys.platform, 'checks': checks, 'passed': False}
    app = None
    try:
        if check_gui:
            import tkinter as tk
            root = tk.Tk()
            root.withdraw()
            root.update()
            root.destroy()
            checks.append('Native launcher window and bundled Tcl/Tk')
        app = LocalApp()

        def get(path):
            with urlopen(app.url + path, timeout=20) as response:
                return response.read()

        def compute(payload):
            request = Request(app.url + 'api/compute',
                              data=json.dumps(payload).encode(),
                              headers={'Content-Type': 'application/json'})
            with urlopen(request, timeout=20) as response:
                return json.load(response)['result']

        health = json.loads(get('api/health'))
        assert health == {'service': 'q-layer-python', 'version': VERSION}, health
        checks.append('Native Python service and version')
        assert b'v2.1' in get('')
        for asset in ('app.js', 'style.css', 'python-client.js', 'engine-worker.mjs',
                      'python/qlayer/engine.py', 'python/qlayer/calibration.py'):
            assert len(get(asset)) > 0, asset
        assert get('vendor/pyodide/pyodide.asm.wasm')[:4] == b'\x00asm'
        checks.append('Bundled interface, Python resources and offline assets')
        assert compute({'action': 'metadata'})
        result = compute({'settings': {'opticalStrain': 'off'}})
        assert math.isclose(result['settings']['Ga']['full'], 1000.30329156114, abs_tol=1e-7)
        assert math.isclose(result['settings']['As']['full'], 101.191482723, abs_tol=1e-7)
        checks.append('Default recipe matches v2.1 scientific reference')
        profile = json.loads((ROOT / 'qlayer' / 'bep_calibration.json').read_text(encoding='utf-8'))
        for source in ('As', 'P'):
            fit = compute({'action': 'fit_calibration', 'source': source,
                           'measurements': profile['sources'][source]['measurements']})
            assert fit['usable'], fit
            assert fit['summary']['rSquared'] > .999
            profile['sources'][source] = fit['record']
            checks.append(f'{source} measured-pair fitting through local API')
        restored = compute({'action': 'validate_calibrations', 'calibrations': profile})['profile']
        fitted = compute({'settings': {'opticalStrain': 'off'}, 'calibrations': restored})
        assert math.isclose(fitted['settings']['As']['full'], 101.191482723, abs_tol=1e-7)
        checks.append('Saved calibration profile round trip and recipe calculation')
        report['passed'] = True
    except Exception:
        report['error'] = traceback.format_exc()
    finally:
        if app is not None:
            app.close()
        Path(report_path).write_text(json.dumps(report, indent=2), encoding='utf-8')
    return 0 if report['passed'] else 1


def launch():
    import tkinter as tk
    from tkinter import messagebox, ttk

    root = tk.Tk()
    root.title(f'Q Layer Tuner {VERSION}')
    root.resizable(False, False)
    root.configure(background='#f3f6fa')
    app = None
    try:
        app = LocalApp()
        frame = ttk.Frame(root, padding=24)
        frame.grid()
        ttk.Label(frame, text='Q Layer Tuner', font=('Segoe UI', 19, 'bold')).grid(
            row=0, column=0, columnspan=2, sticky='w')
        ttk.Label(frame, text=f'Version {VERSION}  |  Running locally',
                  font=('Segoe UI', 10)).grid(row=1, column=0, columnspan=2, sticky='w', pady=(4, 16))
        ttk.Label(frame, text='The app opens in your web browser.\n'
                  'Keep this launcher open while you use it.\n'
                  'Python is included. No internet connection is needed.',
                  font=('Segoe UI', 10)).grid(row=2, column=0, columnspan=2, sticky='w')
        url_text = tk.StringVar(value=app.url)
        ttk.Entry(frame, textvariable=url_text, state='readonly', width=48).grid(
            row=3, column=0, columnspan=2, sticky='ew', pady=(16, 10))
        ttk.Label(frame, text='Save calibrations JSON in the app to keep fitted curves.',
                  font=('Segoe UI', 9)).grid(row=4, column=0, columnspan=2, sticky='w', pady=(0, 16))

        def open_app():
            if not webbrowser.open(app.url):
                messagebox.showinfo('Open Q Layer Tuner', f'Open this address in your browser:\n{app.url}')

        ttk.Button(frame, text='Open app', command=open_app).grid(row=5, column=0, sticky='ew', padx=(0, 8))
        ttk.Button(frame, text='Quit', command=root.destroy).grid(row=5, column=1, sticky='ew')
        root.protocol('WM_DELETE_WINDOW', root.destroy)
        root.after(350, open_app)
        root.mainloop()
    except Exception as error:
        messagebox.showerror('Q Layer Tuner could not start', str(error))
        return 1
    finally:
        if app is not None:
            app.close()
    return 0


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--self-test', metavar='REPORT_JSON')
    parser.add_argument('--skip-gui-test', action='store_true', help=argparse.SUPPRESS)
    args = parser.parse_args()
    raise SystemExit(self_test(args.self_test, not args.skip_gui_test) if args.self_test else launch())
