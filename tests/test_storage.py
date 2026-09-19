import io
import json
import tempfile
import time
import unittest
import wave
import zipfile
from pathlib import Path

from echosight.storage import SessionStore, import_recording, read_recording, validate_session


def wav_bytes():
    out = io.BytesIO()
    with wave.open(out, 'wb') as f:
        f.setnchannels(1); f.setsampwidth(2); f.setframerate(48000)
        f.writeframes(b'\x00\x00\xff\x7f\x00\x80' * 100)
    return out.getvalue()


class StorageTests(unittest.TestCase):
    def test_coordinate_frame_identity_is_a_bounded_string(self):
        for frame in [{"frame": "room"}, [], "", "x" * 161]:
            with self.subTest(frame=frame), self.assertRaises(ValueError):
                validate_session({"coordinate_frame_id": frame})

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(); self.root = Path(self.tmp.name)
        self.wav = self.root / 'input.wav'; self.wav.write_bytes(wav_bytes())
    def tearDown(self): self.tmp.cleanup()
    def test_lossless_and_decode(self):
        meta = import_recording(self.wav, self.root / 'raw')
        self.assertEqual(Path(meta['recording_path']).read_bytes(), wav_bytes())
        y, fs = read_recording(meta['recording_path'])
        self.assertEqual(fs, 48000); self.assertEqual(len(y), 300)
        self.assertEqual(y[2], -1.0)
    def test_import_uses_same_bytes_for_decode_hash_and_preservation(self):
        from unittest.mock import patch
        import echosight.storage as storage
        original = self.wav.read_bytes()
        decode = storage._read_wav
        def mutate_source_after_decode(source):
            decoded = decode(source)
            changed = bytearray(original)
            changed[24:28] = (44100).to_bytes(4, 'little')
            self.wav.write_bytes(changed)
            return decoded
        with patch('echosight.storage._read_wav', side_effect=mutate_source_after_decode):
            meta = import_recording(self.wav, self.root / 'raw')
        self.assertEqual(Path(meta['recording_path']).read_bytes(), original)
        _, actual_rate = read_recording(meta['recording_path'])
        self.assertEqual(meta['sample_rate_hz'], actual_rate)
    def test_cancel_before_publication_wins_over_completed_result(self):
        import threading
        from unittest.mock import patch
        with SessionStore(self.root / 'store') as store:
            sid = store.create_session({})['session_id']
            ready = threading.Event(); release = threading.Event()
            class InterceptResult(dict):
                def keys(self):
                    ready.set()
                    release.wait(2)
                    return super().keys()
                def __iter__(self): return super().__iter__()
            def process(session, **kwargs):
                return InterceptResult(status='no_result')
            jid = store.start_job(sid, process)['job_id']
            self.assertTrue(ready.wait(2))
            store.cancel_job(jid)
            release.set()
            for _ in range(100):
                if store.get_job(jid)['status'] in ('cancelled', 'completed'): break
                time.sleep(.01)
            self.assertEqual(store.get_job(jid)['status'], 'cancelled')
            with self.assertRaises(KeyError): store.get_result(sid)
    def test_pcm_widths_and_rates_preserve_signed_samples(self):
        for width, raw, expected in (
            (1, bytes([0, 128, 255]), [-1., 0., 127/128]),
            (2, b'\x00\x80\x00\x00\xff\x7f', [-1., 0., 32767/32768]),
            (3, b'\x00\x00\x80\x00\x00\x00\xff\xff\x7f', [-1., 0., 8388607/8388608]),
            (4, b'\x00\x00\x00\x80\x00\x00\x00\x00\xff\xff\xff\x7f', [-1., 0., 2147483647/2147483648])):
            for rate in (8000, 44100, 48000, 96000, 192000):
                with self.subTest(width=width, rate=rate):
                    out = io.BytesIO()
                    with wave.open(out, 'wb') as stream:
                        stream.setnchannels(1); stream.setsampwidth(width); stream.setframerate(rate); stream.writeframes(raw)
                    self.wav.write_bytes(out.getvalue())
                    meta = import_recording(self.wav, self.root / 'raw')
                    values, actual_rate = read_recording(meta['recording_path'])
                    self.assertEqual(actual_rate, rate); self.assertEqual(values.tolist(), expected)
                    self.assertEqual(Path(meta['recording_path']).read_bytes(), out.getvalue())
    def test_failed_session_creation_does_not_reserve_identifier(self):
        from unittest.mock import patch
        with SessionStore(self.root / 'store') as store:
            with patch('echosight.storage._write_json', side_effect=OSError('interrupted write')):
                with self.assertRaises(OSError): store.create_session({'session_id': 'retryable'})
            self.assertEqual(store.create_session({'session_id': 'retryable'})['session_id'], 'retryable')
    def test_phyphox_zip_preserves_decimal_values_and_source(self):
        path = self.root / 'phone.zip'
        with zipfile.ZipFile(path, 'w') as z:
            z.writestr('Audio samples.csv', 'sample_value\n0.123456789012345\n-0.75\n0\n')
            z.writestr('Recording rate.csv', 'reported_rate_Hz\n48000\n')
        meta = import_recording(path, self.root / 'raw')
        self.assertEqual(Path(meta['recording_path']).read_bytes(), path.read_bytes())
        y, fs = read_recording(meta['recording_path'])
        self.assertEqual(y[0], 0.123456789012345); self.assertEqual(fs, 48000)
        self.assertEqual(meta['format'], 'phyphox_csv_zip')
        self.assertIn('sample_grid_unverified', meta['diagnostics'])
    def test_phyphox_never_closes_an_explicit_sample_gap(self):
        path = self.root / 'gap.zip'
        with zipfile.ZipFile(path, 'w') as z:
            z.writestr('Audio samples.csv', 'sample_value\n0.1\n\n0.2\n')
            z.writestr('Recording rate.csv', 'reported_rate_Hz\n48000\n')
        with self.assertRaisesRegex(ValueError, 'sample gap'):
            import_recording(path, self.root / 'raw')
    def test_calibration_revision_preserves_raw_and_prior_input(self):
        with SessionStore(self.root / 'store') as store:
            sid = store.create_session({})['session_id']
            cap = store.add_recording(sid, self.wav, {'capture_id': 'phone'})
            before = store.public_session(sid)
            changed = store.update_calibration(sid, {'expected_revision': before['revision'],
                'calibration': {'source_position_m': [0, 0, 1], 'sound_speed_m_s': 344.},
                'captures': [{'capture_id': 'phone', 'receiver_position_m': [1, 1, 2]}]})
            self.assertEqual(changed['revision'], before['revision'] + 1)
            self.assertEqual(changed['captures'][0]['sha256'], cap['sha256'])
            self.assertEqual(changed['captures'][0]['receiver_position_m'], [1, 1, 2])
            self.assertEqual(Path(store.get_session(sid)['captures'][0]['recording_path']).read_bytes(), wav_bytes())
            with self.assertRaises(FileExistsError):
                store.update_calibration(sid, {'expected_revision': before['revision'], 'calibration': {'sound_speed_m_s': 345.}})
            with self.assertRaises(ValueError):
                store.update_calibration(sid, {'expected_revision': changed['revision'], 'captures': [{'capture_id': 'phone', 'sha256': '0' * 64}]})
            self.assertEqual(store.public_session(sid), changed)
            saved = self.root / 'store' / 'sessions' / sid / 'revisions' / f"revision_{before['revision']}.json"
            self.assertEqual(json.loads(saved.read_text()), before)
    def test_phyphox_rejects_inconsistent_rate_and_nonfinite(self):
        for values, rates in [('0\nnan\n', '48000\n'), ('0\n1\n', '48000\n44100\n')]:
            path = self.root / 'phone.zip'
            with zipfile.ZipFile(path, 'w') as z:
                z.writestr('Audio samples.csv', 'sample_value\n' + values)
                z.writestr('Recording rate.csv', 'reported_rate_Hz\n' + rates)
            with self.assertRaises(ValueError): import_recording(path, self.root / 'raw')
    def test_invalid_and_nonfinite(self):
        self.wav.write_bytes(b'not audio')
        with self.assertRaises(ValueError): import_recording(self.wav, self.root / 'raw')
        for spec in ({'source_position_m': [1, 2, float('nan')]}, {'sound_speed_m_s': 0}, {'captures': [{'capture_id': '../x'}]}):
            with self.assertRaises(ValueError): validate_session(spec)
    def test_export_replay_preserves_raw_and_hashes(self):
        with SessionStore(self.root / 'store') as store:
            session = store.create_session({'source_position_m': [0, 0, 1]})
            sid = session['session_id']
            store.add_recording(sid, self.wav, {'capture_id': 'mic1', 'receiver_position_m': [1, 0, 1], 'provenance': 'measured'})
            archive = store.export_session(sid)
            with SessionStore(self.root / 'replay') as replay:
                loaded = replay.import_archive(archive)
                self.assertEqual(loaded['session_id'], sid)
                raw = Path(loaded['captures'][0]['recording_path'])
                self.assertEqual(raw.read_bytes(), wav_bytes())
                self.assertEqual(loaded['captures'][0]['provenance'], 'measured')
                self.assertEqual(loaded['replay']['kind'], 'archive_reload')
    def test_maximum_response_shape_exports_and_reloads(self):
        # 32 captures × (96 kHz × (.15 s echo window + two .004 s margins) + 1).
        values = [-1.2345678901234567e-123] * 15169
        expected = {'status': 'no_result', 'observations': [
            {'capture_id': f'c{i}', 'response': {'values': values}} for i in range(32)]}
        with SessionStore(self.root / 'store') as store:
            sid = store.create_session({})['session_id']
            jid = store.start_job(sid, lambda session, **kw: expected)['job_id']
            deadline = time.monotonic() + 10
            while time.monotonic() < deadline:
                job = store.get_job(jid)
                if job['status'] in ('completed', 'failed'): break
                time.sleep(.02)
            self.assertEqual(job['status'], 'completed', job)
            archive = store.export_session(sid)
            with SessionStore(self.root / 'replay') as replay:
                loaded = replay.import_archive(archive)
                with self.assertRaises(KeyError): replay.get_result(loaded['session_id'])
                replay_archive = replay.export_session(loaded['session_id'])
                with zipfile.ZipFile(replay_archive) as z:
                    self.assertNotIn('result.json', z.namelist())
                    actual = json.loads(z.read('archived-result.json'))
                self.assertEqual(actual['observations'], expected['observations'])
                self.assertTrue(loaded['replay']['archived_result']['requires_recomputation'])
    def test_foreign_archived_geometry_is_quarantined_until_recomputed(self):
        with SessionStore(self.root / 'store') as store:
            session = store.create_session({'source_position_m': [0, 0, 1]})
            store.add_recording(session['session_id'], self.wav, {'capture_id': 'mic1'})
            session = store.public_session(session['session_id'])
            original = store.export_session(session['session_id'])
        forged = {'schema_version': '2.0', 'session_id': 'DIFFERENT_SESSION',
                  'session_revision': 99, 'status': 'ok', 'surfaces': [{'surface_id': 'fake'}],
                  'hypotheses': [], 'diagnostics': [], 'recording_manifest': [],
                  'acquisition': {}, 'provenance': {'physical_validation': True, 'evidence_classes': ['measured']}}
        payload = json.dumps(forged).encode()
        bad = self.root / 'forged.zip'
        with zipfile.ZipFile(original) as source, zipfile.ZipFile(bad, 'w') as target:
            for name in source.namelist(): target.writestr(name, source.read(name))
            target.writestr('result.json', payload)
        with SessionStore(self.root / 'replay') as replay:
            loaded = replay.import_archive(bad)
            sid = loaded['session_id']
            with self.assertRaises(KeyError): replay.get_result(sid)
            evidence = loaded['replay']['archived_result']
            self.assertEqual(evidence['status'], 'quarantined_unverified')
            self.assertTrue({'schema_mismatch', 'session_mismatch', 'revision_mismatch',
                'recording_manifest_mismatch', 'acquisition_mismatch',
                'unsupported_physical_validation_claim'} <= set(evidence['binding_issues']))
            exported = replay.export_session(sid)
            with zipfile.ZipFile(exported) as z:
                self.assertEqual(z.read('archived-result.json'), payload)
                self.assertNotIn('result.json', z.namelist())
            jid = replay.start_job(sid, lambda s, **kw: {'schema_version': '1.0', 'session_id': s['session_id'],
                'status': 'no_result', 'surfaces': [], 'provenance': {'physical_validation': False}})['job_id']
            for _ in range(100):
                if replay.get_job(jid)['status'] == 'completed': break
                time.sleep(.01)
            result = replay.get_result(sid)
            self.assertEqual(result['surfaces'], [])
            self.assertEqual(result['computation_origin'], 'local_processing')
            self.assertFalse(result['provenance']['physical_validation'])
    def test_result_budget_does_not_expand_raw_session_budget(self):
        from unittest.mock import patch
        with SessionStore(self.root / 'store') as store:
            sid = store.create_session({})['session_id']
            store.add_recording(sid, self.wav, {'capture_id': 'one'})
            source_path = store.export_session(sid)
            archive = self.root / 'two_captures.zip'
            with zipfile.ZipFile(source_path) as source, zipfile.ZipFile(archive, 'w') as target:
                for name in source.namelist():
                    raw = source.read(name)
                    if name == 'session.json':
                        session = json.loads(raw)
                        session['captures'].append(dict(session['captures'][0], capture_id='two'))
                        raw = json.dumps(session).encode()
                    target.writestr(name, raw)
        with SessionStore(self.root / 'replay') as replay:
            with patch('echosight.storage.MAX_ARCHIVE_BYTES', len(wav_bytes())):
                with self.assertRaisesRegex(ValueError, 'recording byte limit'):
                    replay.import_archive(archive)
    def test_oversized_result_archive_rejected_before_publication(self):
        from echosight.storage import MAX_RESULT_BYTES
        with SessionStore(self.root / 'store') as store:
            session = store.create_session({})
        archive = self.root / 'oversized.zip'
        with zipfile.ZipFile(archive, 'w', compression=zipfile.ZIP_DEFLATED) as z:
            z.writestr('session.json', json.dumps(session))
            z.writestr('result.json', b' ' * (MAX_RESULT_BYTES + 1))
        with SessionStore(self.root / 'replay') as replay:
            with self.assertRaisesRegex(ValueError, 'result metadata too large'):
                replay.import_archive(archive)
            with self.assertRaises(KeyError): replay.get_session(session['session_id'])
    def test_path_injection_and_zip_traversal(self):
        with SessionStore(self.root / 'store') as store:
            with self.assertRaises(ValueError): store.create_session({'captures': [{'capture_id': 'x', 'recording_path': '/etc/passwd'}]})
            bad = self.root / 'bad.zip'
            with zipfile.ZipFile(bad, 'w') as z: z.writestr('../escape', 'bad')
            with self.assertRaises(ValueError): store.import_archive(bad)
            with self.assertRaises(ValueError): store.get_session('../bad')
    def test_only_one_process_owns_store(self):
        import subprocess
        import sys
        with SessionStore(self.root / 'store'):
            child = subprocess.run([sys.executable, '-c', 'from echosight.storage import SessionStore; SessionStore(' + repr(str(self.root / 'store')) + ')'], capture_output=True, text=True)
            self.assertNotEqual(child.returncode, 0)
            self.assertIn('already open', child.stderr)
        with SessionStore(self.root / 'store'):
            pass
    def test_import_checks_revision_and_recomputes_audio_metadata(self):
        with SessionStore(self.root / 'store') as store:
            sid = store.create_session({})['session_id']
            store.add_recording(sid, self.wav, {'capture_id': 'mic1'})
            good = store.export_session(sid)
            for revision in [-1, 1]:
                altered = self.root / ('altered' + str(revision) + '.zip')
                with zipfile.ZipFile(good) as source, zipfile.ZipFile(altered, 'w') as target:
                    for name in source.namelist():
                        raw = source.read(name)
                        if name == 'session.json':
                            spec = json.loads(raw); spec['revision'] = revision
                            spec['captures'][0]['sample_count'] = 999
                            raw = json.dumps(spec).encode()
                        target.writestr(name, raw)
                with SessionStore(self.root / ('replay' + str(revision))) as replay:
                    if revision < 0:
                        with self.assertRaises(ValueError): replay.import_archive(altered)
                    else:
                        session = replay.import_archive(altered)
                        self.assertEqual(session['captures'][0]['sample_count'], 300)
    def test_checksum_failure_is_atomic(self):
        with SessionStore(self.root / 'store') as store:
            sid = store.create_session({})['session_id']
            store.add_recording(sid, self.wav, {'capture_id': 'mic1'})
            good = store.export_session(sid)
            bad = self.root / 'tampered.zip'
            with zipfile.ZipFile(good) as source, zipfile.ZipFile(bad, 'w') as target:
                for name in source.namelist():
                    raw = source.read(name)
                    if name.startswith('raw/'): raw = raw[:-1] + bytes([raw[-1] ^ 1])
                    target.writestr(name, raw)
            with SessionStore(self.root / 'replay') as replay:
                with self.assertRaises(ValueError): replay.import_archive(bad)
                with self.assertRaises(KeyError): replay.get_session(sid)
    def test_completed_job_is_immutable_and_result_can_be_stale(self):
        with SessionStore(self.root / 'store') as store:
            sid = store.create_session({})['session_id']
            jid = store.start_job(sid, lambda session, **kw: {'status': 'no_result'})['job_id']
            for _ in range(100):
                if store.get_job(jid)['status'] == 'completed': break
                time.sleep(.01)
            self.assertEqual(store.cancel_job(jid)['status'], 'completed')
            self.assertFalse(store.get_result(sid)['stale'])
            store.add_recording(sid, self.wav, {'capture_id': 'new'})
            self.assertTrue(store.get_result(sid)['stale'])
        snapshot = self.root / 'store' / 'jobs' / (jid + '.input.json')
        with SessionStore(self.root / 'store'):
            self.assertNotIn('status', json.loads(snapshot.read_text()))
    def test_jobs_cancel_and_recover(self):
        def process(session, cancel=None, progress=None):
            progress(0.2, 'running')
            for _ in range(500):
                if cancel(): return {'status': 'cancelled'}
                time.sleep(.001)
            return {'status': 'no_result'}
        with SessionStore(self.root / 'store') as store:
            sid = store.create_session({})['session_id']; job = store.start_job(sid, process)
            store.cancel_job(job['job_id'])
            for _ in range(100):
                job = store.get_job(job['job_id'])
                if job['status'] == 'cancelled': break
                time.sleep(.01)
            self.assertEqual(job['status'], 'cancelled')
        jobpath = self.root / 'store' / 'jobs' / (job['job_id'] + '.json')
        state = json.loads(jobpath.read_text()); state['status'] = 'running'; jobpath.write_text(json.dumps(state))
        with SessionStore(self.root / 'store') as store:
            self.assertEqual(store.get_job(job['job_id'])['status'], 'interrupted')

if __name__ == '__main__': unittest.main()
