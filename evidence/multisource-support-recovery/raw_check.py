import hashlib,importlib.util,json,sys,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];OUT=ROOT/'work/spatial-finish';sys.path.insert(0,str(ROOT))
from echosight import multisource as original
from evaluation.metrics import score_surfaces
from evaluation.source_relocation import failures_for
spec=importlib.util.spec_from_file_location('echosight.experimental_multisource',OUT/'experimental_multisource.py');exp=importlib.util.module_from_spec(spec);spec.loader.exec_module(exp)
criteria=json.loads((ROOT/'evaluation/source_relocation_acceptance.json').read_text());rows=[]
for family,seed in [('higher_order_four_sources',1129),('coordinate_frame_mismatch',1193)]:
 folder=ROOT.parent/'work/clean-checkout/work/relocation-heldout-de8442b'/f'{family}-{seed}'
 hashes={str(p.relative_to(folder)):hashlib.sha256(p.read_bytes()).hexdigest() for p in folder.rglob('*') if p.suffix in ('.wav','.json') and not p.name.endswith('result.json') and p.name!='truth.json'}
 outputs={};times={}
 for name,mod in [('original',original),('experimental',exp)]:
  t=time.perf_counter();outputs[name]=mod.process_scene_bundle(folder/'bundle.json');times[name]=time.perf_counter()-t
 truth=json.loads((folder/'truth.json').read_text());row=dict(family=family,seed=seed,input_hashes=hashes,results={})
 for name,r in outputs.items():
  metric=score_surfaces(r,truth,**criteria['matching']);row['results'][name]=dict(status=r['status'],metrics=metric,diagnostics=r['diagnostics'],recording_to_result_seconds=times[name],failures=failures_for(r,metric,times[name],family,criteria))
  (OUT/f'{family}-{seed}-{name}-raw.json').write_text(json.dumps(r,indent=2)+'\n')
 row['inputs_unchanged']=all(hashlib.sha256((folder/p).read_bytes()).hexdigest()==h for p,h in hashes.items());assert row['inputs_unchanged']
 rows.append(row);(OUT/'raw-check-results.json').write_text(json.dumps(rows,indent=2)+'\n');print(family,seed,[(n,r['metrics']['matched_count'],r['metrics']['false_surfaces'],r['status'],r['recording_to_result_seconds'],r['failures']) for n,r in row['results'].items()],flush=True)
