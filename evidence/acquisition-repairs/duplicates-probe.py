from pathlib import Path
import copy, hashlib, io, json, sys, struct, zipfile
import numpy as np
from scipy.io import wavfile
from scipy.optimize import brentq
from echosight.simulation import simulate_session
from echosight.storage import load_session,read_recording,SessionStore,read_recording_evidence_snapshot
from echosight.signals import process_recording
from echosight.pipeline import process_session

ROOT=Path(__file__).resolve().parent
session_path=simulate_session(ROOT/'input',seed=1701,capture_count=12)
session=load_session(session_path)
rawpath=Path(session['captures'][0]['recording_path']); samples,rate=read_recording(rawpath)
obs=process_recording(samples,rate,session['probe'],'supplied')
L=obs['candidates'][0]['delay_s']*343
height=max(8.,L*2)
source=np.zeros(3); image=np.array([0.,0.,height])
poses=[]
for i in range(12):
    angle=i*2.39996323; radius=.7+.21*i
    x,y=radius*np.cos(angle),radius*np.sin(angle)
    z=brentq(lambda z:np.linalg.norm(np.array([x,y,z])-image)-np.linalg.norm([x,y,z])-L,-100,100)
    poses.append([x,y,z])
base={k:v for k,v in session.items() if k!='captures'}
base.update(source_position_m=[0.,0.,0.],session_id='duplicate-raw-evidence',source_position_std_m=.001)
float_path=ROOT/'repacked-float.wav';wavfile.write(float_path,rate,samples.astype(np.float32))
# A legal extra RIFF metadata chunk changes container bytes but not audio samples.
original=rawpath.read_bytes();extra=b'JUNK'+struct.pack('<I',4)+b'abcd'
with_junk=original[:4]+struct.pack('<I',len(original)+len(extra)-8)+original[8:]+extra
junk_path=ROOT/'repacked-junk.wav';junk_path.write_bytes(with_junk)
formats=[rawpath,float_path,junk_path]
records=[]
for p in formats:
    y,fs,h,e=read_recording_evidence_snapshot(p)
    records.append(dict(path=p.name,raw_sha256=h,sample_equal=bool(np.array_equal(samples,y)),rate=fs,format=e['format']))
with SessionStore(ROOT/'store') as store:
    store.create_session(base)
    for i,pose in enumerate(poses):
        store.add_recording(base['session_id'],formats[i%len(formats)],dict(capture_id=f'copy-{i:02d}',receiver_position_m=pose,receiver_position_std_m=.001,provenance='simulated'))
    result=process_session(store.get_session(base['session_id']))
    (ROOT/'result.json').write_text(json.dumps(result,indent=2)+'\n')
    archive=store.export_session(base['session_id'],ROOT/'duplicate-session.zip')
with SessionStore(ROOT/'replay-store') as replay:
    imported=replay.import_archive(archive)
    sid=imported['session_id']
    replay_result=process_session(replay.get_session(sid))
    (ROOT/'replay-result.json').write_text(json.dumps(replay_result,indent=2)+'\n')
report=dict(records=records,distinct_container_hashes=len(set(r['raw_sha256'] for r in records)),identical_decoded_waveforms=True,
    probe_candidate_excess_distance_m=L,declared_poses=poses,
    ordinary=dict(status=result['status'],surfaces=len(result['surfaces']),accepted_observations=sum(o['status']!='rejected' for o in result['observations']),diagnostics=result['diagnostics']),
    replay=dict(status=replay_result['status'],surfaces=len(replay_result['surfaces']),accepted_observations=sum(o['status']!='rejected' for o in replay_result['observations'])))
(ROOT/'report.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps({k:v for k,v in report.items() if k!='declared_poses'},indent=2))
