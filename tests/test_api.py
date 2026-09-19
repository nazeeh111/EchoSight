import json
import tempfile
import threading
import time
import unittest
import urllib.error
import urllib.request
from echosight.api import create_server
from tests.test_storage import wav_bytes


class APITests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.processing_gate = None
        self.processing_started = threading.Event()
        def process(session, cancel=None, progress=None):
            progress(.5, 'reading')
            if self.processing_gate is not None:
                self.processing_started.set(); self.processing_gate.wait(3)
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
    def test_revision_update_uses_optimistic_concurrency(self):
        code, body = self.request('POST', '/v1/sessions', {})
        session = json.loads(body); route = '/v1/sessions/' + session['session_id']
        code, body = self.request('PATCH', route, {'expected_revision': 0, 'calibration': {'source_position_m': [0, 0, 1]}})
        self.assertEqual(code, 200, body)
        self.assertEqual(json.loads(body)['revision'], 1)
        code, _ = self.request('PATCH', route, {'expected_revision': 0, 'calibration': {'source_position_m': [0, 0, 2]}})
        self.assertEqual(code, 409)
        code, _ = self.request('PATCH', route, {'expected_revision': 1, 'calibration': {'source_position_m': [0, 0, float('nan')]}})
        self.assertEqual(code, 400)
    def test_concurrent_upload_and_calibration_do_not_change_running_input(self):
        self.processing_gate = threading.Event()
        code, body = self.request('POST', '/v1/sessions', {})
        route = '/v1/sessions/' + json.loads(body)['session_id']
        headers = {'X-Capture-Metadata': json.dumps({'capture_id': 'first'})}
        self.assertEqual(self.request('POST', route + '/recordings', wav_bytes(), headers)[0], 201)
        _, body = self.request('POST', route + '/jobs', {})
        jid = json.loads(body)['job_id']; self.assertTrue(self.processing_started.wait(1))
        self.assertEqual(self.request('POST', route + '/jobs', {})[0], 409)
        headers = {'X-Capture-Metadata': json.dumps({'capture_id': 'second'})}
        self.assertEqual(self.request('POST', route + '/recordings', wav_bytes(), headers)[0], 201)
        self.assertEqual(self.request('PATCH', route, {'expected_revision': 2, 'calibration': {'source_position_m': [0, 0, 1]}})[0], 200)
        self.processing_gate.set()
        for _ in range(100):
            _, job = self.request('GET', '/v1/jobs/' + jid)
            if json.loads(job)['status'] == 'completed': break
            time.sleep(.01)
        code, body = self.request('GET', route + '/result')
        result = json.loads(body)
        self.assertEqual(result['capture_count'], 1)
        self.assertTrue(result['stale']); self.assertEqual(result['session_revision'], 1)
        self.processing_gate = None
        _, body = self.request('POST', route + '/jobs', {})
        jid = json.loads(body)['job_id']
        for _ in range(100):
            _, job = self.request('GET', '/v1/jobs/' + jid)
            if json.loads(job)['status'] == 'completed': break
            time.sleep(.01)
        _, body = self.request('GET', route + '/result')
        self.assertEqual(json.loads(body)['capture_count'], 2); self.assertFalse(json.loads(body)['stale'])
    def test_interrupted_upload_does_not_publish_capture(self):
        import socket
        code, body = self.request('POST', '/v1/sessions', {})
        route = '/v1/sessions/' + json.loads(body)['session_id']
        port = self.server.server_address[1]
        with socket.create_connection(('127.0.0.1', port), timeout=2) as connection:
            header = f'POST {route}/recordings HTTP/1.0\r\nHost: 127.0.0.1:{port}\r\nContent-Length: 1000\r\n\r\n'.encode()
            connection.sendall(header + b'partial recording'); connection.shutdown(socket.SHUT_WR)
            self.assertIn(b'400', connection.recv(4096).split(b'\r\n', 1)[0])
        code, body = self.request('GET', route)
        self.assertEqual(code, 200); self.assertEqual(json.loads(body)['captures'], [])
        self.assertEqual(self.request('POST', route + '/recordings', wav_bytes())[0], 201)
    def test_http_cancellation_waits_for_worker_without_publishing(self):
        self.processing_gate = threading.Event()
        _, body = self.request('POST', '/v1/sessions', {})
        route = '/v1/sessions/' + json.loads(body)['session_id']
        _, body = self.request('POST', route + '/jobs', {})
        jid = json.loads(body)['job_id']; self.assertTrue(self.processing_started.wait(1))
        self.assertEqual(self.request('POST', '/v1/jobs/' + jid + '/cancel', {})[0], 202)
        self.processing_gate.set()
        for _ in range(100):
            _, job = self.request('GET', '/v1/jobs/' + jid)
            if json.loads(job)['status'] == 'cancelled': break
            time.sleep(.01)
        self.assertEqual(json.loads(job)['status'], 'cancelled')
        self.assertEqual(self.request('GET', route + '/result')[0], 404)
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
