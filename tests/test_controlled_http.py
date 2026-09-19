import copy
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import threading
import time
import unittest
import urllib.request
import urllib.error
from echosight.api import create_server
from evaluation.controlled_development import recording_protocol


class ControlledHTTPTests(unittest.TestCase):
    def test_api_and_cli_process_same_four_phone_recordings(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);protocol=recording_protocol(root/'recordings','moved',receiver_count=4)
            path=root/'protocol.json'
            portable=copy.deepcopy(protocol)
            for epoch in portable['epochs']:
                for capture in epoch['session']['captures']:
                    capture['recording_path']=str(Path(capture['recording_path']).relative_to(root.resolve()))
            path.write_text(json.dumps(portable))
            cli=subprocess.run([sys.executable,'-m','echosight','controlled',str(path),'--output',str(root/'cli.json')],capture_output=True,text=True)
            self.assertEqual(cli.returncode,0,cli.stderr)
            expected=json.loads((root/'cli.json').read_text())
            self.assertEqual(expected['status'],'repeatable_acoustic_change_unlocalized')
            server=create_server(root/'store',port=0)
            thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
            def request(method,route,body=None,headers=None):
                raw=json.dumps(body).encode() if isinstance(body,dict) else body
                req=urllib.request.Request(f'http://127.0.0.1:{server.server_port}'+route,data=raw,method=method,headers=headers or {})
                try:
                    with urllib.request.urlopen(req,timeout=10) as response:return response.status,json.load(response)
                except urllib.error.HTTPError as exc:return exc.code,json.load(exc)
            try:
                api=copy.deepcopy(protocol)
                for epoch in api['epochs']:
                    session=epoch.pop('session');captures=session.pop('captures')
                    status,saved=request('POST','/v1/sessions',session);self.assertEqual(status,201,saved)
                    sid=saved['session_id']
                    for c in captures:
                        meta={k:c[k] for k in ('capture_id','receiver_position_m','receiver_position_std_m','device_id','receiver_pose_group_id','provenance')}
                        status,saved=request('POST',f'/v1/sessions/{sid}/recordings',Path(c['recording_path']).read_bytes(),{'X-Capture-Metadata':json.dumps(meta)})
                        self.assertEqual(status,201,saved)
                    epoch.update(session_id=sid,expected_revision=len(captures))
                status,job=request('POST','/v1/controlled-jobs',api);self.assertEqual(status,202,job)
                jid=job['job_id']
                for _ in range(200):
                    _,job=request('GET',f'/v1/jobs/{jid}')
                    if job['status'] in ('completed','failed','cancelled'):break
                    time.sleep(.02)
                self.assertEqual(job['status'],'completed',job)
                status,result=request('GET',f'/v1/jobs/{jid}/result');self.assertEqual(status,200,result)
                self.assertEqual(result['status'],expected['status'])
                self.assertEqual(result['receiver_evidence'],expected['receiver_evidence'])
                bad=copy.deepcopy(api);bad['epochs'][0]['session']='/etc/passwd'
                self.assertEqual(request('POST','/v1/controlled-jobs',bad)[0],400)
                bad=copy.deepcopy(api);bad['epochs'][0]['expected_revision']=0
                self.assertEqual(request('POST','/v1/controlled-jobs',bad)[0],409)
                self.assertEqual(request('POST','/v1/controlled-jobs',b'',{'Content-Length':str(1024*1024+1)})[0],413)
            finally:
                server.shutdown();thread.join();server.server_close()

if __name__=='__main__':unittest.main()
