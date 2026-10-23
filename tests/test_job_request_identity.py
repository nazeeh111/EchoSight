"""Request retries identify accepted jobs rather than new computations."""
import json
import tempfile
import threading
import time
import unittest
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from unittest.mock import patch

import echosight.storage as storage
from echosight.storage import SessionStore


class JobRequestIdentityTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name) / 'store'
        self.calls = []

    def tearDown(self):
        self.tmp.cleanup()

    def process(self, session, **kwargs):
        self.calls.append(session['revision'])
        return {'status': 'no_result'}

    def settle(self, store, jid):
        deadline = time.monotonic() + 3
        while time.monotonic() < deadline:
            job = store.get_job(jid)
            if job['status'] in storage.TERMINAL:
                # Terminal publication precedes event cleanup by a few lines.
                with store._lock:
                    if jid not in store._events: return job
            time.sleep(.005)
        self.fail('job did not settle')

    def test_concurrent_retries_share_one_active_job_even_when_queue_full(self):
        release = threading.Event()
        def process(session, **kwargs):
            self.calls.append(session['revision'])
            if not release.wait(3): raise RuntimeError('test worker timeout')
            return {'status': 'no_result'}
        with SessionStore(self.root, max_jobs=1) as store:
            sid = store.create_session({})['session_id']
            try:
                with ThreadPoolExecutor(max_workers=8) as pool:
                    jobs = list(pool.map(lambda _: store.start_job(sid, process, request_id='retry_123'), range(16)))
                self.assertEqual(len({job['job_id'] for job in jobs}), 1)
                self.assertEqual(jobs[0]['request_id'], 'retry_123')
                with self.assertRaisesRegex(RuntimeError, 'queue full'):
                    store.start_job(sid, process, request_id='different')
            finally:
                release.set()
            self.assertEqual(self.settle(store, jobs[0]['job_id'])['status'], 'completed')
            self.assertEqual(self.calls, [0])
            self.assertEqual(len(list((self.root / 'jobs').glob('*.input.json'))), 1)

    def test_completed_retry_keeps_original_revision_across_newer_job_and_restart(self):
        with SessionStore(self.root) as store:
            sid = store.create_session({})['session_id']
            original = store.start_job(sid, self.process, request_id='original')
            self.settle(store, original['job_id'])
            store.update_calibration(sid, {'expected_revision': 0, 'calibration': {'sound_speed_m_s': 345}})
            newer = store.start_job(sid, self.process, request_id='newer')
            self.settle(store, newer['job_id'])
            retry = store.start_job(sid, self.process, request_id='original')
            self.assertEqual((retry['job_id'], retry['session_revision']), (original['job_id'], 0))
            self.assertEqual(self.calls, [0, 1])
        with SessionStore(self.root) as store:
            retry = store.start_job(sid, self.process, request_id='original')
            self.assertEqual((retry['job_id'], retry['session_revision'], retry['status']),
                             (original['job_id'], 0, 'completed'))
            self.assertEqual(self.calls, [0, 1])
            snapshot = json.loads((self.root / 'jobs' / (retry['job_id'] + '.input.json')).read_text())
            self.assertEqual(snapshot['revision'], 0)

    def test_failed_and_cancelled_requests_remain_bound(self):
        with SessionStore(self.root) as store:
            sid = store.create_session({})['session_id']
            def failed(*args, **kwargs): raise ValueError('expected failure')
            first = store.start_job(sid, failed, request_id='failed')
            self.assertEqual(self.settle(store, first['job_id'])['status'], 'failed')
            self.assertEqual(store.start_job(sid, self.process, request_id='failed')['job_id'], first['job_id'])
            def cancelled(*args, **kwargs): return {'status': 'cancelled'}
            second = store.start_job(sid, cancelled, request_id='cancelled')
            self.assertEqual(self.settle(store, second['job_id'])['status'], 'cancelled')
        with SessionStore(self.root) as store:
            self.assertEqual(store.start_job(sid, self.process, request_id='cancelled')['job_id'], second['job_id'])
            self.assertEqual(store.start_job(sid, self.process, request_id='failed')['job_id'], first['job_id'])
            self.assertEqual(self.calls, [])

    def test_same_request_is_independent_across_sessions_and_no_key_keeps_old_behavior(self):
        with SessionStore(self.root) as store:
            a = store.create_session({})['session_id']; b = store.create_session({})['session_id']
            first = store.start_job(a, self.process, request_id='shared')
            other = store.start_job(b, self.process, request_id='shared')
            self.assertNotEqual(first['job_id'], other['job_id'])
            self.settle(store, first['job_id']); self.settle(store, other['job_id'])
            no_key = store.start_job(a, self.process)
            self.settle(store, no_key['job_id'])
            again = store.start_job(a, self.process)
            self.assertNotEqual(no_key['job_id'], again['job_id'])
            self.assertNotIn('request_id', again)
            self.settle(store, again['job_id'])

    def test_request_identifier_contract(self):
        with SessionStore(self.root) as store:
            sid = store.create_session({})['session_id']
            for invalid in ['', 'x' * 81, '../escape', '/tmp/path', 'a/b', 'é', '_first', True, 42, {}, []]:
                with self.subTest(invalid=invalid), self.assertRaises(ValueError):
                    store.start_job(sid, self.process, request_id=invalid)
            self.assertEqual(list((self.root / 'jobs').glob('*.json')), [])
            accepted = store.start_job(sid, self.process, request_id='A' + '-_' * 39 + 'z')
            self.settle(store, accepted['job_id'])

    def test_failed_snapshot_write_does_not_publish_or_launch_and_retry_is_safe(self):
        write = storage._write_json
        def fail_snapshot(path, data, *args, **kwargs):
            if str(path).endswith('.input.json'): raise OSError('snapshot disk failure')
            return write(path, data, *args, **kwargs)
        with SessionStore(self.root) as store:
            sid = store.create_session({})['session_id']
            with patch('echosight.storage._write_json', side_effect=fail_snapshot):
                with self.assertRaisesRegex(OSError, 'snapshot disk failure'):
                    store.start_job(sid, self.process, request_id='retry')
            self.assertEqual(list((self.root / 'jobs').glob('*.json')), [])
            self.assertEqual(self.calls, [])
            job = store.start_job(sid, self.process, request_id='retry')
            self.settle(store, job['job_id'])
            self.assertEqual(self.calls, [0])

    def test_post_publication_io_failure_retains_identity_without_launching(self):
        write = storage._write_json
        def write_then_fail(path, data, *args, **kwargs):
            result = write(path, data, *args, **kwargs)
            if data.get('request_id') == 'uncertain' and data.get('status') == 'queued':
                raise OSError('failure after replacement')
            return result
        with SessionStore(self.root) as store:
            sid = store.create_session({})['session_id']
            with patch('echosight.storage._write_json', side_effect=write_then_fail):
                with self.assertRaisesRegex(OSError, 'failure after replacement'):
                    store.start_job(sid, self.process, request_id='uncertain')
            retry = store.start_job(sid, self.process, request_id='uncertain')
            self.assertEqual(retry['status'], 'failed')
            self.assertEqual(retry['error']['code'], 'job_admission_failed')
            self.assertEqual(self.calls, [])
        with SessionStore(self.root) as store:
            self.assertEqual(store.start_job(sid, self.process, request_id='uncertain')['job_id'], retry['job_id'])
            self.assertEqual(self.calls, [])

    def test_pre_publication_metadata_failure_allows_safe_retry(self):
        write = storage._write_json
        def fail_metadata(path, data, *args, **kwargs):
            if data.get('request_id') == 'unpublished': raise OSError('metadata unavailable')
            return write(path, data, *args, **kwargs)
        with SessionStore(self.root) as store:
            sid = store.create_session({})['session_id']
            with patch('echosight.storage._write_json', side_effect=fail_metadata):
                with self.assertRaisesRegex(OSError, 'metadata unavailable'):
                    store.start_job(sid, self.process, request_id='unpublished')
            self.assertEqual(list((self.root / 'jobs').glob('*.json')), [])
            self.assertEqual(self.calls, [])
            job = store.start_job(sid, self.process, request_id='unpublished')
            self.settle(store, job['job_id'])
            self.assertEqual(self.calls, [0])

    def test_unfinalized_publication_failure_remains_bound_through_restart(self):
        write = storage._write_json
        def fail_after_publication(path, data, *args, **kwargs):
            if data.get('request_id') == 'unfinalized':
                if data.get('status') == 'queued': write(path, data, *args, **kwargs)
                raise OSError('persistent disk failure')
            return write(path, data, *args, **kwargs)
        with SessionStore(self.root) as store:
            sid = store.create_session({})['session_id']
            with patch('echosight.storage._write_json', side_effect=fail_after_publication):
                with self.assertRaisesRegex(OSError, 'persistent disk failure'):
                    store.start_job(sid, self.process, request_id='unfinalized')
                retry = store.start_job(sid, self.process, request_id='unfinalized')
                self.assertEqual(retry['status'], 'queued')
            self.assertEqual(self.calls, [])
        with SessionStore(self.root) as store:
            recovered = store.start_job(sid, self.process, request_id='unfinalized')
            self.assertEqual(recovered['job_id'], retry['job_id'])
            self.assertEqual(recovered['status'], 'interrupted')
            self.assertEqual(self.calls, [])

    def test_worker_submission_failure_is_terminal_and_never_retried(self):
        with SessionStore(self.root) as store:
            sid = store.create_session({})['session_id']
            with patch.object(store._pool, 'submit', side_effect=RuntimeError('worker unavailable')):
                with self.assertRaisesRegex(RuntimeError, 'worker unavailable'):
                    store.start_job(sid, self.process, request_id='submit')
            retry = store.start_job(sid, self.process, request_id='submit')
            self.assertEqual(retry['status'], 'failed')
            self.assertEqual(self.calls, [])
            self.assertEqual(store._events, {})

    def test_executor_enqueues_then_raises_without_starting_computation(self):
        with SessionStore(self.root) as store:
            sid = store.create_session({})['session_id']
            submit = store._pool.submit
            futures = []
            def enqueue_then_raise(*args, **kwargs):
                futures.append(submit(*args, **kwargs))
                raise RuntimeError('thread creation failed after enqueue')
            with patch.object(store._pool, 'submit', side_effect=enqueue_then_raise):
                with self.assertRaisesRegex(RuntimeError, 'thread creation failed'):
                    store.start_job(sid, self.process, request_id='ambiguous_submit')
            for future in futures: future.result(timeout=3)
            retry = store.start_job(sid, self.process, request_id='ambiguous_submit')
            self.assertEqual(retry['status'], 'failed')
            self.assertEqual(self.calls, [])
            self.assertEqual(store._events, {})

    def test_interrupted_request_is_recovered_without_relaunch(self):
        with SessionStore(self.root) as store:
            sid = store.create_session({})['session_id']
            job = store.start_job(sid, self.process, request_id='restart')
            self.settle(store, job['job_id'])
        path = self.root / 'jobs' / (job['job_id'] + '.json')
        metadata = json.loads(path.read_text()); metadata['status'] = 'running'
        storage._write_json(path, metadata)
        self.calls.clear()
        with SessionStore(self.root) as store:
            retry = store.start_job(sid, self.process, request_id='restart')
            self.assertEqual(retry['status'], 'interrupted')
            self.assertEqual(retry['job_id'], job['job_id'])
            self.assertEqual(self.calls, [])


if __name__ == '__main__': unittest.main()
