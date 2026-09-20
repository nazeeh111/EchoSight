"""Interpretation context at raw CLI, revision, archive and HTTP boundaries."""
import contextlib
import copy
import io
import json
from pathlib import Path
import tempfile
import threading
import time
import unittest
import urllib.error
import urllib.request
import zipfile


def context(minimum_views=2):
    return {'schema_version': '1.0', 'route_id': 'declared-route', 'profiles': [],
            'maximum_squared_distance': 9., 'minimum_views': minimum_views}


def completed(store, sid):
    from echosight.pipeline import process_session
    job = store.start_job(sid, process_session)
    deadline = time.monotonic() + 30
    while job['status'] in {'queued', 'running'} and time.monotonic() < deadline:
        time.sleep(.01)
        job = store.get_job(job['job_id'])
    if job['status'] != 'completed':
        raise AssertionError(job)
    return job, store.get_result(sid)


class InterpretationIntegrationTests(unittest.TestCase):
    def test_session_rejects_unknown_interpretation_fields(self):
        from echosight.storage import validate_session
        for value in (dict(context(), unknown=True), [], True, {'profiles': []}):
            with self.subTest(context=value), self.assertRaises(ValueError):
                validate_session({'interpretation_context': value})

    def test_context_revision_preserves_raw_jobs_and_replay(self):
        from echosight.storage import SessionStore, load_session
        from echosight.simulation import simulate_session
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = load_session(simulate_session(root / 'input', seed=1, capture_count=12))
            with SessionStore(root / 'store') as store:
                sid = store.create_session(dict(source, captures=[], interpretation_context=context()))['session_id']
                for cap in source['captures']:
                    metadata = {k: cap[k] for k in ('capture_id', 'receiver_position_m', 'receiver_position_std_m', 'provenance')}
                    store.add_recording(sid, cap['recording_path'], metadata)
                first_job, first = completed(store, sid)
                before = store.public_session(sid)
                hashes = [c['sha256'] for c in before['captures']]
                changed = store.update_calibration(sid, {'expected_revision': before['revision'],
                    'interpretation_context': context(3)})
                self.assertEqual(changed['revision'], before['revision'] + 1)
                self.assertEqual([c['sha256'] for c in changed['captures']], hashes)
                self.assertTrue(store.get_result(sid)['stale'])
                self.assertEqual(store.get_job_result(first_job['job_id'])['acquisition']['interpretation_context'], context())
                _, second = completed(store, sid)
                self.assertEqual(first['surfaces'], second['surfaces'])
                self.assertNotEqual(first['result_id'], second['result_id'])
                self.assertNotEqual(first['interpretation']['context_id'], second['interpretation']['context_id'])
                exported = store.export_session(sid)
                with SessionStore(root / 'replay') as replay:
                    restored = replay.import_archive(exported)
                    self.assertEqual(restored['interpretation_context'], context(3))
                    self.assertEqual(restored['replay']['archived_result']['binding_issues'], [])
                    with self.assertRaises(KeyError): replay.get_result(sid)
                    _, recomputed = completed(replay, sid)
                    self.assertEqual(recomputed['result_id'], second['result_id'])
                    self.assertEqual(recomputed['interpretation'], second['interpretation'])
                swapped = root / 'swapped-context.zip'
                with zipfile.ZipFile(exported) as source_zip, zipfile.ZipFile(swapped, 'w') as target_zip:
                    for info in source_zip.infolist():
                        raw = source_zip.read(info.filename)
                        if info.filename == 'session.json':
                            altered = json.loads(raw)
                            altered['interpretation_context'] = context(4)
                            raw = json.dumps(altered).encode()
                        target_zip.writestr(info.filename, raw)
                with SessionStore(root / 'swapped') as replay:
                    restored = replay.import_archive(swapped)
                    self.assertEqual(restored['revision'], changed['revision'])
                    self.assertEqual(restored['replay']['archived_result']['binding_issues'], ['acquisition_mismatch'])
                    with self.assertRaises(KeyError): replay.get_result(sid)
                cleared = store.update_calibration(sid, {'expected_revision': changed['revision'], 'interpretation_context': None})
                self.assertIsNone(cleared['interpretation_context'])
                self.assertEqual([c['sha256'] for c in cleared['captures']], hashes)
                self.assertTrue(store.get_result(sid)['stale'])
                with self.assertRaises(FileExistsError):
                    store.update_calibration(sid, {'expected_revision': changed['revision'], 'interpretation_context': context()})
                with self.assertRaises(ValueError):
                    store.update_calibration(sid, {'expected_revision': cleared['revision'], 'interpretation_context': {'bad': True}})
                self.assertEqual(store.public_session(sid), cleared)

    def test_cli_context_override_is_bounded_and_demo_manifest_replays(self):
        from echosight.cli import main
        from echosight.pipeline import process_session
        from echosight.storage import MAX_JSON_BYTES
        stream = io.StringIO()
        with tempfile.TemporaryDirectory() as tmp, contextlib.redirect_stdout(stream), contextlib.redirect_stderr(io.StringIO()):
            root = Path(tmp)
            context_path = root / 'context.json'
            context_path.write_text(json.dumps(context()))
            self.assertEqual(main(['demo', str(root / 'demo'), '--seed', '1', '--captures', '12',
                                  '--interpretation-context', str(context_path)]), 0)
            manifest = root / 'demo/session.json'
            session = json.loads(manifest.read_text())
            self.assertEqual(session['interpretation_context'], context())
            initial = json.loads((root / 'demo/result.json').read_text())
            self.assertEqual(process_session(manifest)['result_id'], initial['result_id'])
            original_bytes = manifest.read_bytes()
            context_path.write_text(json.dumps(context(3)))
            destination = root / 'override.json'
            self.assertEqual(main(['process', str(manifest), '--output', str(destination),
                                  '--interpretation-context', str(context_path)]), 0)
            revised = json.loads(destination.read_text())
            self.assertEqual(manifest.read_bytes(), original_bytes)
            self.assertEqual(revised['surfaces'], initial['surfaces'])
            self.assertNotEqual(revised['result_id'], initial['result_id'])
            stream.seek(0); stream.truncate()
            self.assertEqual(main(['inspect', str(destination)]), 0)
            display = json.loads(stream.getvalue())
            self.assertIn('interpretation', display)
            self.assertEqual(display['interpretation']['surface_interpretations'][0]['material'],
                             revised['interpretation']['surface_interpretations'][0]['material'])
            self.assertEqual(display['interpretation']['surface_interpretations'][0]['appearance'],
                             revised['interpretation']['surface_interpretations'][0]['appearance'])
            self.assertNotIn('feature_records', display['interpretation']['surface_interpretations'][0])
            prior_output = destination.read_bytes()
            for raw in ('{"unexpected":true}', ' ' * (MAX_JSON_BYTES + 1)):
                context_path.write_text(raw)
                self.assertEqual(main(['process', str(manifest), '--output', str(destination),
                                      '--interpretation-context', str(context_path)]), 2)
                self.assertEqual(destination.read_bytes(), prior_output)

    def test_context_session_and_patch_schemas_reject_malformed(self):
        from tests.test_schemas import validator
        from jsonschema import ValidationError
        for name, value in [('session', {'interpretation_context': context()}),
                            ('calibration-patch', {'expected_revision': 0, 'interpretation_context': context()}),
                            ('calibration-patch', {'expected_revision': 0, 'interpretation_context': None})]:
            validator(name).validate(value)
            bad = copy.deepcopy(value)
            bad['interpretation_context'] = dict(context(), extra=True)
            with self.assertRaises(ValidationError): validator(name).validate(bad)

    def test_cli_inspect_rejects_malformed_interpretation_without_traceback(self):
        from echosight.cli import main
        with tempfile.TemporaryDirectory() as tmp, contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
            path = Path(tmp) / 'result.json'
            path.write_text(json.dumps({'surfaces': [], 'interpretation': {'surface_interpretations': [None]}}))
            self.assertEqual(main(['inspect', str(path)]), 2)

    def test_http_context_revision_and_reference_reject_stale_or_unknown_fields(self):
        from echosight.api import create_server
        from echosight.pipeline import process_session
        with tempfile.TemporaryDirectory() as tmp:
            server = create_server(tmp, port=0)
            thread = threading.Thread(target=server.serve_forever, daemon=True)
            thread.start()
            def request(method, route, body=None):
                raw = json.dumps(body).encode() if body is not None else None
                req = urllib.request.Request(f'http://127.0.0.1:{server.server_address[1]}' + route,
                                             data=raw, method=method)
                with urllib.request.urlopen(req, timeout=30) as response:
                    return json.loads(response.read())
            try:
                session = request('POST', '/v1/sessions', {'interpretation_context': context()})
                sid = session['session_id']; route = '/v1/sessions/' + sid
                completed(server.store, sid)
                with self.assertRaises(urllib.error.HTTPError) as error:
                    request('POST', route + '/material-reference', {'surface_id': 'absent', 'material_id': 'known',
                        'label': 'Known reference', 'route_id': 'route', 'provenance': {'kind': 'supplied', 'note': 'label'}})
                self.assertEqual(error.exception.code, 400)
                revised = request('PATCH', route, {'expected_revision': session['revision'], 'interpretation_context': context(3)})
                self.assertEqual(revised['interpretation_context'], context(3))
                with self.assertRaises(urllib.error.HTTPError) as error:
                    request('POST', route + '/material-reference', {'surface_id': 'absent', 'material_id': 'known',
                        'label': 'Known reference', 'route_id': 'route', 'provenance': {'kind': 'supplied', 'note': 'label'}})
                self.assertEqual(error.exception.code, 409)
                with self.assertRaises(urllib.error.HTTPError) as error:
                    request('POST', route + '/material-reference', {'surface_id': 'absent', 'recording_path': '/not/accepted'})
                self.assertEqual(error.exception.code, 400)
                with self.assertRaises(urllib.error.HTTPError) as error:
                    request('POST', '/v1/sessions', {'interpretation_context': {'unknown': True}})
                self.assertEqual(error.exception.code, 400)
            finally:
                server.shutdown(); server.server_close(); thread.join()

    def test_raw_cli_and_http_build_same_reference_profile(self):
        from evaluation.material_development import render_case, SETTINGS
        from echosight.api import create_server
        from echosight.cli import main
        from echosight.pipeline import process_session
        from echosight.interpretation import validate_context
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            path = render_case(root / 'reference', 'reference_flat')
            source = json.loads(path.read_text())
            fitted = process_session(path)
            self.assertEqual(len(fitted['surfaces']), 1)
            surface_id = fitted['surfaces'][0]['surface_id']
            provenance = {'kind': 'simulated', 'note': 'Known controlled reference with spherical 1/d pressure; no physical material qualification.'}
            appearance = {'provenance': {'kind': 'supplied', 'note': 'Contextual example palette, not an optical measurement.'},
                          'colors': [{'color_srgb': '#8A6B47', 'probability': .75}]}
            (root / 'provenance.json').write_text(json.dumps(provenance))
            (root / 'appearance.json').write_text(json.dumps(appearance))
            output = root / 'profile.json'
            with contextlib.redirect_stdout(io.StringIO()):
                code = main(['material-reference', str(path), '--surface-id', surface_id,
                    '--material-id', 'controlled-flat', '--label', 'Controlled flat reference',
                    '--route-id', SETTINGS['route_id'], '--provenance', str(root / 'provenance.json'),
                    '--appearance', str(root / 'appearance.json'), '--regularization-std-db', '1', '--output', str(output)])
            self.assertEqual(code, 0)
            cli_profile = json.loads(output.read_text())
            self.assertGreaterEqual(cli_profile['reference_summary']['sample_count'], 5)
            self.assertEqual(cli_profile['appearance'], appearance)
            self.assertEqual(cli_profile['reference_summary']['regularization_std_db'], 1.)
            server = create_server(root / 'api', port=0)
            thread = threading.Thread(target=server.serve_forever, daemon=True); thread.start()
            def request(method, route, body=None, headers=None):
                raw = json.dumps(body).encode() if isinstance(body, dict) else body
                req = urllib.request.Request(f'http://127.0.0.1:{server.server_address[1]}' + route,
                    data=raw, headers=headers or {}, method=method)
                with urllib.request.urlopen(req, timeout=30) as response: return json.loads(response.read())
            try:
                sid = request('POST', '/v1/sessions', dict(source, captures=[]))['session_id']
                route = '/v1/sessions/' + sid
                for cap in source['captures']:
                    metadata = {k: cap[k] for k in ('capture_id', 'receiver_position_m', 'receiver_position_std_m', 'provenance')}
                    request('POST', route + '/recordings', (path.parent / cap['recording_path']).read_bytes(),
                            {'X-Capture-Metadata': json.dumps(metadata)})
                job = request('POST', route + '/jobs', {})
                deadline = time.monotonic() + 30
                while job['status'] in {'queued', 'running'} and time.monotonic() < deadline:
                    time.sleep(.01); job = request('GET', '/v1/jobs/' + job['job_id'])
                self.assertEqual(job['status'], 'completed', job)
                api_profile = request('POST', route + '/material-reference', {'surface_id': surface_id,
                    'material_id': 'controlled-flat', 'label': 'Controlled flat reference',
                    'route_id': SETTINGS['route_id'], 'provenance': provenance, 'appearance': appearance,
                    'regularization_std_db': 1.})
                for key in ('mean_db', 'predictive_covariance_db2', 'training_recording_sha256',
                            'training_waveform_sha256', 'appearance'):
                    self.assertEqual(api_profile[key], cli_profile[key])
                configured = dict(context(), route_id=SETTINGS['route_id'], profiles=[api_profile])
                self.assertEqual(validate_context(configured)['profiles'][0], api_profile)
                revision = request('GET', route)['revision']
                request('PATCH', route, {'expected_revision': revision, 'interpretation_context': configured})
                _, interpreted = completed(server.store, sid)
                material = interpreted['interpretation']['surface_interpretations'][0]['material']
                self.assertEqual(material['status'], 'unknown')
                self.assertEqual(material['probabilities'], [])  # Training audio cannot become independent query evidence.
                raw_before = output.read_bytes()
                with contextlib.redirect_stderr(io.StringIO()):
                    self.assertEqual(main(['material-reference', str(path), '--surface-id', 'absent',
                        '--material-id', 'controlled-flat', '--label', 'Controlled flat reference',
                        '--route-id', SETTINGS['route_id'], '--provenance', str(root / 'provenance.json'),
                        '--output', str(output)]), 2)
                self.assertEqual(output.read_bytes(), raw_before)
            finally:
                server.shutdown(); server.server_close(); thread.join()


if __name__ == '__main__':
    unittest.main()
