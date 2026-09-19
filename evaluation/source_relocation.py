"""Equal-input evaluation of calibrated source relocation.

The default split is development. Held-out execution requires an explicit flag
and an immutable source checkout selected by the coordinator. No truth is loaded
until all fitting methods have returned.
"""
from __future__ import annotations
import argparse
import hashlib
import importlib
import json
from pathlib import Path
import subprocess
import time
from .metrics import score_surfaces
from .source_relocation_baseline import independent_consensus
from .source_relocation_simulation import simulate


def digest_json(value):
    return hashlib.sha256(json.dumps(value,sort_keys=True,allow_nan=False).encode()).hexdigest()


def failures_for(result,metrics,runtime,family,spec):
    criteria={**spec['common'],**spec['requirements'][family]};failures=[]
    for key,observed,sense in [('maximum_false_surfaces',metrics['false_surfaces'],'max'),
        ('maximum_pipeline_runtime_seconds',runtime,'max'),('minimum_matched_surfaces',metrics['matched_count'],'min'),
        ('minimum_horizontal_surfaces',metrics['horizontal_matched'],'min'),('maximum_definitive_surfaces',metrics['predicted_count'],'max')]:
        if key in criteria and ((sense=='max' and observed>criteria[key]) or (sense=='min' and observed<criteria[key])):
            failures.append(f'{key}: observed {observed}, required {criteria[key]}')
    if 'allowed_status' in criteria and result['status'] not in criteria['allowed_status']:
        failures.append(f"status {result['status']} is outside {criteria['allowed_status']}")
    if criteria.get('require_diagnostics') and not result.get('diagnostics'):failures.append('required diagnostics absent')
    if 'require_matched_truth_id' in criteria and not any(m['truth_id']==criteria['require_matched_truth_id'] for m in metrics['matches']):
        failures.append('required finite-panel match absent')
    if criteria.get('maximum_claimed_physical_edges')==0:
        if any(s.get('physical_edges') or s.get('extent_status','unknown')!='unknown' or
            (s.get('triangles') and s.get('mesh_semantics')!='reflection_support_convex_hull_not_physical_edges')
            for s in result.get('surfaces',[])):failures.append('unsupported physical-edge/extent claim')
    return failures


def run(output, *, split='development', receiver_count=12, module='echosight.multisource'):
    core=importlib.import_module(module)
    process_scene_bundle=core.process_scene_bundle;infer_scene_bundle=core.infer_scene_bundle
    root=Path(__file__).resolve().parents[1];out=Path(output);out.mkdir(parents=True,exist_ok=True)
    specpath=Path(__file__).with_name('source_relocation_acceptance.json');spec=json.loads(specpath.read_text())
    if split=='heldout' and receiver_count!=12:raise ValueError('Frozen held-out criteria use12receiverposes; four-phone experiments are development only')
    if split=='heldout':cases=spec['cases']
    else:cases=[{'family':family,'seed':seed} for seed in spec['development_seeds'] for family in spec['requirements']]
    code=lambda:{str(p.relative_to(root)):hashlib.sha256(p.read_bytes()).hexdigest() for folder in ['echosight','evaluation'] for p in (root/folder).glob('*.py')}
    before=code();rows=[]
    for case in cases:
        folder=out/f"{case['family']}-{case['seed']}";path=simulate(folder,case['family'],case['seed'],receiver_count)
        bundle=json.loads(path.read_text());start=time.perf_counter();main=process_scene_bundle(path,method='mapper');duration=time.perf_counter()-start
        processed=main.get('processed_sessions',[])
        # Every comparator gets exactly the same extracted observations and poses.
        inputs_hash=digest_json(processed)
        methods=[('mapper',main,duration,'recording_to_result')]
        start=time.perf_counter()
        grid=infer_scene_bundle(processed,bundle,method='plane_grid') if processed else process_scene_bundle(path,method='plane_grid')
        methods.append(('plane_grid',grid,time.perf_counter()-start,'inference_only' if processed else 'recording_to_result'))
        start=time.perf_counter();baseline=independent_consensus(processed)
        methods.append(('independent_consensus',baseline,time.perf_counter()-start,'inference_only'))
        unchanged_inputs=inputs_hash==digest_json(processed)
        truth=json.loads((folder/'truth.json').read_text())
        for name,result,seconds,scope in methods:
            metrics=score_surfaces(result,truth,**spec['matching']);fails=failures_for(result,metrics,seconds,case['family'],spec)
            if not unchanged_inputs:fails.append('shared input mutated during comparison')
            (folder/f'{name}-result.json').write_text(json.dumps(result,indent=2,allow_nan=False)+'\n')
            rows.append({**case,'method':name,'status':result['status'],'runtime_seconds':seconds,'runtime_scope':scope,
                'metrics':metrics,'failures':fails,'diagnostics':result.get('diagnostics',[]),
                'shared_processed_input_sha256':inputs_hash,'shared_input_unchanged':unchanged_inputs,
                'source_count':len(bundle['sessions']),'receiver_count':receiver_count,
                'candidate_counts':[[len(o.get('candidates',[])) for o in item['observations']] for item in processed]})
            print(case['family'],case['seed'],name,result['status'],f"{metrics['matched_count']}/{metrics['truth_count']} true, {metrics['false_surfaces']} false",flush=True)
        (out/'partial.json').write_text(json.dumps(rows,indent=2,allow_nan=False)+'\n')
    unchanged=before==code()
    report={'schema_version':'1.0','split':split,'receiver_count':receiver_count,'source_unchanged_during_run':unchanged,
        'source_sha256':before,'acceptance_sha256':hashlib.sha256(specpath.read_bytes()).hexdigest(),
        'git_commit':(root/'EVALUATED_COMMIT').read_text().strip() if (root/'EVALUATED_COMMIT').exists() else subprocess.run(['git','rev-parse','HEAD'],cwd=root,capture_output=True,text=True).stdout.strip(),
        'cases':rows,'passed':unchanged and not any(r['failures'] for r in rows if r['method']=='mapper'),
        'limits':'Synthetic calibrated source relocation only. No new measured spatial validation. Frozen twelve-receiver gates unchanged; four-receiver results are development only. Alternative runtimes exclude common signal extraction.'}
    (out/'results.json').write_text(json.dumps(report,indent=2,allow_nan=False)+'\n');return report

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output',required=True)
    p.add_argument('--split',choices=['development','heldout'],default='development')
    p.add_argument('--allow-heldout',action='store_true');p.add_argument('--receiver-count',type=int,choices=[4,12],default=12)
    p.add_argument('--module',default='echosight.multisource');a=p.parse_args()
    if a.split=='heldout' and not a.allow_heldout:p.error('Held-out execution requires --allow-heldout after coordinator selects an immutable checkpoint')
    result=run(a.output,split=a.split,receiver_count=a.receiver_count,module=a.module)
    print(json.dumps({'passed':result['passed'],'split':result['split']}));raise SystemExit(0 if result['passed'] else 1)
