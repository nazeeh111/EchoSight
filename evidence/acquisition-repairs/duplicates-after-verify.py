from pathlib import Path
import hashlib,json
import numpy as np
from echosight.pipeline import process_session
from echosight.storage import waveform_sha256
ROOT=Path(__file__).resolve().parent
source_names=['echosight/storage.py','echosight/pipeline.py','echosight/signals.py','echosight/inference.py','echosight/geometry.py','echosight/calibration.py','echosight/controlled.py']
before={n:hashlib.sha256(Path(n).read_bytes()).hexdigest() for n in source_names}
checks={}
for name in ('result.json','replay-result.json','http-result.json'):
    result=json.loads((ROOT/name).read_text())
    obs=result['observations']
    assert len(obs)==12 and all(o['status']=='rejected' and not o['candidates'] for o in obs)
    assert all(any(d.get('code')=='recording_waveform_reused' for d in o['diagnostics'] if isinstance(d,dict)) for o in obs)
    assert all(len(o['duplicate_waveform_group'])==12 for o in obs)
    assert len({o['waveform_sha256'] for o in obs})==1
    assert result['surfaces']==[] and result['status']=='no_result'
    checks[name]={'observations':12,'all_group_members_rejected':True,'surfaces':0,'status':result['status'],'group_size':12}
retained=[]
for store in [ROOT/'store',ROOT/'replay-store']+sorted(ROOT.glob('http-*')):
    if not store.is_dir():continue
    for session_path in (store/'sessions').glob('*/session.json'):
        session=json.loads(session_path.read_text());captures=session['captures']
        assert len(captures)==12
        for c in captures:
            raw=(session_path.parent/c['recording_path']).read_bytes()
            assert hashlib.sha256(raw).hexdigest()==c['sha256']
        retained.append({'store':store.name,'capture_references':12,'distinct_containers':len({c['sha256'] for c in captures}),'all_original_byte_hashes_verified':True})
control=process_session(ROOT/'input/session.json')
(ROOT/'unique-control-result.json').write_text(json.dumps(control,indent=2)+'\n')
assert len(control['observations'])==12 and all(o['status']!='rejected' for o in control['observations'])
assert len(control['surfaces'])==6
assert len({o['waveform_sha256'] for o in control['observations']})==12
x=np.array([0.,-0.,1.]);y=np.array([-0.,0.,1.]);bits=x.view(np.uint64).copy()
assert waveform_sha256(x,48000)==waveform_sha256(y,48000)
assert np.array_equal(bits,x.view(np.uint64))
assert waveform_sha256(x,48000)!=waveform_sha256(x,44100)
after={n:hashlib.sha256(Path(n).read_bytes()).hexdigest() for n in source_names}
assert before==after,'Source changed during verification'
report=dict(checks=checks,retained=retained,unique_control={'accepted_observations':12,'surfaces':6,'status':control['status'],'distinct_waveforms':12,'seed':1701},signed_zero={'digest_equal':True,'original_bits_untouched':True,'different_rate_digest_different':True},source_sha256=after)
(ROOT/'verification.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
