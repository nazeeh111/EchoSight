from pathlib import Path
import json,hashlib
import numpy as np
P=Path(__file__).resolve().parent;report=json.loads((P/'run-v4/results.json').read_text());output={}
for group in ['reused_v3','fresh_raw_clock']:
 rows=[r for r in report['cases'] if r['group']==group and 'diagnostics' in r];clock=[c for r in rows for c in r['clock_observations']];runtime=[r['diagnostics']['exact_v4']['runtime_s'] for r in rows]
 entries=[];normalizers=[]
 for r in rows:
  folder=P/('run-v3/fresh' if group=='reused_v3' else 'run-v4/fresh')/f"{r['family']}-{r['seed']}";base=json.loads((folder/'baseline.json').read_text())['result']
  for item in base['processed_sessions']:
   for o in item['observations']:
    if o['status']!='ok':continue
    v=np.array(o['response']['values']);t=o['response']['start_delay_s']+np.arange(len(v))/o['response']['sample_rate_hz'];scale=float(np.interp(0,t,v));window=abs(t)<.00025;normalizers.append(abs(scale)/max(abs(v[window])))
  d=r['diagnostics']['exact_v4'];old=r['diagnostics']['old_v3'];entries.append(dict(family=r['family'],seed=r['seed'],old_flag=old['source_flag'],new_flag=d['source_flag'],support=d.get('component_held_support_counts'),secondary_held_ratio=min(1e100,d['models']['secondary']['held_mse']/min(d['models']['single']['held_mse'],d['models']['plane']['held_mse'])) if 'models' in d else None,training_cost_changes={m:d['models'][m]['training_mse']-old['models'][m]['training_mse'] for m in d.get('models',{})},held_cost_changes={m:d['models'][m]['held_mse']-old['models'][m]['held_mse'] for m in d.get('models',{})}))
 errors=[abs(c['clock_error_ppm']) for c in clock if c['clock_error_ppm'] is not None]
 output[group]=dict(cases=len(rows),classification_changes=sum(r['classification_changed'] for r in rows),dual_flags=sum(r['diagnostics']['exact_v4']['source_flag'] for r in rows if r['family'].startswith('dual')),false_control_flags=sum(r['diagnostics']['exact_v4']['source_flag'] for r in rows if not r['family'].startswith('dual')),accepted_recordings=sum(c['status']=='ok' for c in clock),total_recordings=len(clock),clock_max_abs_rate_error_ppm=max(errors),clock_median_abs_rate_error_ppm=float(np.median(errors)),minimum_abs_zero_to_local_peak_ratio=min(normalizers),runtime_median_s=float(np.median(runtime)),runtime_max_s=max(runtime),baseline=report['groups'][group]['baseline'],guarded=report['groups'][group]['guarded'],cases_detail=entries)
output['engineering_gates_passed']=report['engineering_gates_passed'];output['failed_gates']=report['failed_gates']
manifest=json.loads((P/'review-snapshot-b5de1137125e/MANIFEST.json').read_text())
for name,digest in manifest['files'].items():assert hashlib.sha256((P/'review-snapshot-b5de1137125e'/name).read_bytes()).hexdigest()==digest
output['original_snapshot_unchanged']=True
output['original_snapshot_files_checked']=len(manifest['files'])
(P/'run-v4/summary.json').write_text(json.dumps(output,indent=2)+'\n');print(json.dumps({k:({j:x for j,x in v.items() if j!='cases_detail'} if isinstance(v,dict) else v) for k,v in output.items()},indent=2))
