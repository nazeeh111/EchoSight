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
    def test_path_injection_and_zip_traversal(self):
        with SessionStore(self.root / 'store') as store:
            with self.assertRaises(ValueError): store.create_session({'captures': [{'capture_id': 'x', 'recording_path': '/etc/passwd'}]})
            bad = self.root / 'bad.zip'
            with zipfile.ZipFile(bad, 'w') as z: z.writestr('../escape', 'bad')
            with self.assertRaises(ValueError): store.import_archive(bad)
            with self.assertRaises(ValueError): store.get_session('../bad')
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
