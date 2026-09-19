from pathlib import Path
import sys,json,numpy as np
HERE=Path(__file__).resolve().parent;sys.path.insert(0,str(HERE));from diagnostic import prepare,residual_profiles
v1=HERE/'run-v1';v2=HERE/'run-v2';out=[]
for row in json.loads((v2/'results.json').read_text())['cases']:
 if not row['diagnostic']['source_flag']:continue
 folder=v1/'cases'/f"{row['family']}-{row['seed']}";result=json.loads((folder/'baseline.json').read_text())['result'];training,held,kernel=prepare(result);d=row['diagnostic'];p=d['models']['secondary']['parameters'];reference=np.array(d['reference_m']);res,gains,align=residual_profiles(p,'secondary',training,kernel,reference,343.);by_source=[]
 for j in range(4):
  tg=[g for g,r in zip(gains,training) if r['source_index']==j];hg=[g for g,r in zip(d['models']['secondary']['held_component_gains'],held) if r['source_index']==j];by_source.append(dict(source_index=j,train_count=len(tg),train_strong=int(sum(abs(g[1])>.1 for g in tg)),held_count=len(hg),held_strong=sum(abs(g[1])>.1 for g in hg),held_secondary_gains=[g[1] for g in hg]))
 sources=np.array([se['session']['source_position_m'] for se in result['processed_sessions']]);supported=[x['source_index'] for x in by_source if x['held_strong']>=3];sv=np.linalg.svd(sources[supported]-sources[supported].mean(axis=0),compute_uv=False).tolist() if supported else []
 out.append(dict(family=row['family'],seed=row['seed'],sources=by_source,component_supported_sources=supported,centered_source_singular_values_m=sv,scope='Postfit diagnosis of frozen false flag. No gate changed. Strong amplitude is an engineering indicator, not confidence.'))
(v2/'component-support-diagnosis.json').write_text(json.dumps(out,indent=2)+'\n');print(json.dumps(out,indent=2))
