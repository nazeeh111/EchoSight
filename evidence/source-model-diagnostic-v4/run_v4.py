from pathlib import Path
import sys,json,time,subprocess,resource,copy
import numpy as np
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1];sys.path.insert(0,str(ROOT));sys.path.insert(0,str(HERE))
from diagnostic_v3 import diagnose as old_diagnose
from diagnostic_v4 import diagnose
from render_v4 import render,FAMILIES,SEEDS
from evaluation.path_interpretations import save,sha,checkout
from evaluation.metrics import score_surfaces
COMMIT='de8442b2dd088c036d2b92eaeaf29a1273785795'
FILES=[HERE/n for n in ['V4-DESIGN.md','gain_v4.py','check_v4.py','run_v4.py','diagnostic_v4.py','waveform_v4.py','render_v4.py','diagnostic_v3.py','waveform_v3.py']]+[ROOT/'evaluation/path_interpretations.py',ROOT/'evaluation/path_interpretations_acceptance.json',ROOT/'evaluation/metrics.py']
def hashes():return {str(p.relative_to(ROOT)):sha(p) for p in FILES}
def aggregate(rows,field):return {k:sum(r[field][k] for r in rows if field in r) for k in ['matched_count','false_surfaces','missed_surfaces']}
def main():
 out=HERE/'run-v4';action=sys.argv[1]
 if action=='freeze':
  if (out/'freeze.json').exists():raise FileExistsError('Preserve freeze')
  save(out/'freeze.json',dict(hashes=hashes(),core_commit=COMMIT,prior_snapshot='b5de1137125e098c6e546463abb18495585fdbcc48b2c3ed5b7fe3b2c896e417',v3_results_sha256=sha(HERE/'run-v3/results.json'),math_checks_sha256=sha(HERE/'v4-gain-checks.json'),fresh_seeds=SEEDS,before_new_generation=True,frozen_unix_time=time.time()));print('Frozen',sha(out/'freeze.json'));return
 assert json.loads((out/'freeze.json').read_text())['hashes']==hashes()
 _,core=checkout(COMMIT,out/'checkouts');cases=[]
 for f in FAMILIES:
  for s in SEEDS:cases.append((f,s,render(out/'fresh'/f'{f}-{s}',f,s),'fresh_raw_clock'))
 save(out/'execution-plan.json',dict(cases=[dict(family=f,seed=s,manifest_sha256=sha(p.parent/'manifest.json')) for f,s,p,g in cases],hashes=hashes()))
 oldrows=[r for r in json.loads((HERE/'run-v3/results.json').read_text())['cases'] if r['group']=='fresh_development']
 cases=[(r['family'],r['seed'],HERE/'run-v3/fresh'/f"{r['family']}-{r['seed']}"/'bundle.json','reused_v3') for r in oldrows]+cases;rows=[]
 for family,seed,bundle,group in cases:
  folder=bundle.parent;baseline=folder/'baseline.json';row=dict(family=family,seed=seed,group=group)
  try:
   if group=='fresh_raw_clock':
    command=[sys.executable,str(ROOT/'evaluation/path_interpretations.py'),'_worker','--checkout',str(core.resolve()),'--bundle',str(bundle.resolve()),'--method','mapper','--output',str(baseline.resolve())];done=subprocess.run(command,cwd=ROOT,capture_output=True,text=True,timeout=300)
    if done.returncode:raise RuntimeError(done.stderr)
   data=json.loads(baseline.read_text());diagnostics={}
   for label,fn in [('old_v3',old_diagnose),('exact_v4',diagnose)]:
    started=time.perf_counter();d=fn(data['result']);d['runtime_s']=time.perf_counter()-started;diagnostics[label]=d
   truth=json.loads((folder/'truth.json').read_text());score=score_surfaces(data['result'],truth);guarded=copy.deepcopy(data['result']);d=diagnostics['exact_v4']
   if d['source_flag']:guarded['surfaces']=[]
   after=score_surfaces(guarded,truth);control=family not in ['dual_room','dual_phase'];clock=[]
   for j,item in enumerate(data['result']['processed_sessions']):
    for i,o in enumerate(item['observations']):
     t=truth['sessions'][j]['captures'][i];clock.append(dict(source_index=j,capture_id=o['capture_id'],status=o['status'],diagnostics=o.get('diagnostics',[]),actual_alpha=t['alpha'],actual_offset_s=t['offset_s'],estimated_alpha=o.get('clock',{}).get('alpha'),clock_error_ppm=(o['clock']['alpha']-t['alpha'])*1e6 if o.get('clock') else None))
   row.update(baseline_score=score,guarded_score=after,diagnostics=diagnostics,baseline_runtime_s=data['runtime_s'],control_retention_passed=not(control and d['source_flag']),near_reflector_complete=family!='near_reflector' or after['matched_count']==7,clock_observations=clock,baseline_output_sha256=sha(baseline),raw_unchanged=all(sha(folder/p)==h for p,h in json.loads((folder/'manifest.json').read_text())['recordings'].items()),classification_changed=diagnostics['old_v3']['source_flag']!=d['source_flag'],accepted_recordings=sum(c['status']=='ok' for c in clock))
   print(group,family,seed,diagnostics['old_v3']['status'],'->',d['status'],score['matched_count'],score['false_surfaces'],'=>',after['matched_count'],after['false_surfaces'],after['missed_surfaces'],flush=True)
  except Exception as error:
   row['operational_error']=repr(error);print('ERROR',family,seed,repr(error),flush=True)
  rows.append(row);save(out/'partial-results.json',rows)
 fresh=[r for r in rows if r['group']=='fresh_raw_clock'];failed=[dict(family=r['family'],seed=r['seed'],reason='operational_error' if 'operational_error' in r else 'control_or_retention') for r in rows if 'operational_error' in r or not r['control_retention_passed'] or not r['near_reflector_complete']]
 benefit=any(r.get('diagnostics',{}).get('exact_v4',{}).get('source_flag') and r['baseline_score']['false_surfaces']>0 for r in fresh if r['family'] in ['dual_room','dual_phase'])
 report=dict(cases=rows,hashes=hashes(),hashes_unchanged=hashes()==json.loads((out/'freeze.json').read_text())['hashes'],engineering_gates_passed=not failed and benefit,failed_gates=failed,has_fresh_dual_false_surface_suppression=benefit,groups={g:dict(baseline=aggregate([r for r in rows if r['group']==g],'baseline_score'),guarded=aggregate([r for r in rows if r['group']==g],'guarded_score')) for g in ['reused_v3','fresh_raw_clock']},peak_process_rss_bytes=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,scope='Development-only; warning withholds all geometry, including every true surface counted as missed.')
 save(out/'results.json',report);print(json.dumps({k:v for k,v in report.items() if k not in ['cases','hashes']}),flush=True)
if __name__=='__main__':main()
