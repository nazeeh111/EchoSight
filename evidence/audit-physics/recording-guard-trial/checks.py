"""Focused experimental integration checks, independent of truth annotations."""
import copy,json
import numpy as np
from run import ROOT,REPO,ORIGINAL_INFER,guarded,guard_inference,process_session
checks=[]
folder=REPO/'work/physics-estimator/control-twelve/room-211'
raw=process_session(folder/'session.json',cancel=lambda:True);assert raw['status']=='cancelled' and not raw['surfaces'];checks.append('raw_entry_pre_cancel')
record=json.loads((ROOT/'results/twelve-room-211-matched_filter-original.json').read_text());session=record['acquisition'];observations=record['observations']
short=observations[:11];baseline=ORIGINAL_INFER(session,short);out=guarded(session,short);assert out['held_guard']['status']=='unavailable';assert out['surfaces']==baseline['surfaces'];assert 'validation_pvalue' not in json.dumps(out);checks.append('fewer_than_twelve_preserves_uncalibrated_baseline_no_p')
# Cancellation begins only once the experimental training-search branch starts.
original=guard_inference._rank_proposals;state={'inside':False}
def rank(*args,**kwargs):state['inside']=True;return original(*args,**kwargs)
guard_inference._rank_proposals=rank
try:
 out=guarded(session,observations,cancel=lambda:state['inside']);assert out['status']=='cancelled';checks.append('cancel_inside_training_search')
finally:guard_inference._rank_proposals=original
original=guard_inference._joint_refit;state={'inside':False,'calls':0}
def refine(*args,**kwargs):state['inside']=True;return original(*args,**kwargs)
def cancel():
 if state['inside']:state['calls']+=1
 return state['calls']>=2
guard_inference._joint_refit=refine
try:
 out=guarded(session,observations,cancel=cancel);assert out['status']=='cancelled';checks.append('cancel_inside_joint_optimizer')
finally:guard_inference._joint_refit=original
out=guarded(session,observations);assert out['held_guard']['training_hypotheses']<=72 and len(out['held_guard']['maximum_statistics'])==720;checks.append('bounded_hypotheses_and_permutations')
cov=np.array(out['shared_image_source_covariance_m2']);assert np.allclose(cov,cov.T) and np.linalg.eigvalsh(cov).min()>=-1e-12
pairs=[(e['capture_id'],e['candidate_id']) for s in out['surfaces'] for e in s['support']];assert len(pairs)==len(set(pairs));checks.append('exclusive_evidence_shared_covariance')
# Matrices and hypotheses must survive lossless JSON export/reload.
assert json.loads(json.dumps(out,allow_nan=False))==out;checks.append('finite_json_export_reload')
# Original-core ambiguity cannot be removed by withholding its parent in stage1.
for path in (ROOT/'results').glob('*matched_filter-original.json'):
 baseline=json.loads(path.read_text())
 if 'first_order_vs_higher_order_ambiguity' not in baseline['diagnostics']:continue
 guarded_path=path.with_name(path.name.replace('-original.json','-held_guard.json'))
 if not guarded_path.exists():continue
 other=json.loads(guarded_path.read_text());assert not other['surfaces'] and other['status']=='ambiguous' and other.get('higher_order_explanations');checks.append('preserved_physical_ambiguity:'+path.stem)
(ROOT/'checks.json').write_text(json.dumps(dict(passed=True,checks=checks),indent=2)+'\n');print(checks)
