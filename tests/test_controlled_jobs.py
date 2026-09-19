"""Controlled jobs use revision-pinned stored raw recordings and normal recovery."""
import copy
import json
import tempfile
import threading
import time
import unittest
from pathlib import Path
from echosight.storage import SessionStore
from tests.test_controlled import recording_protocol


def store_protocol(store, protocol):
    request=copy.deepcopy(protocol)
    for epoch in request['epochs']:
        session=epoch.pop('session');captures=session.pop('captures')
        sid=store.create_session(session)['session_id']
        for capture in captures:
            store.add_recording(sid,capture['recording_path'],{k:capture[k] for k in (
                'capture_id','receiver_position_m','receiver_position_std_m','provenance','device_id','receiver_pose_group_id')})
        epoch.update(session_id=sid,expected_revision=store.get_session(sid)['revision'])
    return request


def wait(store,jid):
    for _ in range(300):
        job=store.get_job(jid)
        if job['status'] in ('completed','cancelled','failed','interrupted'):return job
        time.sleep(.01)
    raise AssertionError('job timeout')


class ControlledJobTests(unittest.TestCase):
    def test_raw_job_snapshot_result_and_restart_preserve_separate_session_results(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            with SessionStore(root/'store') as store:
                request=store_protocol(store,recording_protocol(root/'input','moved',receiver_count=4))
                job=store.start_controlled_job(request);jid=job['job_id']
                self.assertEqual(wait(store,jid)['status'],'completed')
                result=store.get_job_result(jid)
                self.assertEqual(result['status'],'repeatable_acoustic_change_unlocalized')
                self.assertEqual(len(result['recording_manifest']),16)
                self.assertEqual(len(result['session_snapshots']),4)
                for epoch in request['epochs']:
                    with self.assertRaises(KeyError):store.get_result(epoch['session_id'])
                broken=copy.deepcopy(request);broken['epochs'][0]['expected_revision']=0
                with self.assertRaises(FileExistsError):store.start_controlled_job(broken)
                broken=copy.deepcopy(request);broken['epochs'][0]['session']='/etc/passwd'
                with self.assertRaises(ValueError):store.start_controlled_job(broken)
            with SessionStore(root/'store') as store:
                self.assertEqual(store.get_job_result(jid)['protocol_sha256'],result['protocol_sha256'])
                for epoch in request['epochs']:
                    with self.assertRaises(KeyError):store.get_result(epoch['session_id'])

    def test_process_crash_marks_controlled_job_interrupted(self):
        import subprocess,sys
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            with SessionStore(root/'store') as store:
                request=store_protocol(store,recording_protocol(root/'input',receiver_count=4))
            (root/'request.json').write_text(json.dumps(request))
            script="""import json,os,sys,time
from pathlib import Path
from echosight.storage import SessionStore
root=Path(sys.argv[1])
def processor(*args,**kwargs):os._exit(17)
store=SessionStore(root/'store')
store.start_controlled_job(json.loads((root/'request.json').read_text()),processor=processor)
time.sleep(5)
"""
            child=subprocess.run([sys.executable,'-c',script,str(root)],timeout=10)
            self.assertEqual(child.returncode,17)
            jobs=list((root/'store'/'jobs').glob('job_*.json'))
            jid=next(json.loads(p.read_text())['job_id'] for p in jobs if '.input.' not in p.name)
            with SessionStore(root/'store') as store:
                self.assertEqual(store.get_job(jid)['status'],'interrupted')
                with self.assertRaises(KeyError):store.get_job_result(jid)
                for epoch in request['epochs']:self.assertEqual(len(store.get_session(epoch['session_id'])['captures']),4)

    def test_cancellation_and_failed_publication_never_serve_result(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);entered=threading.Event();release=threading.Event()
            def process(protocol,cancel=None,progress=None):
                entered.set();release.wait(3)
                return {'schema_version':'1.0','status':'no_repeatable_change'}
            with SessionStore(root/'store') as store:
                request=store_protocol(store,recording_protocol(root/'input',receiver_count=4))
                job=store.start_controlled_job(request,processor=process);jid=job['job_id']
                self.assertTrue(entered.wait(1));store.cancel_job(jid);release.set()
                self.assertEqual(wait(store,jid)['status'],'cancelled')
                with self.assertRaises(KeyError):store.get_job_result(jid)
                from unittest.mock import patch
                original=store._update_job
                def fail_completion(jid,**updates):
                    if updates.get('status')=='completed':raise OSError('injected publication failure')
                    return original(jid,**updates)
                with patch.object(store,'_update_job',side_effect=fail_completion):
                    jid=store.start_controlled_job(request,processor=process)['job_id']
                    self.assertEqual(wait(store,jid)['status'],'failed')
                with self.assertRaises(KeyError):store.get_job_result(jid)
            with SessionStore(root/'store') as store:
                with self.assertRaises(KeyError):store.get_job_result(jid)

if __name__=='__main__':unittest.main()
