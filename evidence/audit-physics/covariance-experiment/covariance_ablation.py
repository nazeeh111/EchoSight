"""Independent Monte Carlo check of experimental whole-repetition covariance."""
import json,time,hashlib,inspect
from pathlib import Path
import numpy as np
from scipy.signal import lfilter
from echosight.signals import generate_probe,process_recording
from echosight.timing_bootstrap import estimate


def naive(observation):
 r=observation['response'];y=np.array(r['values']);fs=r['sample_rate_hz'];direct=-r['start_delay_s']*fs
 delays=np.array([c['delay_s']*fs for c in observation['candidates']]);axis=np.arange(len(y));grid=np.arange(-round(.0008*fs),round(.0008*fs)+1)
 kernel=np.interp(direct+grid,axis,y);kernel/=max(abs(kernel));positions=np.r_[0,delays]
 A=np.array([np.interp(axis-direct-d,grid,kernel,left=0,right=0) for d in positions]).T
 amplitudes=np.linalg.lstsq(A,y,rcond=None)[0];residual=y-A@amplitudes
 D=np.array([(np.interp(axis-direct-d-.05,grid,kernel,left=0,right=0)-np.interp(axis-direct-d+.05,grid,kernel,left=0,right=0))/.1*fs for d in positions]).T*amplitudes[None,:]
 profiled=D-A@np.linalg.lstsq(A,D,rcond=None)[0]
 C=np.linalg.pinv(profiled.T@profiled,rcond=1e-12)*float(residual@residual)/max(len(y)-2*len(positions),1)
 L=np.column_stack([-np.ones(len(delays)),np.eye(len(delays))]);return L@C@L.T

rng=np.random.default_rng(20261023);x,p=generate_probe();fs=48000;t=np.arange(len(x))/fs;u=np.arange(len(x)+fs//3)/fs
rows=[];started=time.perf_counter()
function_hash=hashlib.sha256(inspect.getsource(estimate).encode()).hexdigest()
for family in ['white_fractional','colored_integer']:
 for index in range(40):
  integer=family in ('white_integer','colored_integer')
  alpha=1. if integer else 1.0003;offset=.06 if integer else .06319
  first=.012 if integer else .012013;gap=.014 if integer else .00025
  source=(u-offset)/alpha;direct=.4*np.interp(source,t,x,left=0,right=0)
  echo=.2*np.interp(source-first,t,x,left=0,right=0)+.16*np.interp(source-first-gap,t,x,left=0,right=0);y=direct+echo
  if family=='clock_jitter_overlap':
   jitter=rng.normal(0,.000015,len(p['pilot_start_samples']))
   moved=y.copy()
   for begin,shift in zip(p['pilot_start_samples'],jitter):
    a=offset+alpha*(begin/fs-.006);b=offset+alpha*(begin/fs+.14);ix=(u>=a)&(u<b)
    moved[ix]=np.interp(u[ix]-shift,u,y)
   y=moved
  noise=rng.normal(0,.02,len(y))
  if family in ('colored_fractional','colored_integer'):noise=lfilter([np.sqrt(1-.85**2)],[1,-.85],noise)
  y+=noise
  o=process_recording(y,fs,p,'r',estimator='joint_kernel')
  row=dict(family=family,index=index,status=o['status'],truth_delays_s=[first,first+gap],predicted_delays_s=[c['delay_s'] for c in o['candidates']])
  if o['status']=='ok' and len(o['candidates'])==2:
   row['bootstrap']=estimate(y,fs,p,o,process_recording,draws=31,seed=19000+index)
   row['naive_iid_hessian_covariance_s2']=naive(o).tolist()
  rows.append(row)
 summary=[]
 for fam in [family]:
  valid=[r for r in rows if r['family']==fam and r.get('bootstrap',{}).get('status')=='estimated'];pred=np.array([r['predicted_delays_s'] for r in valid]);truth=np.array([r['truth_delays_s'] for r in valid]);center=pred.mean(axis=0)
  methods={}
  for name,key in [('bootstrap_noise','noise_covariance_s2'),('bootstrap_with_declared_floor','covariance_s2'),('naive_iid','naive_iid_hessian_covariance_s2')]:
   cov=np.array([r[key] if name=='naive_iid' else r['bootstrap'][key] for r in valid]);std=np.sqrt(np.diagonal(cov,axis1=1,axis2=2));emp=np.cov(pred,rowvar=False)
   methods[name]=dict(component_95pct_coverage_about_true_delay=np.mean(abs(pred-truth)<=1.96*std,axis=0).tolist(),component_95pct_coverage_about_empirical_mean=np.mean(abs(pred-center)<=1.96*std,axis=0).tolist(),mean_predicted_covariance_s2=cov.mean(axis=0).tolist(),empirical_covariance_s2=emp.tolist(),bias_s=np.mean(pred-truth,axis=0).tolist())
  summary.append(dict(family=fam,estimated=len(valid),requested=40,methods=methods));print(json.dumps(summary[-1]),flush=True)
Path('../physics-estimator/covariance-ablation.json').write_text(json.dumps(dict(classification='Monte Carlo development simulation, not physical coverage',estimator_function_sha256=function_hash,estimator_function_unchanged=hashlib.sha256(inspect.getsource(estimate).encode()).hexdigest()==function_hash,seed=20261023,bootstrap_draws=31,repeats=7,elapsed_seconds=time.perf_counter()-started,rows=rows),indent=2)+'\n')
