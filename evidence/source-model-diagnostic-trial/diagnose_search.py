from pathlib import Path
import sys,json,numpy as np
HERE=Path(__file__).resolve().parent;sys.path.insert(0,str(HERE));from diagnostic import prepare,residual_profiles
out=HERE/'run-v1';rows=[]
for family in ['dual_room','dual_phase']:
 for seed in [2401,2411]:
  folder=out/'cases'/f'{family}-{seed}';result=json.loads((folder/'baseline.json').read_text())['result'];truth=json.loads((folder/'truth.json').read_text());d=json.loads((folder/'diagnostic.json').read_text());prepared=prepare(result)
  if prepared is None:continue
  training,held,kernel=prepared;reference=np.mean([r['source'] for r in training],axis=0);parameters=np.r_[truth['secondary_offset_m'],truth['driver_delay_s']/1e-4];train_res,_,_=residual_profiles(parameters,'secondary',training,kernel,reference,343.);held_res,_,_=residual_profiles(parameters,'secondary',held,kernel,reference,343.);rows.append(dict(family=family,seed=seed,fitted_parameters=d['models']['secondary']['parameters'],truth_parameters_evaluation_only=parameters.tolist(),executed_train_mse=d['models']['secondary']['training_mse'],executed_held_mse=d['models']['secondary']['held_mse'],oracle_fixed_truth_train_mse=float(np.mean(train_res**2)),oracle_fixed_truth_held_mse=float(np.mean(held_res**2)),single_held_mse=d['models']['single']['held_mse'],scope='Truth-parameter cost is diagnostic upper-bound evidence only. It does not count as fitted recovery or validated source qualification.'))
(out/'search-diagnosis.json').write_text(json.dumps(rows,indent=2)+'\n');print(json.dumps(rows,indent=2))
