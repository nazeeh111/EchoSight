"""Development comparison; generated waveform truth never supplied to either detector."""
import argparse,hashlib,importlib.util,json,time
from pathlib import Path
import numpy as np
from echosight import signals as trial
parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument("--baseline-signals",required=True)
parser.add_argument("--output",required=True)
args=parser.parse_args()
from tests.test_signals import waveform
spec=importlib.util.spec_from_file_location('baseline',args.baseline_signals)
baseline=importlib.util.module_from_spec(spec);spec.loader.exec_module(baseline)
rows=[]
for alpha in [.9951,.996,.997,.998,1.,1.002,1.003,1.004,1.0049]:
 for noise in [.0003,.003,.01]:
  y,fs,p=waveform(alpha=alpha);y=y+np.random.default_rng(617).normal(0,noise,len(y))
  row=dict(kind='affine',alpha=alpha,noise=noise)
  for name,m in [('baseline',baseline),('refined',trial)]:
   started=time.perf_counter();r=m.process_recording(y,fs,p,'r');candidates=r['candidates']
   row[name]=dict(status=r['status'],alpha=r['clock'].get('alpha'),runtime_s=time.perf_counter()-started,
     candidates=len(candidates),max_delay_error_s=max(min([abs(c['delay_s']-d) for c in candidates] or [1]) for d in [.012345,.026789]) if r['status']=='ok' else None)
  rows.append(row)
for kind in ['warp','missing','noise']:
 for i in range(10):
  if kind=='warp':y,fs,p=waveform(warp=.0002+i*.0002)
  elif kind=='missing':
   y,fs,p=waveform(alpha=.996+i*.0009);start=int((p['pilot_start_samples'][i%7]/48000+.04)*48000);y[start:start+int(.18*48000)]=0
  else:y,fs,p=waveform();y=np.random.default_rng(i).normal(0,.001+i*.002,len(y))
  row=dict(kind=kind,index=i)
  for name,m in [('baseline',baseline),('refined',trial)]:
   r=m.process_recording(y,fs,p,'r');row[name]=dict(status=r['status'],diagnostics=[d['code'] for d in r['diagnostics']])
  rows.append(row)
report=dict(evidence_class='simulation_development_not_frozen_holdout',
 baseline_signals_sha256=hashlib.sha256(Path(args.baseline_signals).read_bytes()).hexdigest(),
 current_signals_sha256=hashlib.sha256(Path(trial.__file__).read_bytes()).hexdigest(),rows=rows)
Path(args.output).parent.mkdir(parents=True,exist_ok=True)
Path(args.output).write_text(json.dumps(report,indent=2)+'\n')
for name in ['baseline','refined']:
 good=[r[name] for r in rows if r['kind']=='affine'];bad=[r[name] for r in rows if r['kind']!='affine']
 print(name,'affine accepted',sum(r['status']=='ok' for r in good),'of',len(good),'max accepted delayerror',max([r['max_delay_error_s'] for r in good if r['status']=='ok']),'invalid accepted',sum(r['status']=='ok' for r in bad),'of',len(bad))
