"""HTTP boundaries for the opt-in local workspace, including real WAV upload."""
import hashlib
import http.client
import json
from pathlib import Path
import tempfile
import threading
import time
import unittest
from unittest.mock import patch

from echosight.api import create_server
from tests.test_storage import wav_bytes


class WebUITests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.assets = (self.root / 'assets').resolve()
        self.assets.mkdir()
        (self.assets / 'results.html').write_text('<script type="importmap">{"imports":{}}</script><script src="workspace.js"></script>')
        (self.assets / 'workspace.js').write_text('export const enabled = true;')
        (self.assets / '.private.json').write_text('{"private":true}')
        (self.root / 'outside.json').write_text('{"outside":true}')
        (self.assets / 'escape.json').symlink_to(self.root / 'outside.json')
        self.calls = []
        def process(session, cancel=None, progress=None):
            self.calls.append(session['session_id'])
            return {'schema_version': '1.0', 'status': 'no_result', 'surfaces': [], 'diagnostics': ['fixture processor']}
        with patch('echosight.webui.ui_directory', return_value=self.assets):
            self.server = create_server(self.root / 'store', port=0, processor=process, ui=True)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.port = self.server.server_address[1]
        self.host = f'127.0.0.1:{self.port}'
        self.origin = 'http://' + self.host
        self.browser = {'Origin': self.origin, 'Sec-Fetch-Site': 'same-origin', 'X-EchoSight-UI-Token': self.server.ui_token}

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join()
        self.tmp.cleanup()

    def request(self, method, route, body=None, headers=None):
        if isinstance(body, dict): body = json.dumps(body).encode()
        connection = http.client.HTTPConnection('127.0.0.1', self.port, timeout=3)
        try:
            connection.request(method, route, body=body, headers=headers or {})
            response = connection.getresponse()
            return response.status, dict(response.getheaders()), response.read()
        finally:
            connection.close()

    def duplicate(self, method, route, headers, body=b''):
        connection = http.client.HTTPConnection('127.0.0.1', self.port, timeout=3)
        try:
            connection.putrequest(method, route, skip_host=True)
            for name, value in headers: connection.putheader(name, value)
            connection.endheaders(body)
            response = connection.getresponse()
            return response.status, response.read()
        finally:
            connection.close()

    def test_browser_bootstrap_and_guard(self):
        code, headers, body = self.request('GET', '/ui/config', headers={'Sec-Fetch-Site': 'same-origin'})
        self.assertEqual(code, 200)
        self.assertEqual(json.loads(body)['token'], self.server.ui_token)
        self.assertEqual(headers['Cache-Control'], 'no-store')
        self.assertNotIn('Access-Control-Allow-Origin', headers)
        for supplied in ({'Origin': 'https://evil.example'}, {'Sec-Fetch-Site': 'cross-site'},
                         {'Sec-Fetch-Site': 'same-site'}, {'Host': 'evil.example'},
                         {'Origin': 'http://localhost:' + str(self.port)}):
            with self.subTest(supplied=supplied):
                self.assertEqual(self.request('GET', '/ui/config', headers=supplied)[0], 403)
        for supplied in ({'Sec-Fetch-Site': 'same-origin'}, {'Origin': self.origin},
                         dict(self.browser, **{'X-EchoSight-UI-Token': 'wrong'})):
            self.assertEqual(self.request('POST', '/v1/sessions', {}, supplied)[0], 403)
        self.assertEqual(self.request('POST', '/v1/sessions', {}, self.browser)[0], 201)
        self.assertEqual(self.request('POST', '/v1/sessions', {})[0], 201)

    def test_default_remains_native_only(self):
        server = create_server(self.root / 'native', port=0, processor=lambda s: {}, ui=False)
        thread = threading.Thread(target=server.serve_forever, daemon=True); thread.start()
        old_port = self.port
        try:
            self.port = server.server_address[1]
            self.assertEqual(self.request('GET', '/v1/health')[0], 200)
            self.assertEqual(self.request('GET', '/v1/health', headers={'Sec-Fetch-Site': 'none'})[0], 403)
            self.assertEqual(self.request('GET', '/ui/config')[0], 404)
        finally:
            self.port = old_port
            server.shutdown(); server.server_close(); thread.join()

    def test_static_assets_are_confined_and_csp_supports_importmap(self):
        code, headers, body = self.request('GET', '/ui/results.html', headers={'Sec-Fetch-Site': 'none'})
        self.assertEqual(code, 200)
        self.assertIn("'sha256-", headers['Content-Security-Policy'])
        self.assertIn("frame-ancestors 'none'", headers['Content-Security-Policy'])
        self.assertNotIn(self.server.ui_token.encode(), body)
        self.assertEqual(self.request('GET', '/')[0], 303)
        for route in ('/ui/%2e%2e/outside.json', '/ui/.private.json', '/ui/escape.json',
                      '/ui/%2foutside.json', '/ui/%5coutside.json', '/ui/../echosight/api.py'):
            with self.subTest(route=route): self.assertEqual(self.request('GET', route)[0], 404)
        self.assertEqual(self.request('GET', '/ui/results.html?token=anything')[0], 400)
        self.assertEqual(self.request('GET', self.origin + '/ui/config')[0], 400)

    def test_duplicate_headers_and_ambiguous_json_are_rejected(self):
        for extra in ([('Host', self.host)], [('Origin', self.origin), ('Origin', self.origin)],
                      [('X-EchoSight-UI-Token', self.server.ui_token)] * 2,
                      [('Sec-Fetch-Site', 'same-origin')] * 2):
            self.assertEqual(self.duplicate('GET', '/ui/config', [('Host', self.host)] + extra)[0], 403)
        for length in ([('Content-Length', '2')] * 2, [('Content-Length', '+2')],
                       [('Content-Length', '2,2')], [('Transfer-Encoding', 'chunked')]):
            self.assertEqual(self.duplicate('POST', '/v1/sessions', [('Host', self.host)] + length, b'{}')[0], 400)
        for raw in (b'{"probe":{},"probe":{}}', b'{"sound_speed_m_s":NaN}',
                    b'{"deep":' + b'[' * 1500 + b'0' + b']' * 1500 + b'}'):
            code, _, response = self.request('POST', '/v1/sessions', raw)
            self.assertEqual(code, 400, response)

    def test_upload_checksum_verified_before_capture_publication(self):
        _, _, raw = self.request('POST', '/v1/sessions', {}, self.browser)
        sid = json.loads(raw)['session_id']; route = f'/v1/sessions/{sid}'
        wav = wav_bytes()
        metadata = json.dumps({'capture_id': 'mic1', 'receiver_position_m': [1, 1, 1], 'provenance': 'simulated'})
        headers = dict(self.browser, **{'X-Capture-Metadata': metadata, 'X-Recording-SHA256': '0' * 64})
        self.assertEqual(self.request('POST', route + '/recordings', wav, headers)[0], 400)
        self.assertEqual(json.loads(self.request('GET', route, headers=self.browser)[2])['captures'], [])
        digest = hashlib.sha256(wav).hexdigest()
        headers['X-Recording-SHA256'] = digest
        code, _, raw = self.request('POST', route + '/recordings', wav, headers)
        self.assertEqual(code, 201, raw)
        self.assertEqual(json.loads(raw)['sha256'], digest)
        captures = json.loads(self.request('GET', route, headers=self.browser)[2])['captures']
        self.assertEqual(len(captures), 1)
        original = next((self.root / 'store' / 'sessions' / sid / 'raw').glob('*'))
        self.assertEqual(original.read_bytes(), wav)
        self.assertFalse(list((self.root / 'store').glob('echosight-upload-*')))

    def test_recording_headers_are_unambiguous_and_body_is_bounded(self):
        _, _, raw = self.request('POST', '/v1/sessions', {})
        sid = json.loads(raw)['session_id']; route = f'/v1/sessions/{sid}/recordings'
        wav = wav_bytes(); digest = hashlib.sha256(wav).hexdigest()
        common = [('Host', self.host), ('Content-Length', str(len(wav)))]
        for added in ([('X-Recording-SHA256', digest)] * 2,
                      [('X-Capture-Metadata', '{}')] * 2,
                      [('X-Capture-Metadata', '{"capture_id":"first","capture_id":"second"}')]):
            with self.subTest(headers=[h[0] for h in added]):
                self.assertEqual(self.duplicate('POST', route, common + added, wav)[0], 400)
        from echosight.storage import MAX_RECORDING_BYTES
        self.assertEqual(self.request('POST', route, b'', {'Content-Length': str(MAX_RECORDING_BYTES + 1)})[0], 413)
        session = json.loads(self.request('GET', f'/v1/sessions/{sid}')[2])
        self.assertEqual(session['captures'], [])

    def test_retried_job_identity_does_not_process_again(self):
        _, _, raw = self.request('POST', '/v1/sessions', {}, self.browser)
        sid = json.loads(raw)['session_id']; route = f'/v1/sessions/{sid}/jobs'
        code, _, raw = self.request('POST', route, {'request_id': 'request_retry'}, self.browser)
        self.assertEqual(code, 202, raw); jid = json.loads(raw)['job_id']
        for _ in range(100):
            job = json.loads(self.request('GET', '/v1/jobs/' + jid, headers=self.browser)[2])
            if job['status'] == 'completed': break
            time.sleep(.01)
        self.assertEqual(job['status'], 'completed')
        code, _, raw = self.request('POST', route, {'request_id': 'request_retry'}, self.browser)
        self.assertEqual(code, 202); self.assertEqual(json.loads(raw)['job_id'], jid)
        self.assertEqual(self.calls, [sid])
        self.assertEqual(self.request('POST', route, {'request_id': []}, self.browser)[0], 400)
        self.assertEqual(self.request('POST', route, {'request_id': '../bad'}, self.browser)[0], 400)


if __name__ == '__main__': unittest.main()
