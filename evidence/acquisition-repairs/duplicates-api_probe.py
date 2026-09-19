from pathlib import Path
import copy, hashlib, io, json, threading, time, tempfile, urllib.request, zipfile
from echosight.api import create_server
from echosight.storage import load_session, read_recording_evidence_snapshot
ROOT=Path(__file__).resolve().parent
report=json.loads((ROOT/'report.json').read_text())
session=load_session(ROOT/'input/session.json')
wave=(ROOT/'repacked-float.wav').read_bytes()
with zipfile.ZipFile('acquisition/ios/build/fixtures/waveform.echosight.zip') as native:
    manifest=json.loads(native.read('manifest.json'))
manifest['capture_id']='repackaged-duplicate-test';manifest['recording_sha256']=hashlib.sha256(wave).hexdigest()
assert manifest['frame_count']==93120
native_path=ROOT/'repacked-native.echosight.zip'
with zipfile.ZipFile(native_path,'w',compression=zipfile.ZIP_STORED) as z:
    z.writestr('manifest.json',json.dumps(manifest));z.writestr('recording.wav',wave)
y,rate,digest,evidence=read_recording_evidence_snapshot(native_path)
base={k:v for k,v in session.items() if k not in ('captures','session_id')}
base.update(source_position_m=[0,0,0],source_position_std_m=.001)
server=create_server(tempfile.mkdtemp(prefix='http-',dir=ROOT),port=0)
thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
url='http://127.0.0.1:'+str(server.server_address[1])
def request(method,route,data=None,headers=None):
    if isinstance(data,dict):data=json.dumps(data).encode()
    with urllib.request.urlopen(urllib.request.Request(url+route,data=data,method=method,headers=headers or {})) as response:return json.loads(response.read())
try:
    sid=request('POST','/v1/sessions',base)['session_id']
    paths=[ROOT/'input/capture-00.wav',ROOT/'repacked-float.wav',ROOT/'repacked-junk.wav',native_path]
    for i,pose in enumerate(report['declared_poses']):
        request('POST',f'/v1/sessions/{sid}/recordings',paths[i%4].read_bytes(),{'X-Capture-Metadata':json.dumps(dict(capture_id=f'http-copy-{i:02d}',receiver_position_m=pose,receiver_position_std_m=.001,provenance='simulated'))})
    jid=request('POST',f'/v1/sessions/{sid}/jobs',{})['job_id']
    for _ in range(300):
        job=request('GET',f'/v1/jobs/{jid}')
        if job['status'] in ('completed','failed','cancelled'):break
        time.sleep(.05)
    result=request('GET',f'/v1/sessions/{sid}/result')
    (ROOT/'http-result.json').write_text(json.dumps(result,indent=2)+'\n')
    summary=dict(status=result['status'],surfaces=len(result['surfaces']),accepted_observations=sum(o['status']!='rejected' for o in result['observations']),distinct_raw_hashes=len({o['recording_sha256'] for o in result['observations']}),native_processing_eligible=evidence['acquisition']['processing_eligible'],native_provenance='repackaged synthetic Float32 WAV and injected fixture manifest; no microphone',job_status=job['status'])
    (ROOT/'http-report.json').write_text(json.dumps(summary,indent=2)+'\n');print(json.dumps(summary,indent=2))
finally:
    server.shutdown();server.server_close();thread.join()
