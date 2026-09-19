from pathlib import Path
import sys,json,time,resource
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1];sys.path.insert(0,str(ROOT));sys.path.insert(0,str(HERE))
from diagnostic_v2 import diagnose
from evaluation.path_interpretations import save,sha
FILES=[HERE/'V2-DESIGN.md',HERE/'diagnostic_v2.py',HERE/'run_v2.py',HERE/'diagnostic.py']
def hashes():return {str(p.relative_to(ROOT)):sha(p) for p in FILES}
def main():
 out=HERE/'run-v2';previous=HERE/'run-v1';action=sys.argv[1]
 if action=='freeze':
  if (out/'freeze.json').exists():raise FileExistsError('Preserve freeze')
  save(out/'freeze.json',dict(hashes=hashes(),v1_freeze_sha256=sha(previous/'freeze.json'),v1_results_sha256=sha(previous/'results.json'),before_v2_fitting=True));print(hashes());return
 assert json.loads((out/'freeze.json').read_text())['hashes']==hashes()
 old=json.loads((previous/'results.json').read_text());rows=[]
 for r in old['cases']:
  folder=previous/'cases'/f"{r['family']}-{r['seed']}";data=json.loads((folder/'baseline.json').read_text());started=time.perf_counter();d=diagnose(data['result']);d['runtime_s']=time.perf_counter()-started;d['peak_rss_bytes']=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss;score=r['baseline_score'];control=r['family'] not in ['dual_room','dual_phase'];row=dict(family=r['family'],seed=r['seed'],baseline_score=score,diagnostic=d,control_retention_passed=not(control and d['source_flag']),false_surfaces_removed=score['false_surfaces'] if d['source_flag'] else 0,true_surfaces_withheld=score['matched_count'] if d['source_flag'] else 0,baseline_output_sha256=sha(folder/'baseline.json'),raw_unchanged=all(sha(folder/p)==h for p,h in json.loads((folder/'manifest.json').read_text())['recordings'].items()));rows.append(row);save(out/'partial-results.json',rows);print(r['family'],r['seed'],d['status'],d.get('held_improved_count'),d['runtime_s'],flush=True)
 save(out/'results.json',dict(cases=rows,hashes=hashes(),scope='Development-only repeated-input search comparison; no fresh held-out validation.'))
if __name__=='__main__':main()
