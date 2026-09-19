from pathlib import Path
import sys,json,copy,itertools
from unittest.mock import patch
root=Path(__file__).resolve().parent.parent;sys.path.insert(0,str(root/'work/review-37d355f-snapshot'))
import numpy as np
from echosight import multisource as ms,receiver_covariance as rc
from echosight.geometry import plane_from_image,image_source
from tests.test_multisource import fixture
from tests.test_receiver_covariance import declaration
rng=np.random.default_rng(4782);s=np.array([1.2,1.1,.9]);receivers=rng.uniform([.6,.6,.3],[3.8,3.4,2.8],(8,3));sources=np.tile(s,(8,1));qs=[image_source(s,[1,0,0],0),image_source(s,[0,1,0],0),np.array([-s[0],-s[1],s[2]])]
rows=[];links=[]
for i,r in enumerate(receivers):
    peaks=[dict(candidate_id=f'{i}-{k}',delay_s=float((np.linalg.norm(q-r)-np.linalg.norm(s-r))/343),delay_std_s=2e-5) for k,q in enumerate(qs)]
    rows.append(dict(source_index=0,session_id='s0',receiver_group=f'g{i}',o=dict(capture_id=str(i),direct_std_s=2e-5,receiver_position_std_m=900.),peaks=peaks,t=np.array([p['delay_s'] for p in peaks])))
    links.extend((k,i,k) for k in range(3))
B=rng.normal(size=(24,8));C=B@B.T*1e-6+np.eye(24)*1e-7;cal=dict(index={f'g{i}':i for i in range(8)},covariance=C);calls=[]
def capture(groups,gradients,stds,calibration):
    value=rc.marginal(groups,gradients,stds,calibration);calls.append((groups,np.array(gradients),value));return value
out=dict(surfaces=[dict(surface_id=f'p{k}') for k in range(3)],hypotheses=[],diagnostics=[],guidance=[])
with patch.object(ms,'_receiver_marginal',side_effect=capture):
    ms._parent_subset_alternatives(out,qs,s,sources,receivers,343.,rows,links,np.zeros((4,4)),np.eye(9)*1e-6,None,cal)
planes=[plane_from_image(s,q) for q in qs];paths=[(i,) for i in range(3)]+list(itertools.permutations(range(3),2));maxerr=0.
for path,(groups,g,variance) in zip(paths,calls):
    image=s.copy()
    for k in path:image=image_source(image,*planes[k])
    def f(r):return (np.linalg.norm(image-r,axis=1)-np.linalg.norm(s-r,axis=1))/343.
    r=np.array([receivers[i] for _,i,_ in links]);ng=np.zeros_like(r)
    for axis in range(3):
        h=np.eye(3)[axis]*1e-5;ng[:,axis]=(f(r+h)-f(r-h))/2e-5
    maxerr=max(maxerr,float(np.max(abs(g-ng))))
    nv=np.array([ng[j]@C[3*int(group[1:]):3*int(group[1:])+3,3*int(group[1:]):3*int(group[1:])+3]@ng[j] for j,group in enumerate(groups)])
    np.testing.assert_allclose(variance,nv,rtol=1e-7,atol=1e-19)
assert len(calls)==9 and maxerr<1e-11
# Public raw entry validates malformed/full declarations before recording I/O.
data,bundle=fixture(receivers=4);raw=copy.deepcopy(bundle);raw['sessions']=[]
for item in data:
    session=copy.deepcopy(item['session']);session['probe']={};session['captures']=[]
    for o in item['observations']:session['captures'].append(dict(capture_id=o['capture_id'],receiver_position_m=o['receiver_position_m'],receiver_pose_group_id=o['receiver_pose_group_id'],recording_path='/nonexistent/no-read.wav'))
    raw['sessions'].append(session)
raw['shared_calibration']['receiver_pose_covariance']=declaration(data,np.eye(12)*1e-6)
malformed=[]
for change in [('scalar_policy','add'),('group_ids',['r0']*65),('covariance_m2',np.diag([-1]+[1]*11).tolist())]:
    bad=copy.deepcopy(raw);bad['shared_calibration']['receiver_pose_covariance'][change[0]]=change[1];malformed.append(bad)
with patch('echosight.storage.read_recording_evidence_snapshot',side_effect=AssertionError('reading prior to validation')):
    for bad in malformed:
        result=ms.process_scene_bundle(bad);assert result['status']=='no_result' and result['diagnostics'] and not result['processed_sessions']
    assert ms.process_scene_bundle(raw,cancel=lambda:True)['status']=='cancelled'
# Rejected evidence is still part of calibration coverage, and cancellation fires inside validation.
processed,b=fixture(receivers=4);b['shared_calibration']['receiver_pose_covariance']=declaration(processed,np.eye(12)*1e-6)
processed[0]['observations'][0].update(status='rejected',receiver_pose_group_id='not-declared')
assert ms.infer_scene_bundle(processed,b)['status']=='calibration_needed'
counter=[0]
def cancel():counter[0]+=1;return counter[0]>=3
assert ms.infer_scene_bundle(data,b,cancel=cancel)['status']=='cancelled'
summary={'parent_paths_checked':len(calls),'parent_receiver_gradient_max_error':maxerr,'parent_marginals_match_independent_block_projection':True,'raw_invalid_and_oversized_declarations_fail_before_read':3,'rejected_observation_coverage_enforced':True,'validation_cancelled_on_callback':counter[0]}
(root/'work/review-37d355f-boundary-probes.json').write_text(json.dumps(summary,indent=2)+'\n');print(json.dumps(summary,indent=2))
