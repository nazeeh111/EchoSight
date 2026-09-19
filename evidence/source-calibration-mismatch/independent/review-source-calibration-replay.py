"""Reprocess three existing cases using only the pinned runtime; no new raw data."""
from pathlib import Path
import json,sys,numpy as np
ROOT=Path(__file__).resolve().parents[1];P=ROOT/'work/source-calibration-mismatch';sys.path.insert(0,str(P/'core'))
from echosight.calibration import calibrate_reference
rows=[]
for name in ['single-2833-x','dual_opposite_phase-2821-x','dual_opposite_phase-2821-y']:
 folder=P/'run-v2/raw'/name;reference=json.loads((folder/'reference.json').read_text());saved=json.loads((folder/'calibration.json').read_text());actual=calibrate_reference(folder/'session.json',reference)
 assert actual['status']==saved['status'];assert actual['diagnostics']==saved['diagnostics'];assert actual['input_result_id']==saved['input_result_id']
 if 'calibration' in actual:
  for key in ['source_position_m','effective_speed_m_s','source_effective_speed_covariance']:assert np.allclose(actual['calibration'][key],saved['calibration'][key],rtol=1e-10,atol=1e-12)
  for key in ['training_normalized_rms','validation_normalized_rms','validation_fitted_rms_s','validation_max_abs_residual_s']:assert abs(actual[key]-saved[key])<1e-12
 transfer=None
 if name=='single-2833-x':
  yfolder=folder.with_name('single-2833-y');ys=json.loads((yfolder/'session.json').read_text());yo=json.loads((yfolder/'observations.json').read_text())['observations'];normal=np.array([0.,1.,0.]);nominal=np.array(ys['source_position_m']);nominal_image=nominal-2*(normal@nominal)*normal;estimated=np.array(actual['calibration']['source_position_m']);image=estimated-2*(normal@estimated)*normal;errors=[]
  for capture,o in zip(ys['captures'],yo):
   r=np.array(capture['receiver_position_m']);length=np.linalg.norm(r-nominal_image)-np.linalg.norm(r-nominal);eligible=[c for c in o['candidates'] if max(0,(length-.3)/380)<=c['delay_s']<=(length+.3)/300];assert o['status']=='ok' and len(eligible)==1
   errors.append(float((np.linalg.norm(r-image)-np.linalg.norm(r-estimated))/actual['calibration']['effective_speed_m_s']-eligible[0]['delay_s']))
  rms=float(np.sqrt(np.mean(np.square(errors))));maximum=max(abs(x) for x in errors);assert rms>.0001 and maximum>.0002
  transfer=dict(status='unique_reference_transfer',residuals_s=errors,rms_s=rms,max_abs_s=maximum,passes_existing_absolute_gates=False,scope='Fresh prediction from replayed x proposal using unchanged y-reference candidate rule; valid-control failure retained.')
 rows.append(dict(fresh_transfer_failure=transfer,case=name,status=actual['status'],input_result_id=actual['input_result_id'],diagnostics=actual['diagnostics'],validation_rms_s=actual.get('validation_fitted_rms_s'),calibration=actual.get('calibration')))
 print(name,actual['status'],flush=True)
(ROOT/'work/review-source-calibration-replay.json').write_text(json.dumps(rows,indent=2)+'\n')
