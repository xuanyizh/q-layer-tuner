"""Test local HTTP transport using an ephemeral loopback test server."""
from functools import partial
from http.server import ThreadingHTTPServer
import json
from threading import Thread
import unittest
from urllib.error import HTTPError
from urllib.request import Request, urlopen
from server import Handler, ROOT


class QuietHandler(Handler):
    def log_message(self, *_args):
        pass


class ServerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server = ThreadingHTTPServer(('127.0.0.1', 0), partial(QuietHandler, directory=str(ROOT/'dist')))
        cls.thread = Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()
        cls.url = 'http://127.0.0.1:' + str(cls.server.server_port)

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.thread.join()

    def post(self, payload):
        return urlopen(Request(self.url+'/api/compute', data=json.dumps(payload).encode(), headers={'Content-Type': 'application/json'}))

    def test_native_api_and_static_assets(self):
        with urlopen(self.url+'/api/health') as response:
            self.assertEqual(json.load(response)['service'], 'q-layer-python')
        with self.post({'settings': {'opticalStrain': 'on', 'pValve': 40}}) as response:
            r = json.load(response)['result']
            self.assertAlmostEqual(r['settings']['Ga']['full'], 1000.702674650466, places=7)
            self.assertEqual(r['bep']['P']['valve'], 40)
        with urlopen(self.url+'/') as response:
            self.assertIn('opticalStrain', response.read().decode())
        with urlopen(self.url+'/vendor/pyodide/pyodide.asm.wasm') as response:
            self.assertEqual(response.headers['Content-Type'], 'application/wasm')
            self.assertEqual(response.read()[:4], b'\x00asm')

    def test_bad_input_returns_json_error(self):
        with self.assertRaises(HTTPError) as context:
            self.post({'settings': {'measuredPL': None}})
        self.assertEqual(context.exception.code, 400)
        self.assertIn('measuredPL', json.load(context.exception)['error'])
