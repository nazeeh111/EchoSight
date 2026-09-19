"""Existing-recording public calibration handoff covariance probe. No generation."""
from pathlib import Path
import sys,json,hashlib
import numpy as np
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT))
from echosight.calibration import calibrate_reference,_jacobian
from echosight.storage import load_session,validate_session,SessionStore
from echosight import inference
P=Path(__file__).resolve().parent
folder=ROOT/'work/source-calibration-mismatch/run-v2/raw/single-2821-x'
session=load_session(folder/'session.json');reference=json.loads((folder/'reference.json').read_text())
result=calibrate_reference(session,reference)
assert result['status']=='calibration_proposal'
# This is a public, valid source-calibration PATCH shape, applied to a validated session.
mapped=validate_session(dict(session,**result['calibration']))
observations=json.loads((folder/'observations.json').read_text())['observations']
by_id={o['capture_id']:o for o in observations}
ids=reference['training_capture_ids']+reference['validation_capture_ids']
cs={c['capture_id']:c for c in session['captures']}
selected={e['capture_id']:e['candidate_id'] for e in result['evidence']}
points=np.array([cs[c]['receiver_position_m'] for c in ids]);n=np.array(reference['normal']);d=reference['offset_m']
theta=np.r_[mapped['source_position_m'],np.log(mapped['effective_speed_m_s'])]
def predict(t):
 s=t[:3];q=s+2*(d-n@s)*n;return (np.linalg.norm(points-q,axis=1)-np.linalg.norm(points-s,axis=1))/np.exp(t[3])
H=_jacobian(predict,theta)
s=theta[:3];v=np.exp(theta[3]);q=s+2*(d-n@s)*n
D=np.zeros((12,36))
for i,r in enumerate(points):
 D[i,3*i:3*i+3]=((r-q)/np.linalg.norm(r-q)-(r-s)/np.linalg.norm(r-s))/v
R=np.diag(np.repeat([cs[c].get('receiver_position_std_m',.01)**2 for c in ids],3))
timing=[]
for c in ids:
 o=by_id[c];p=next(p for p in o['candidates'] if p['candidate_id']==selected[c]);clock=o['clock']
 timing.append(p['delay_std_s']**2+o['direct_std_s']**2+(p['delay_s']*clock['alpha_std']/clock['alpha'])**2)
T=np.diag(timing);Cnoise=T+D@R@D.T
count=len(reference['training_capture_ids']);W=np.diag(1/np.diag(Cnoise)[:count]);K=np.linalg.solve(H[:count].T@W@H[:count],H[:count].T@W)
F=np.diag([1,1,1,v]);Hp=H@np.linalg.inv(F)
Cp=np.array(mapped['source_effective_speed_covariance']);cross=-F@K@D[:count]@R
prepared=inference._prepare(mapped,observations,inference._empty(mapped,'probe'));assert prepared is not None
ss,vv,rows,rr=prepared
links=[(0,i,next(j for j,p in enumerate(row['peaks']) if p['candidate_id']==selected[row['o']['capture_id']])) for i,row in enumerate(rows)]
_,runtime,_=inference._covariance([q],links,ss,rr,vv,rows,mapped)
independent=T+Hp@Cp@Hp.T+D@R@D.T
assert np.allclose(runtime,independent,rtol=1e-5,atol=1e-15)
term=Hp@cross@D.T
correct_fresh=independent+term+term.T
# Same raw recordings add dependence between their timing error and fitted calibration.
timing_cross=F@K@T[:count,:]
shared_timing=Hp@timing_cross
correct_same=correct_fresh-shared_timing-shared_timing.T
assert np.linalg.eigvalsh(correct_fresh).min()>0
assert np.linalg.eigvalsh(correct_same).min()>-1e-15
out=dict(status='reproduced',source_case=str(folder.relative_to(ROOT)),public_calibration_status=result['status'],input_id=result['input_id'],runtime_sha256=hashlib.sha256((ROOT/'echosight/inference.py').read_bytes()).hexdigest(),scope='Analytic local covariance on existing isolated-reference paths. Fresh audio is a conditional independence comparison, not generated or measured data. No room result or coverage claim.',maximum_runtime_covariance_match_abs=float(np.max(abs(runtime-independent))),max_abs_source_receiver_cross_covariance_by_parameter=np.max(abs(cross),axis=1).tolist(),per_capture=[dict(capture_id=c,training=i<count,independence_sd_us=float(np.sqrt(independent[i,i])*1e6),shared_survey_fresh_audio_sd_us=float(np.sqrt(correct_fresh[i,i])*1e6),shared_survey_same_audio_sd_us=float(np.sqrt(max(0,correct_same[i,i]))*1e6),fresh_sd_ratio=float(np.sqrt(correct_fresh[i,i]/independent[i,i])),same_sd_ratio=float(np.sqrt(max(0,correct_same[i,i])/independent[i,i]))) for i,c in enumerate(ids)],parameter_receiver_cross_covariance=cross.tolist(),source_effective_speed_covariance=Cp.tolist(),note='Cross term sign uses survey error = declared minus actual; estimator error = K(timing error - D survey error - G reference error). Calibration marginal is preserved; this probe isolates omitted correlations, not estimator changes.')
(P/'cross-probe.json').write_text(json.dumps(out,indent=2)+'\n')
print(json.dumps({k:val for k,val in out.items() if k not in ['parameter_receiver_cross_covariance','source_effective_speed_covariance','per_capture']},indent=2))
print(json.dumps(out['per_capture'],indent=2))
