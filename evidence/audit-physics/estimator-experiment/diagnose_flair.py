"""Post-development estimator diagnostic; independent laser labels are scoring-only."""
import copy,hashlib,json,sys,time
from pathlib import Path
import numpy as np
from scipy.signal import find_peaks,hilbert
sys.path.insert(0,str(Path('work/audit-baseline').resolve()))
from echosight.inference import infer_scene
from evaluation.metrics import score_surfaces
from joint_kernel import extract
root=Path('work/audit-flair-baseline');baseline=json.loads((root/'mapper-result.json').read_text());session=json.loads((root/'session.json').read_text())
data=np.load('work/audit-data/flair-subset/subset.npz',allow_pickle=False)
fs=float(data['fs'].ravel()[0]);v=float(data['c'].ravel()[0]);source=np.asarray(session['source_position_m'])
methods={'matched':copy.deepcopy(baseline['observations']),'joint':copy.deepcopy(baseline['observations']),'raw_rir_diagnostic':copy.deepcopy(baseline['observations'])}
for i,o in enumerate(methods['joint']):
 o['candidates']=extract(o)
 for j,c in enumerate(o['candidates']):c.update(candidate_id=f"{o['capture_id']}:joint:{j}",delay_std_s=max(.5/fs,.5/13000))
for i,o in enumerate(methods['raw_rir_diagnostic']):
 h=data['rirs'][:,i];e=abs(hilbert(h));direct=o['direct_arrival_receiver_s']-.1
 peaks,_=find_peaks(e,height=max(e)*.07,prominence=max(e)*.07*.65,distance=round(.00035*fs))
 peaks=sorted([j for j in peaks if .00035<=j/fs-direct<=.08],key=lambda j:-e[j])[:18]
 o['candidates']=[dict(delay_s=float(j/fs-direct),delay_std_s=max(.5/fs,.5/13000),amplitude=float(e[j]/max(e)),candidate_id=f"{o['capture_id']}:raw:{k}") for k,j in enumerate(peaks)]
# All extraction is complete before opening laser annotations.
truth=json.loads((root/'truth-laser.json').read_text());rows=[]
for name,observations in methods.items():
 planes=[]
 for plane in truth['surfaces']:
  n=np.array(plane['normal']);d=plane['offset_m'];q=source+2*(d-source@n)*n;residuals=[]
  for o in observations:
   r=np.array(o['receiver_position_m']);pred=(np.linalg.norm(r-q)-np.linalg.norm(r-source))/v
   delta=np.array([c['delay_s'] for c in o['candidates']]);residuals.append(float(min(abs(delta-pred))*v) if len(delta) else None)
  valid=[r for r in residuals if r is not None]
  planes.append(dict(surface_id=plane['surface_id'],normal=n.tolist(),offset_m=d,within25mm=sum(r<=.025 for r in valid),median_nearest_path_error_m=float(np.median(valid)),path_errors_m=residuals))
 started=time.perf_counter();fit=infer_scene(session,observations);elapsed=time.perf_counter()-started
 rows.append(dict(method=name,plane_diagnostics=planes,geometry_metrics=score_surfaces(fit,truth),runtime_s=elapsed,fit_status=fit['status'],fit_diagnostics=fit['diagnostics']))
 Path('work/physics-estimator/'+name+'-flair-result.json').write_text(json.dumps(fit,indent=2)+'\n')
report=dict(evidence='post_development_measured_RIR_hybrid_diagnostic_not_new_blind_test',fitting_geometry_truth_input=False,
  baseline_commit=(Path('work/audit-baseline')/'EVALUATED_COMMIT').read_text().strip(),
  joint_estimator_sha256=hashlib.sha256(Path('work/physics-estimator/joint_kernel.py').read_bytes()).hexdigest(),
  limits=['raw_RIR comparator has access to original broadband measurement: diagnostic, not equal-input alternative',
          'joint timing covariance and repetition support not yet qualified; outputs experimental only'],rows=rows)
Path('work/physics-estimator/flair-diagnostic.json').write_text(json.dumps(report,indent=2)+'\n')
for r in rows:
 print(r['method'],r['geometry_metrics']['matched_count'],r['geometry_metrics']['false_surfaces'],[(p['surface_id'],p['within25mm'],round(p['median_nearest_path_error_m'],3)) for p in r['plane_diagnostics']])
