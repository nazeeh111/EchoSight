from pathlib import Path
import sys,json,time,subprocess,resource,copy
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1];sys.path.insert(0,str(ROOT));sys.path.insert(0,str(HERE))
from diagnostic_v3 import diagnose
from render_v3 import render,FAMILIES,SEEDS
from evaluation.path_interpretations import save,sha,checkout
from evaluation.metrics import score_surfaces
FILES=[HERE/n for n in ['V3-DESIGN.md','run_v3.py','diagnostic_v3.py','waveform_v3.py','render_v3.py']]+[ROOT/'evaluation/path_interpretations.py',ROOT/'evaluation/path_interpretations_acceptance.json',ROOT/'evaluation/metrics.py']
COMMIT='de8442b2dd088c036d2b92eaeaf29a1273785795'
def hashes():return {str(p.relative_to(ROOT)):sha(p) for p in FILES}
def main():
 out=HERE/'run-v3';old=HERE/'run-v1';action=sys.argv[1]
 if action=='freeze':
  if (out/'freeze.json').exists():raise FileExistsError('Preserve freeze')
  save(out/'freeze.json',dict(hashes=hashes(),old_results_sha256=sha(old/'results.json'),v2_results_sha256=sha(HERE/'run-v2/results.json'),fresh_seeds=SEEDS,before_fresh_generation=True));print(hashes());return
 assert json.loads((out/'freeze.json').read_text())['hashes']==hashes()
 _,core=checkout(COMMIT,out/'checkouts');cases=[]
 for family in FAMILIES:
  for seed in SEEDS:cases.append((family,seed,render(out/'fresh'/f'{family}-{seed}',family,seed),'fresh_development'))
 save(out/'execution-plan.json',dict(cases=[dict(family=f,seed=s,manifest_sha256=sha(p.parent/'manifest.json')) for f,s,p,g in cases],hashes=hashes()))
 cases=[(r['family'],r['seed'],old/'cases'/f"{r['family']}-{r['seed']}"/'bundle.json','reused_development') for r in json.loads((old/'results.json').read_text())['cases']]+cases;rows=[]
 for family,seed,bundle,group in cases:
  folder=bundle.parent;baseline=folder/'baseline.json'
  if group=='fresh_development':
   command=[sys.executable,str(ROOT/'evaluation/path_interpretations.py'),'_worker','--checkout',str(core.resolve()),'--bundle',str(bundle.resolve()),'--method','mapper','--output',str(baseline.resolve())];done=subprocess.run(command,cwd=ROOT,capture_output=True,text=True,timeout=300)
   if done.returncode:raise RuntimeError(done.stderr)
  data=json.loads(baseline.read_text());started=time.perf_counter();d=diagnose(data['result']);d['runtime_s']=time.perf_counter()-started;d['peak_rss_bytes']=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss;truth=json.loads((folder/'truth.json').read_text());score=score_surfaces(data['result'],truth);guarded=copy.deepcopy(data['result'])
  if d['source_flag']:guarded['surfaces']=[]
  after=score_surfaces(guarded,truth);control=family not in ['dual_room','dual_phase'];row=dict(family=family,seed=seed,group=group,baseline_score=score,guarded_score=after,diagnostic=d,control_retention_passed=not(control and d['source_flag']),near_reflector_complete=family!='near_reflector' or after['matched_count']==7,baseline_output_sha256=sha(baseline),raw_unchanged=all(sha(folder/p)==h for p,h in json.loads((folder/'manifest.json').read_text())['recordings'].items()));rows.append(row);save(out/'partial-results.json',rows);print(group,family,seed,d['status'],d.get('component_held_support_counts'),score['matched_count'],score['false_surfaces'],'->',after['matched_count'],after['false_surfaces'],after['missed_surfaces'],flush=True)
 fresh=[r for r in rows if r['group']=='fresh_development'];passed=all(r['control_retention_passed'] and r['near_reflector_complete'] for r in fresh) and any(r['diagnostic']['source_flag'] for r in fresh if r['family'] in ['dual_room','dual_phase']);save(out/'results.json',dict(cases=rows,hashes=hashes(),fresh_engineering_criteria_passed=passed,scope='Development-only conditional source qualification; all withheld true geometry scored as missed.'))
if __name__=='__main__':main()
