"""Carry state through real HTTP/CLI boundaries; it remains declared display state."""
import copy
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import threading
import unittest
import urllib.error
import urllib.request
from jsonschema import Draft202012Validator, ValidationError
from echosight.api import create_server
from echosight.evolution import compare_results
from tests.test_evolution import result

ROOT = Path(__file__).resolve().parents[1]

def revisions():
    values=[]
    for i in range(4):
        item=result(2.+i*.01);item['result_id']=f'raw-{i}';item['surfaces'][0]['surface_id']=f'fit-{i}';values.append(item)
    return values

class TrackingIntegrationTests(unittest.TestCase):
    def test_http_three_comparisons_roundtrip_and_reject_stale_state(self):
        with tempfile.TemporaryDirectory() as tmp:
            server=create_server(tmp,port=0)
            thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
            address=f'http://127.0.0.1:{server.server_address[1]}/v1/compare'
            def request(body):
                req=urllib.request.Request(address,data=json.dumps(body).encode(),method='POST')
                try:
                    with urllib.request.urlopen(req) as response:return response.status,json.loads(response.read())
                except urllib.error.HTTPError as error:return error.code,json.loads(error.read())
            try:
                values=revisions();carry=None
                for value in values[1:]: value['session_id'] = 'session-b'
                for a,b in zip(values,values[1:]):
                    code,carry=request({'previous':a,'current':b,'previous_comparison':carry})
                    self.assertEqual(code,200,carry)
                    self.assertEqual(carry['current_tracks'],[{'surface_id':b['surfaces'][0]['surface_id'],'track_id':'fit-0'}])
                    self.assertEqual(carry['correspondences'][0]['additional_support_count'],
                                     4 if a['session_id'] != b['session_id'] else 0)
                    self.assertEqual(carry['schema_version'], '1.1')
                stale=copy.deepcopy(carry);stale['current_result_id']='stale'
                self.assertEqual(request({'previous':values[-1],'current':values[-1],'previous_comparison':stale})[0],400)
                cancelled=copy.deepcopy(values[-1]);cancelled['status']='cancelled'
                code,comparison=request({'previous':values[-2],'current':cancelled})
                self.assertEqual(code,200)
                self.assertEqual(comparison['status'],'incomparable')
                self.assertEqual(comparison['current_tracks'],[])
            finally:
                server.shutdown();server.server_close();thread.join()

    def test_cli_four_raw_revisions_and_malformed_carry(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);values=revisions()
            for value in values[1:]: value['session_id'] = 'session-b'
            for i,item in enumerate(values):(root/f'r{i}.json').write_text(json.dumps(item))
            prior=None
            for i in range(3):
                target=root/f'c{i}.json'
                cmd=[sys.executable,'-m','echosight','compare',str(root/f'r{i}.json'),str(root/f'r{i+1}.json'),'--output',str(target)]
                if prior:cmd+=['--previous-comparison',str(prior)]
                run=subprocess.run(cmd,cwd=ROOT,text=True,capture_output=True)
                self.assertEqual(run.returncode,0,run.stderr)
                comparison=json.loads(target.read_text());self.assertEqual(comparison['current_tracks'][0]['track_id'],'fit-0');prior=target
                self.assertEqual(comparison['correspondences'][0]['additional_support_count'], 4 if i == 0 else 0)
            Path(cmd[cmd.index('--previous-comparison')+1]).write_text(json.dumps({'schema_version':'1.0','status':'comparable','current_result_id':'raw-2','current_tracks':[]}))
            saved=target.read_bytes()
            failed=subprocess.run(cmd,cwd=ROOT,text=True,capture_output=True)
            self.assertNotEqual(failed.returncode,0)
            self.assertEqual(target.read_bytes(),saved)
            cancelled=copy.deepcopy(values[-1]);cancelled['status']='cancelled'
            (root/'r3.json').write_text(json.dumps(cancelled))
            run=subprocess.run(cmd[:cmd.index('--previous-comparison')],cwd=ROOT,text=True,capture_output=True)
            self.assertEqual(run.returncode,0,run.stderr)
            comparison=json.loads(target.read_text())
            self.assertEqual(comparison['status'],'incomparable')
            self.assertEqual(comparison['current_tracks'],[])

    def test_published_schema_covers_current_tracks_births_and_incomparable(self):
        schema=json.loads((ROOT/'schemas/comparison.schema.json').read_text());Draft202012Validator.check_schema(schema);validator=Draft202012Validator(schema)
        a,b,c,_=revisions();ab=compare_results(a,b);original=copy.deepcopy(ab)
        bc=compare_results(b,c,previous_comparison=ab);self.assertEqual(ab,original)
        empty=copy.deepcopy(a);empty['surfaces']=[]
        birth=compare_results(empty,b)
        different=copy.deepcopy(b);different['acquisition']['coordinate_frame_id']='another-frame'
        incomparable=compare_results(a,different)
        self.assertEqual(len(incomparable['current_tracks']),len(different['surfaces']))
        unscoped=copy.deepcopy(b);unscoped.pop('session_id')
        unavailable=compare_results(a,unscoped)
        cancelled=copy.deepcopy(b);cancelled['status']='cancelled'
        for value in (ab,bc,birth,incomparable,unavailable,compare_results(a,cancelled)):validator.validate(value)
        legacy=copy.deepcopy(ab);legacy['schema_version']='1.0'
        for key in ('previous_session_id','current_session_id','support_comparison_status','new_capture_references'):legacy.pop(key)
        for match in legacy['correspondences']:
            match.pop('additional_support_references');match.pop('lost_support_references')
        validator.validate(legacy)
        carried=compare_results(b,c,previous_comparison=legacy)
        self.assertEqual(carried['current_tracks'], bc['current_tracks'])
        invalid=copy.deepcopy(ab);invalid['current_tracks'].append(invalid['current_tracks'][0])
        with self.assertRaises(ValidationError):validator.validate(invalid)
        invalid=copy.deepcopy(ab);invalid['current_tracks'][0]['track_id']=''
        with self.assertRaises(ValidationError):validator.validate(invalid)

if __name__=='__main__':unittest.main()
