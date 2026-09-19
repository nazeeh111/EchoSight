from pathlib import Path
import copy,hashlib,importlib.util,json,sys,time
import argparse
parser=argparse.ArgumentParser();parser.add_argument('--repo',required=True);parser.add_argument('--output',required=True);args=parser.parse_args()
PACKAGE=Path(__file__).resolve().parent;ROOT=Path(args.repo).resolve();OUT=Path(args.output).resolve();OUT.mkdir(parents=True,exist_ok=False);sys.path.insert(0,str(ROOT))
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def save(p,x):p.write_text(json.dumps(x,indent=2,allow_nan=False)+'\n')
def load(p):return json.loads(p.read_text())
original=PACKAGE/'original.py';candidate=PACKAGE/'candidate.py'
assert sha(original)=='55e060183836b11b9976fe0f2187c3b97101687ff34d35d65c6319489e66f6aa'
assert sha(candidate)=='b61f4742927c8270a5133526bddbff5080b806242f6ff2e08310bc9499622085'
cases=[]
for folder in sorted((ROOT/'work/source-model-diagnostic/run-v4/fresh').iterdir()):
 if (folder/'baseline.json').exists():cases.append(dict(name=folder.name,kind='synthetic',saved=folder/'baseline.json',bundle=folder/'bundle.json',truth=folder/'truth.json'))
assert len(cases)==12
for name in ['joint_mapper','shuffled_geometry','null']:
 cases.append(dict(name='measured-'+name,kind='measured',saved=ROOT/f'work/measured-multisource/results/{name}.json',bundle=ROOT/('work/measured-multisource/null-bundle.json' if name=='null' else 'work/measured-multisource/bundle.json'),truth=ROOT/'work/measured-multisource/protocol.json'))
inputhash={str(p):sha(p) for c in cases for p in [c['saved'],c['bundle'],c['truth']]};codehash={str(p):sha(p) for p in (ROOT/'echosight').glob('*.py')}
freeze=dict(original=sha(original),candidate=sha(candidate),cases=[dict(name=c['name'],kind=c['kind']) for c in cases],inputhash=inputhash,codehash=codehash,scope='15 prespecified retained processed-observation comparisons; no raw generation or parameter changes; geometry truth after both fits.')
assert not (OUT/'freeze.json').exists();save(OUT/'freeze.json',freeze)
modules={}
for name,p in [('original',original),('candidate',candidate)]:
 dest=OUT/f'{name}.py';dest.write_bytes(p.read_bytes());spec=importlib.util.spec_from_file_location('echosight.review_'+name,dest);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);modules[name]=m
from evaluation.metrics import score_surfaces
rows=[]
for case in cases:
 saved=load(case['saved']);saved=saved['result'] if case['kind']=='synthetic' else saved;obs=saved['processed_sessions'];bundle=load(case['bundle']);before=json.dumps(obs,sort_keys=True);outputs={};timings={}
 for name,module in modules.items():
  data=copy.deepcopy(obs);start=time.perf_counter();outputs[name]=module.infer_scene_bundle(data,bundle);timings[name]=time.perf_counter()-start;assert json.dumps(data,sort_keys=True)==before
 # Evaluation truth not decoded until both estimators returned.
 truth=load(case['truth'])
 if case['kind']=='measured':
  import numpy as np
  truth={'surfaces':[dict(surface_id=f'wall-{a}-{s}',normal=np.eye(3)[a].tolist(),offset_m=s*size) for a,size in enumerate([5.705,5.965,2.355]) for s in [0,1]]}
 row=dict(name=case['name'],kind=case['kind'],methods={})
 for name,result in outputs.items():
  row['methods'][name]=dict(status=result['status'],metrics=score_surfaces(result,truth),diagnostics=result['diagnostics'],seconds=timings[name])
  save(OUT/f"{case['name']}-{name}-geometry.json",{k:v for k,v in result.items() if k!='processed_sessions'})
 # Identity equality compares geometry excluding execution time and pruning-only diagnostics.
 aa=outputs['original']['surfaces'];bb=outputs['candidate']['surfaces'];row['surface_outputs_exactly_equal']=aa==bb
 rows.append(row);save(OUT/'results.json',dict(freeze_sha256=sha(OUT/'freeze.json'),cases=rows,scope='Inference-only. No raw pipeline runtime qualification.'))
 print(case['name'],[(name,v['metrics']['matched_count'],v['metrics']['false_surfaces'],v['status']) for name,v in row['methods'].items()],flush=True)
assert all(sha(Path(p))==v for p,v in inputhash.items());assert all(sha(Path(p))==v for p,v in codehash.items())
save(OUT/'completed.json',dict(inputhashes_unchanged=True,codehashes_unchanged=True,case_count=len(rows),new_false_cases=[r['name'] for r in rows if r['methods']['candidate']['metrics']['false_surfaces']>r['methods']['original']['metrics']['false_surfaces']],lost_true_cases=[r['name'] for r in rows if r['methods']['candidate']['metrics']['matched_count']<r['methods']['original']['metrics']['matched_count']],all_surfaces_equal=all(r['surface_outputs_exactly_equal'] for r in rows)))
