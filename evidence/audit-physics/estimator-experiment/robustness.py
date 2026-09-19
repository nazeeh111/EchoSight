"""New development noise/rate/jitter controls, independent of FLAIR labels."""
import importlib.util,json,time
from pathlib import Path
import numpy as np
from scipy.optimize import linear_sum_assignment
from joint_kernel import extract
spec=importlib.util.spec_from_file_location('baseline','work/physics-estimator/baseline.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
x,p=m.generate_probe();fs=p['sample_rate_hz'];t=np.arange(len(x))/fs
rng=np.random.default_rng(20261021);rows=[]
for i in range(60):
 alpha=1+rng.uniform(-.0005,.0005);gap=rng.choice([.00018,.00025,.0005]);sign=rng.choice([-1,1]);offset=rng.uniform(.04,.09)
 first=rng.uniform(.010,.016);amplitude=rng.uniform(.10,.25);noise=rng.choice([.0003,.003,.01]);u=np.arange(len(x)+fs//3)/fs
 y=.4*np.interp((u-offset)/alpha,t,x,left=0,right=0)+.2*np.interp((u-offset)/alpha-first,t,x,left=0,right=0)+sign*amplitude*np.interp((u-offset)/alpha-first-gap,t,x,left=0,right=0)+rng.normal(0,noise,len(u))
 started=time.perf_counter();o=m.process_recording(y,fs,p,'r');base_seconds=time.perf_counter()-started
 started=time.perf_counter();cs=extract(o);fit_seconds=time.perf_counter()-started
 methods={'matched':o['candidates'],'joint':cs,'joint_guard':[c for c in cs if not c['unmodeled']]};row=dict(index=i,alpha=alpha,gap=gap,sign=int(sign),amplitude=amplitude,noise=noise,methods={})
 # Truth enters scoring only after all three extraction choices finish.
 truth=np.array([first,first+gap])
 for name,candidates in methods.items():
  pred=np.array([c['delay_s'] for c in candidates]);error=abs(pred[:,None]-truth[None,:]);hits=[]
  if len(pred):
   a,b=linear_sum_assignment(np.where(error<.00005,error,1))
   hits=[float(error[j,k]) for j,k in zip(a,b) if error[j,k]<.00005]
  row['methods'][name]=dict(status=o['status'],matched=len(hits),false=len(pred)-len(hits),missed=2-len(hits),maximum_matched_error_s=max(hits) if hits else None,runtime_s=base_seconds+(fit_seconds if name!='matched' else 0))
 rows.append(row)
Path('work/physics-estimator/robustness.json').write_text(json.dumps(dict(evidence='development_simulation_not_frozen',seed=20261021,rows=rows),indent=2)+'\n')
for name in methods:
 print(name,{k:sum(r['methods'][name][k] for r in rows) for k in ['matched','false','missed','runtime_s']})
