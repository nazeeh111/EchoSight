from pathlib import Path
import argparse,hashlib,json,sys,types
import numpy as np
from scipy.optimize import lsq_linear
ROOT=Path(__file__).resolve().parents[2]
parser=argparse.ArgumentParser(description='Independent v4 algebra and frozen-report consistency checks; no classifiers or raw generation.')
parser.add_argument('--snapshot',type=Path,default=ROOT/'evidence/source-model-diagnostic-v4')
parser.add_argument('--output',type=Path,default=ROOT/'work/source-model-v4-review-reproduction.json')
args=parser.parse_args();S=args.snapshot.resolve()
m=json.loads((S/'MANIFEST.json').read_text())
for n,h in m['files'].items():assert hashlib.sha256((S/n).read_bytes()).hexdigest()==h,n
for name in ['gain_v4','waveform_v4']:
 module=types.ModuleType(name);module.__file__=str(S/(name+'.py'));sys.modules[name]=module;exec(compile((S/(name+'.py')).read_bytes(),module.__file__,'exec'),module.__dict__)
g=sys.modules['gain_v4'];w=sys.modules['waveform_v4'];rng=np.random.default_rng(88403);cases=[]
for kind in ['ordinary','correlated','anti_correlated','identical','zero_primary','zero_secondary','both_zero']:
 for _ in range(12):
  a=rng.normal(size=37);b=rng.normal(size=37);y=rng.normal(size=37)*3
  if kind=='correlated':b=a+.002*b
  if kind=='anti_correlated':b=-a+.002*b
  if kind=='identical':b=a.copy()
  if kind in ['zero_primary','both_zero']:a*=0
  if kind in ['zero_secondary','both_zero']:b*=0
  coeff,residual=g.bounded_gains(a,b,y[None,:]);fit=lsq_linear(np.column_stack([a,b]),y,bounds=([0,-2],[2,2]),method='bvls',tol=1e-13)
  actual=float(residual[0]@residual[0]);reference=float(np.sum((np.column_stack([a,b])@fit.x-y)**2));error=abs(actual-reference)
  assert error<1e-9,(kind,error);assert np.all(coeff[0]>=[0,-2]) and np.all(coeff[0]<=[2,2]);cases.append(dict(kind=kind,absolute_objective_error=error))
# Independent physical absent-plane check, three geometrically different records.
sources=np.array([[.4,0,.7],[.4,0,.7],[.4,0,.7]]);receivers=np.array([[1.2,.3,.8],[-.6,.3,.8],[1.2,-.3,1.8]]);reference=np.array([.4,0,.7]);params=np.array([-.8,0,0,0]);delays,valid=w.delays(params,'plane',sources,receivers,reference,343.)
assert valid.tolist()==[True,False,True]
image=sources.copy();image[:,0]*=-1
assert np.max(abs(delays-(np.linalg.norm(image-receivers,axis=1)-np.linalg.norm(sources-receivers,axis=1))/343))<1e-15
kernel=np.exp(-(w.TIME/.00007)**2);records=[dict(source=s,receiver=r,y=kernel.copy()) for s,r in zip(sources,receivers)];res,gains,align=w.residual_profiles(params,'plane',records,kernel,reference,343.)
assert np.max(abs(res))<1e-12 and gains[1,1]==0
# Independently aggregate frozen reported rows, no classification calls.
r=json.loads((S/'run-v4/results.json').read_text());aggregates={}
for group in ['reused_v3','fresh_raw_clock']:
 rows=[x for x in r['cases'] if x['group']==group];assert len(rows)==12
 aggregates[group]=dict(baseline={k:sum(x['baseline_score'][k] for x in rows) for k in ['matched_count','false_surfaces','missed_surfaces']},guarded={k:sum(x['guarded_score'][k] for x in rows) for k in ['matched_count','false_surfaces','missed_surfaces']},controls_flagged=sum(x['diagnostics']['exact_v4']['source_flag'] for x in rows if x['family'] not in ['dual_room','dual_phase']),duals_flagged=sum(x['diagnostics']['exact_v4']['source_flag'] for x in rows if x['family'] in ['dual_room','dual_phase']),classification_changes=sum(x['classification_changed'] for x in rows),raw_unchanged=all(x['raw_unchanged'] for x in rows))
 for k in ['baseline','guarded']:assert aggregates[group][k]==r['groups'][group][k]
result=dict(snapshot_sha256=m['content_sha256'],verified_manifest_files=len(m['files']),independent_gain_cases=len(cases),gain_max_abs_error=max(x['absolute_objective_error'] for x in cases),algebraic_profile_results=cases,absent_plane_primary_retained=True,absent_secondary_gain=float(gains[1,1]),geometric_delay_max_error_s=float(np.max(abs(delays-(np.linalg.norm(image-receivers,axis=1)-np.linalg.norm(sources-receivers,axis=1))/343))),aggregates=aggregates,new_classifier_fits=0,new_raw_cases=0)
expected=json.loads(Path(__file__).with_name('checks.json').read_text())
assert result==expected, 'Independent checks differ from frozen reviewer results'
args.output.parent.mkdir(parents=True,exist_ok=True)
args.output.write_text(json.dumps(result,indent=2)+'\n');print(json.dumps({k:v for k,v in result.items() if k!='algebraic_profile_results'},indent=2))
