import json
import tempfile
import threading
import time
import unittest
import urllib.error
import urllib.request
from echosight.api import create_server
from test_storage import wav_bytes


class APITests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        def process(session, cancel=None, progress=None):
            progress(.5, 'reading')
            return {'schema_version': '1.0', 'status': 'no_result', 'surfaces': [], 'diagnostics': ['fixture processor'], 'capture_count': len(session['captures'])}
        self.server = create_server(self.tmp.name, port=0, processor=process)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True); self.thread.start()
        self.url = 'http://127.0.0.1:%s' % self.server.server_address[1]
    def tearDown(self):
        self.server.shutdown(); self.server.server_close(); self.thread.join(); self.tmp.cleanup()
    def request(self, method, path, data=None, headers=None):
        if isinstance(data, dict): data = json.dumps(data).encode()
        req = urllib.request.Request(self.url + path, data=data, method=method, headers=headers or {})
        try:
            with urllib.request.urlopen(req) as response: return response.status, response.read()
        except urllib.error.HTTPError as error: return error.code, error.read()
    def test_http_recording_to_result_and_export(self):
        code, body = self.request('POST', '/v1/sessions', {'source_position_m': [0, 0, 1]})
        self.assertEqual(code, 201); sid = json.loads(body)['session_id']
        code, body = self.request('POST', f'/v1/sessions/{sid}/recordings', wav_bytes(), {'X-Capture-Metadata': json.dumps({'capture_id': 'mic1', 'receiver_position_m': [1, 1, 1]})})
        self.assertEqual(code, 201, body)
        code, body = self.request('POST', f'/v1/sessions/{sid}/jobs', {})
        self.assertEqual(code, 202); jid = json.loads(body)['job_id']
        for _ in range(100):
            code, body = self.request('GET', f'/v1/jobs/{jid}')
            if json.loads(body)['status'] == 'completed': break
            time.sleep(.01)
        code, body = self.request('GET', f'/v1/sessions/{sid}/result')
        self.assertEqual(code, 200); self.assertEqual(json.loads(body)['capture_count'], 1)
        code, body = self.request('GET', f'/v1/sessions/{sid}/export')
        self.assertEqual(code, 200); self.assertEqual(body[:2], b'PK')
    def test_compare_endpoint_and_size_limit(self):
        code, body = self.request('POST', '/v1/compare', {'previous': {'surfaces': []}, 'current': {'surfaces': []}})
        self.assertEqual(code, 200, body)
        self.assertEqual(json.loads(body)['status'], 'incomparable')
        code, _ = self.request('POST', '/v1/compare', {'previous': [], 'current': {}})
        self.assertEqual(code, 400)
        code, _ = self.request('POST', '/v1/sessions', b'', {'Content-Length': str(1024 * 1024 + 1)})
        self.assertEqual(code, 413)
    def test_compare_accepts_two_results_above_session_limit(self):
        padding = 'x' * (1024 * 1024)
        result = {'surfaces': [], 'transport_test_padding': padding}
        code, body = self.request('POST', '/v1/compare', {'previous': result, 'current': result})
        self.assertEqual(code, 200, body)
        self.assertEqual(json.loads(body)['status'], 'incomparable')
        from echosight.storage import MAX_COMPARE_BYTES
        code, _ = self.request('POST', '/v1/compare', b'', {'Content-Length': str(MAX_COMPARE_BYTES + 1)})
        self.assertEqual(code, 413)
    def test_errors_and_host_guard(self):
        for raw in (b'{broken', b'{"sound_speed_m_s":NaN}', b'[]'):
            code, _ = self.request('POST', '/v1/sessions', raw)
            self.assertEqual(code, 400)
        for length in ('-1', 'NaN'):
            code, _ = self.request('POST', '/v1/sessions', b'', {'Content-Length': length})
            self.assertEqual(code, 400)
        code, _ = self.request('POST', '/v1/sessions', b'{broken')
        self.assertEqual(code, 400)
        code, _ = self.request('POST', '/v1/sessions', {'captures': [{'capture_id': 'x', 'recording_path': '/etc/passwd'}]})
        self.assertEqual(code, 400)
        code, _ = self.request('GET', '/v1/health', headers={'Host': 'evil.example'})
        self.assertEqual(code, 403)
        code, _ = self.request('POST', '/v1/sessions', {}, {'Origin': 'https://evil.example'})
        self.assertEqual(code, 403)

if __name__ == '__main__': unittest.main()
