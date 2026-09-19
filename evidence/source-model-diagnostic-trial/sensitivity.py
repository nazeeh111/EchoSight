from pathlib import Path
import sys,json,time,copy
import numpy as np
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1];sys.path.insert(0,str(ROOT));sys.path.insert(0,str(HERE))
from diagnostic_v3 import diagnose
from evaluation.path_interpretations import save,sha
FILES=[HERE/'SENSITIVITY.md',HERE/'sensitivity.py',HERE/'diagnostic_v3.py',HERE/'waveform_v3.py']
def hashes():return {str(p.relative_to(ROOT)):sha(p) for p in FILES}
def main():
 out=HERE/'run-v3';freeze=out/'sensitivity-freeze.json'
 if sys.argv[1]=='freeze':
  if freeze.exists():raise FileExistsError('Preserve freeze')
  save(freeze,dict(hashes=hashes(),v3_results_sha256=sha(out/'results.json'),before_sensitivity=True));return
 assert json.loads(freeze.read_text())['hashes']==hashes()
 rows=[];cases=[r for r in json.loads((out/'results.json').read_text())['cases'] if r['group']=='fresh_development']
 for index,row in enumerate(cases):
  folder=out/'fresh'/f"{row['family']}-{row['seed']}";base=json.loads((folder/'baseline.json').read_text())['result'];bundle=json.loads((folder/'bundle.json').read_text());C=np.array(bundle['shared_calibration']['source_pose_joint_covariance_m2']);rng=np.random.default_rng(8101+index);records=[]
  for draw in range(8):
   source_error=rng.multivariate_normal(np.zeros(12),C).reshape(4,3);speed=343.+rng.normal(0,.6);receiver_error={f'receiver-pose-{i:02d}':rng.normal(0,.006,3) for i in range(12)};perturbed=copy.deepcopy(base)
   for j,item in enumerate(perturbed['processed_sessions']):
    item['session']['source_position_m']=(np.array(item['session']['source_position_m'])+source_error[j]).tolist()
    for o in item['observations']:o['receiver_position_m']=(np.array(o['receiver_position_m'])+receiver_error[o['receiver_pose_group_id']]).tolist()
   timed=copy.deepcopy(perturbed)
   for item in timed['processed_sessions']:
    for o in item['observations']:
     if o['status']!='ok':continue
     shift=rng.normal(0,o['direct_std_s']);scale=1+rng.normal(0,o['clock']['alpha_std']/o['clock']['alpha']);o['response']['start_delay_s']=o['response']['start_delay_s']*scale+shift;o['response']['sample_rate_hz']/=scale
   for kind,result in [('geometry_only',perturbed),('geometry_and_local_timing',timed)]:
    started=time.perf_counter();d=diagnose(result,speed);record=dict(draw=draw,kind=kind,source_flag=d['source_flag'],status=d['status'],component_held_support_counts=d.get('component_held_support_counts'),component_identifiable=d.get('component_identifiable'),waveform_flag_before_identifiability=d.get('waveform_flag_before_identifiability'),held_mse={k:v['held_mse'] for k,v in d.get('models',{}).items()},parameters=d.get('models',{}).get('secondary',{}).get('parameters'),runtime_s=time.perf_counter()-started);records.append(record)
  control=row['family'] not in ['dual_room','dual_phase'];summary=dict(family=row['family'],seed=row['seed'],nominal_source_flag=row['diagnostic']['source_flag'],control=control,source_flags_by_kind={kind:sum(r['source_flag'] for r in records if r['kind']==kind) for kind in ['geometry_only','geometry_and_local_timing']},draws=records);rows.append(summary);save(out/'sensitivity-partial.json',rows);print(row['family'],row['seed'],summary['source_flags_by_kind'],flush=True)
 save(out/'sensitivity-results.json',dict(cases=rows,hashes=hashes(),scope='Local conditional nuisance sensitivity,8paired draws per case; not empirical calibration or hardware probability.'))
if __name__=='__main__':main()
