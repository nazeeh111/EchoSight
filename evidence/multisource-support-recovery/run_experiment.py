import copy,hashlib,importlib.util,json,sys,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];OUT=ROOT/'work/spatial-finish';sys.path.insert(0,str(ROOT))
from echosight import multisource as original
from evaluation.metrics import score_surfaces
from evaluation.source_relocation import failures_for
spec=importlib.util.spec_from_file_location('echosight.experimental_multisource',OUT/'experimental_multisource.py');exp=importlib.util.module_from_spec(spec);spec.loader.exec_module(exp)
freeze=json.loads((OUT/'experiment-freeze.json').read_text())
assert hashlib.sha256((OUT/'experimental_multisource.py').read_bytes()).hexdigest()==freeze['experimental_sha256']
criteria=json.loads((ROOT/'evaluation/source_relocation_acceptance.json').read_text())
data=ROOT.parent/'work/clean-checkout/work/relocation-heldout-de8442b'
cases=sorted(criteria['cases'],key=lambda c:c['seed']!=1129);reports=[]
for case in cases:
 folder=data/f"{case['family']}-{case['seed']}";saved=json.loads((folder/'mapper-result.json').read_text());bundle=json.loads((folder/'bundle.json').read_text());obs=saved['processed_sessions']
 outputs={};timings={}
 for name,module in [('original',original),('experimental',exp)]:
  value=copy.deepcopy(obs);before=json.dumps(value,sort_keys=True);start=time.perf_counter();outputs[name]=module.infer_scene_bundle(value,bundle);timings[name]=time.perf_counter()-start
  assert before==json.dumps(value,sort_keys=True)
 truth=json.loads((folder/'truth.json').read_text());row={**case,'input_sha256':hashlib.sha256((folder/'mapper-result.json').read_bytes()).hexdigest(),'bundle_sha256':hashlib.sha256((folder/'bundle.json').read_bytes()).hexdigest(),'results':{}}
 for name,result in outputs.items():
  metrics=score_surfaces(result,truth,**criteria['matching'])
  row['results'][name]={'status':result['status'],'metrics':metrics,'diagnostics':result['diagnostics'],'inference_seconds':timings[name],'failures_using_inference_only_time':failures_for(result,metrics,timings[name],case['family'],criteria)}
  (OUT/f"{case['family']}-{case['seed']}-{name}.json").write_text(json.dumps(result,indent=2)+'\n')
 reports.append(row);(OUT/'experiment-results.json').write_text(json.dumps({'freeze':freeze,'runtime_limit_not_certified':'inference-only replay excludes extraction','cases':reports},indent=2)+'\n')
 print(case['family'],case['seed'],[(name,r['metrics']['matched_count'],r['metrics']['false_surfaces'],r['status']) for name,r in row['results'].items()],flush=True)
