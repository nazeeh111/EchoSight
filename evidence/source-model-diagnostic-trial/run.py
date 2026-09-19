from pathlib import Path
import sys,json,time,subprocess,hashlib,platform,resource
import numpy as np,scipy
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1];sys.path.insert(0,str(ROOT));sys.path.insert(0,str(HERE))
from render import render,FAMILIES,SEEDS
from diagnostic import diagnose
from evaluation.path_interpretations import checkout,sha,save
from evaluation.metrics import score_surfaces
COMMIT='de8442b2dd088c036d2b92eaeaf29a1273785795'
FILES=[HERE/'DESIGN.md',HERE/'diagnostic.py',HERE/'render.py',HERE/'run.py',ROOT/'evaluation/path_interpretations.py',ROOT/'evaluation/path_interpretations_acceptance.json',ROOT/'evaluation/metrics.py']
def hashes():return {str(p.relative_to(ROOT)):sha(p) for p in FILES}
def main():
 action=sys.argv[1];out=HERE/'run-v1'
 if action=='freeze':
  if (out/'freeze.json').exists():raise FileExistsError('Freeze already exists')
  save(out/'freeze.json',dict(hashes=hashes(),commit=COMMIT,seeds=SEEDS,families=FAMILIES,python=sys.version,numpy=np.__version__,scipy=scipy.__version__,platform=platform.platform(),frozen_time=time.time(),no_cases_generated=True));print(hashes());return
 frozen=json.loads((out/'freeze.json').read_text());assert frozen['hashes']==hashes(),'Frozen source changed'
 _,core=checkout(COMMIT,out/'checkouts')
 if action=='run':
  cases=[]
  for family in FAMILIES:
   for seed in SEEDS:cases.append((family,seed,render(out/'cases'/f'{family}-{seed}',family,seed)))
  save(out/'execution-plan.json',dict(cases=[dict(family=f,seed=s,bundle=str(p.relative_to(out)),manifest_sha256=sha(p.parent/'manifest.json')) for f,s,p in cases],hashes=hashes()))
  rows=[]
  for family,seed,bundle in cases:
   folder=bundle.parent;command=[sys.executable,str(ROOT/'evaluation/path_interpretations.py'),'_worker','--checkout',str(core.resolve()),'--bundle',str(bundle.resolve()),'--method','mapper','--output',str((folder/'baseline.json').resolve())];done=subprocess.run(command,cwd=ROOT,capture_output=True,text=True,timeout=300)
   if done.returncode:raise RuntimeError(done.stderr)
   data=json.loads((folder/'baseline.json').read_text());started=time.perf_counter();d=diagnose(data['result']);d['runtime_s']=time.perf_counter()-started;d['peak_rss_bytes']=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss;save(folder/'diagnostic.json',d)
   truth=json.loads((folder/'truth.json').read_text());score=score_surfaces(data['result'],truth);control=family not in ['dual_room','dual_phase'];row=dict(family=family,seed=seed,baseline_score=score,baseline_runtime_s=data['runtime_s'],diagnostic=d,control_retention_passed=not(control and d['source_flag']),false_surfaces_removed=score['false_surfaces'] if d['source_flag'] else 0,true_surfaces_withheld=score['matched_count'] if d['source_flag'] else 0,raw_unchanged=all(sha(folder/p)==h for p,h in json.loads((folder/'manifest.json').read_text())['recordings'].items()));rows.append(row);save(out/'partial-results.json',rows);print(family,seed,score['matched_count'],score['false_surfaces'],d['status'],d.get('held_improved_count'),d['runtime_s'],flush=True)
  save(out/'results.json',dict(cases=rows,hashes=hashes(),scope='Development diagnostic only. Original frozen evaluation unchanged.'))
if __name__=='__main__':main()
