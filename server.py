"""Run the web GUI with native Python: python server.py [--port 8000]."""
import argparse
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
import runpy
from urllib.parse import urlsplit
from qlayer.engine import dispatch, InputError, VERSION

ROOT = Path(__file__).resolve().parent


class Handler(SimpleHTTPRequestHandler):
    extensions_map = {**SimpleHTTPRequestHandler.extensions_map, '.mjs': 'text/javascript', '.wasm': 'application/wasm'}

    def reply(self, status, body):
        data = json.dumps(body, allow_nan=False).encode()
        self.send_response(status)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Content-Length', str(len(data)))
        self.send_header('Cache-Control', 'no-store')
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):
        if urlsplit(self.path).path == '/api/health':
            return self.reply(200, {'service': 'q-layer-python', 'version': VERSION})
        return super().do_GET()

    def do_POST(self):
        if urlsplit(self.path).path != '/api/compute':
            return self.reply(404, {'error': 'Unknown endpoint.'})
        # This launcher binds only to localhost and accepts same-origin requests.
        origin = self.headers.get('Origin')
        if origin and urlsplit(origin).netloc != self.headers.get('Host'):
            return self.reply(403, {'error': 'Cross-origin requests are not accepted.'})
        try:
            length = int(self.headers.get('Content-Length', '0'))
            if not 0 < length <= 65536:
                raise InputError('Request must contain at most 64 KiB of JSON.')
            payload = json.loads(self.rfile.read(length))
            return self.reply(200, {'result': dispatch(payload)})
        except (InputError, ValueError, TypeError, OverflowError) as error:
            return self.reply(400, {'error': str(error)})


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--port', type=int, default=8000)
    args = parser.parse_args()
    runpy.run_path(str(ROOT / 'tools' / 'build.py'))
    server = ThreadingHTTPServer(('127.0.0.1', args.port), partial(Handler, directory=str(ROOT / 'dist')))
    print(f'Q Layer Tuner {VERSION}: http://127.0.0.1:{args.port}/', flush=True)
    print('Keep this window open. Press Ctrl+C to stop.', flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
