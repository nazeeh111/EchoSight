"""Independent connected journey: stale archive crosses actual HTTP import/replay."""
import hashlib
import io
import json
from pathlib import Path
import sys
import tempfile
import threading
import time
import urllib.error
import urllib.request
import zipfile

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from echosight.api import create_server
from echosight.simulation import simulate_session


def request(server, method, route, body=None, headers=None, raw=False):
    if isinstance(body, dict):
        body = json.dumps(body).encode()
    url = f'http://127.0.0.1:{server.server_address[1]}' + route
    req = urllib.request.Request(url, data=body, headers=headers or {}, method=method)
    with urllib.request.urlopen(req, timeout=30) as response:
        data = response.read()
        return data if raw else json.loads(data)


def finish(server, route):
    job = request(server, 'POST', route + '/jobs', {})
    deadline = time.monotonic() + 60
    while job['status'] in ('queued', 'running') and time.monotonic() < deadline:
        time.sleep(.02)
        job = request(server, 'GET', '/v1/jobs/' + job['job_id'])
    assert job['status'] == 'completed', job
    assert job['progress'] == 1
    return job, request(server, 'GET', route + '/result')


with tempfile.TemporaryDirectory(prefix='echosight-integration-') as temp:
    root = Path(temp)
    path = simulate_session(root / 'input', seed=1, capture_count=12)
    spec = json.loads(path.read_text())
    servers = []
    try:
        for name in ('original', 'reloaded'):
            server = create_server(root / name, port=0)
            thread = threading.Thread(target=server.serve_forever, daemon=True)
            thread.start()
            servers.append((server, thread))
        original, restored = [item[0] for item in servers]
        session = request(original, 'POST', '/v1/sessions', dict(spec, captures=[]))
        route = '/v1/sessions/' + session['session_id']
        hashes = {}
        for capture in spec['captures']:
            raw = (path.parent / capture['recording_path']).read_bytes()
            metadata = {key: capture[key] for key in ('capture_id', 'receiver_position_m', 'receiver_position_std_m', 'provenance')}
            imported = request(original, 'POST', route + '/recordings', raw, {'X-Capture-Metadata': json.dumps(metadata)})
            hashes[capture['capture_id']] = hashlib.sha256(raw).hexdigest()
            assert imported['sha256'] == hashes[capture['capture_id']]
        first_job, before = finish(original, route)
        assert len(before['surfaces']) == 6 and not before['stale']
        current = request(original, 'GET', route)
        revised = request(original, 'PATCH', route, {'expected_revision': current['revision'], 'captures': [
            {'capture_id': current['captures'][0]['capture_id'], 'receiver_position_std_m': .02}]})
        assert revised['revision'] == current['revision'] + 1
        assert request(original, 'GET', route + '/result')['stale']
        archived = request(original, 'GET', route + '/export', raw=True)
        with zipfile.ZipFile(io.BytesIO(archived)) as z:
            for capture in revised['captures']:
                assert hashlib.sha256(z.read(capture['recording_path'])).hexdigest() == hashes[capture['capture_id']]
        loaded = request(restored, 'POST', '/v1/imports', archived)
        assert loaded['revision'] == revised['revision']
        issues = loaded['replay']['archived_result']['binding_issues']
        assert set(issues) == {'revision_mismatch', 'acquisition_mismatch'}, issues
        try:
            request(restored, 'GET', route + '/result')
            raise AssertionError('stale archived computation was published')
        except urllib.error.HTTPError as error:
            assert error.code == 404
        try:
            request(restored, 'POST', '/v1/imports', archived)
            raise AssertionError('duplicate import replaced session')
        except urllib.error.HTTPError as error:
            assert error.code == 409
        replay_job, replay = finish(restored, route)
        assert len(replay['surfaces']) == 6 and not replay['stale']
        assert replay['session_revision'] == revised['revision']
        assert {item['capture_id']: item['sha256'] for item in replay['recording_manifest']} == hashes
        assert replay['provenance']['physical_validation'] is False
        assert request(original, 'GET', '/v1/jobs/' + first_job['job_id'] + '/result')['result_id'] == before['result_id']
        print(json.dumps({'status': 'passed', 'captures': len(hashes), 'initial_surfaces': len(before['surfaces']),
            'replayed_surfaces': len(replay['surfaces']), 'original_revision': current['revision'],
            'replayed_revision': replay['session_revision'], 'archived_binding_issues': issues,
            'checks': ['actual HTTP upload and job progress', 'six surfaces with raw evidence',
                'calibration revision marks previous result stale', 'all raw archive bytes equal input',
                'actual HTTP import quarantines stale computation', 'duplicate import cannot replace session',
                'reprocessing consumes revised snapshot', 'original per-job result remains immutable'],
            'physical_validation': False}, indent=2))
    finally:
        for server, thread in servers:
            server.shutdown()
            server.server_close()
            thread.join()
