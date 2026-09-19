"""Isolated development study. No measured labels enter extraction."""
import hashlib,importlib.util,json,time
from pathlib import Path
import numpy as np
from scipy.signal import butter,sosfilt
from scipy.optimize import linear_sum_assignment
base=Path('work/physics-estimator/baseline.py').read_text()

def load(label,code):
 p=Path('work/physics-estimator')/(label+'.py');p.write_text(code)
 spec=importlib.util.spec_from_file_location(label,p);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m

helper='''
def _deconvolve(segment,pulse,regularization):
    from scipy.fft import rfft,irfft,next_fast_len
    n=next_fast_len(len(segment)+len(pulse)-1)
    X=rfft(pulse,n);Y=rfft(segment,n);power=abs(X)**2
    denominator=power+regularization*power.max()
    kernel=irfft(power/denominator,n)
    out=irfft(Y*X.conj()/denominator,n)/kernel[0]
    return out[:len(segment)-len(pulse)+1]
'''
methods={'matched':load('matched',base)}
for reg in [.1,.01,.001]:
 code=base.replace('def process_recording(',helper+'\ndef process_recording(').replace("correlate(segment,pulse,mode='valid',method='fft')/energy",f'_deconvolve(segment,pulse,{reg})')
 methods['deconv'+str(reg)]=load('deconv'+str(reg),code)
methods={'matched':methods['matched'],'joint':methods['matched']}
x,p=methods['matched'].generate_probe();fs=p['sample_rate_hz'];t=np.arange(len(x))/fs;u=np.arange(len(x)+fs//3)/fs
rows=[]
for gap in [.00015,.0002,.00025,.0003,.0004,.0005,.001]:
 for sign in [1,-1]:
  for amplitude in [.08,.16,.24]:
   y=.4*np.interp(u-.06,t,x,left=0,right=0)+.2*np.interp(u-.072,t,x,left=0,right=0)+sign*amplitude*np.interp(u-.072-gap,t,x,left=0,right=0)
   rows.append(('overlap',dict(gap=gap,sign=sign,amplitude=amplitude),y,[.012,.012+gap]))
for cutoff in [3000,4000,6000,10000]:
 for common in [True,False]:
  z=sosfilt(butter(4,cutoff,fs=fs,output='sos'),x)
  y=.4*np.interp(u-.06,t,z if common else x,left=0,right=0)+.2*np.interp(u-.072,t,z,left=0,right=0)
  rows.append(('coloration',dict(cutoff=cutoff,common=common),y,[.012]))
for kind,y in [('direct_only',.4*np.interp(u-.06,t,x,left=0,right=0)),('noise',np.random.default_rng(308).normal(0,.01,len(u)))]:
 rows.append((kind,{},y,[]))
from joint_kernel import extract
report=[]
for kind,config,y,truth in rows:
 r=dict(kind=kind,config=config,truth_for_evaluation_only=truth,methods={})
 for name,m in methods.items():
  started=time.perf_counter();out=m.process_recording(y,fs,p,'development');predicted=np.array([c['delay_s'] for c in (extract(out) if name=='joint' else out['candidates'])]);trutharr=np.array(truth)
  errors=abs(predicted[:,None]-trutharr[None,:]);hits=[]
  if len(predicted) and len(trutharr):
   a,b=linear_sum_assignment(np.where(errors<=.00005,errors,1.))
   hits=[float(errors[i,j]) for i,j in zip(a,b) if errors[i,j]<=.00005]
  r['methods'][name]=dict(status=out['status'],predictions=predicted.tolist(),matched=len(hits),false=len(predicted)-len(hits),missed=len(truth)-len(hits),errors_s=hits,runtime_s=time.perf_counter()-started)
 report.append(r)
output=dict(kind='development_equal_waveforms_50us_matching',baseline_sha256=hashlib.sha256(base.encode()).hexdigest(),rows=report)
Path('work/physics-estimator/joint-development.json').write_text(json.dumps(output,indent=2)+'\n')
for name in methods:
 for kind in ['overlap','coloration','direct_only','noise']:
  rr=[r['methods'][name] for r in report if r['kind']==kind]
  print(name,kind,{k:sum(r[k] for r in rr) for k in ['matched','false','missed']})
