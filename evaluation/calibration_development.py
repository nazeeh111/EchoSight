"""Reproduce the empirical source calibration development experiment."""
from pathlib import Path
import argparse
import json, numpy as np
from scipy.io.wavfile import write
from echosight.signals import generate_probe,process_recording
from echosight.storage import read_recording
rng=np.random.default_rng(81)
source=np.array([1.5,0.,1.3]);actual=source+[.07,-.04,.02];speed=346.
receivers=rng.uniform([.5,-3.,.4],[4.,3.,2.7],(20,3));normal=np.array([1.,0.,0.]);offset=0.
x,p=generate_probe();fs=p['sample_rate_hz'];xt=np.arange(len(x))/fs
parser=argparse.ArgumentParser(description='Development source calibration from raw PCM; not held-out or hardware validation.');parser.add_argument('--output',required=True);args=parser.parse_args()
output=Path(args.output);root=output/'recordings';root.mkdir(parents=True,exist_ok=True)
ydata=[];diagnostics=[]
for i,r in enumerate(receivers):
 image=actual-2*actual[0]*normal
 alpha=1+rng.uniform(-300,300)*1e-6;start=rng.uniform(.04,.10)
 t=np.arange(round((len(x)/fs+.2)*fs))/fs
 corrected=(t-start)/alpha
 y=.55*np.interp(corrected-np.linalg.norm(r-actual)/speed,xt,x,left=0,right=0)+.2*np.interp(corrected-np.linalg.norm(r-image)/speed,xt,x,left=0,right=0)+rng.normal(0,.00015,len(t))
 file=root/f'{i:02d}.wav';write(file,fs,np.round(y*32767).astype(np.int16))
 samples,rate=read_recording(file);o=process_recording(samples,rate,p,str(i))
 if o['status']!='ok' or len(o['candidates'])!=1:raise RuntimeError((i,o['status'],o['candidates']))
 ydata.append(o['candidates'][0]['delay_s']);diagnostics.append(o)

from echosight.calibration import calibrate_reference
train=[str(i) for i in range(16)];held=[str(i) for i in range(16,20)]
session=dict(schema_version='1.0',session_id='source-reference-development',source_position_m=source.tolist(),source_position_std_m=.01,probe=p,captures=[dict(capture_id=str(i),receiver_position_m=r.tolist(),receiver_position_std_m=.003,recording_path=f'recordings/{i:02d}.wav',provenance='simulated') for i,r in enumerate(receivers)])
reference=dict(normal=normal.tolist(),offset_m=0.,offset_std_m=.003,normal_std_rad=.0005,training_capture_ids=train,validation_capture_ids=held)
(output/'session.json').write_text(json.dumps(session,indent=2)+'\n')
(output/'reference.json').write_text(json.dumps(reference,indent=2)+'\n')
(output/'truth.json').write_text(json.dumps({'source_position_m':actual.tolist(),'effective_speed_m_s':speed,'use':'evaluation only; not fitting input'},indent=2)+'\n')
out=calibrate_reference(output/'session.json',reference)
(output/'calibration.json').write_text(json.dumps(out,indent=2)+'\n')
report={'evidence':'development simulation from raw PCM, independently held-out positions within development; not new blind evaluation or hardware validation','status':out['status'],'physical_validation':False,'source_error_m':float(np.linalg.norm(np.array(out['calibration']['source_position_m'])-actual)) if out['status']=='calibration_proposal' else None,'validation_nominal_rms_s':out.get('validation_nominal_rms_s'),'validation_fitted_rms_s':out.get('validation_fitted_rms_s'),'provenance':out.get('provenance')}
(output/'results.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report,indent=2))
raise SystemExit(0 if out['status']=='calibration_proposal' else 1)
