"""Run frozen import-to-geometry evaluation, including failures.

python -m evaluation.run --output work/evaluation
Use --development for seeds 1..5; this does not execute held-out seeds.
"""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path
import platform
import subprocess
import time
import numpy as np
import scipy
from .metrics import score_surfaces, acceptance_failures


def run(output_dir, development=False):
    from echosight.simulation import simulate_session
    from echosight.pipeline import process_session
    from echosight.storage import load_session
    from echosight.inference import infer_baseline, infer_first_echo
    root=Path(__file__).resolve().parents[1]
    acceptance_path=Path(__file__).with_name('acceptance.json')
    acceptance=json.loads(acceptance_path.read_text())
    output=Path(output_dir); output.mkdir(parents=True,exist_ok=True)
    cases=acceptance['held_out_cases']
    if development:
        cases=[{'scenario':s,'seed':1,'required':s!='reflector'} for s in ['room','partial','coplanar','null','clutter','mismatch','reflector','warp']]
    rows=[]
    for case in cases:
        case_dir=output/f"{case['scenario']}-{case['seed']}"
        path=simulate_session(case_dir, scenario=case['scenario'], seed=case['seed'])
        start=time.perf_counter()
        result=process_session(path)
        elapsed=time.perf_counter()-start
        # Ground truth is loaded AFTER acoustic processing and never sent to fit.
        truth=json.loads((case_dir/'truth.json').read_text())
        session=load_session(path)
        methods=[('mapper',result,elapsed)]
        observations=result.get('observations',[])
        for name,method in [('first_echo',infer_first_echo),('plane_grid',infer_baseline)]:
            start=time.perf_counter()
            alternative=method(session,observations)
            methods.append((name,alternative,time.perf_counter()-start))
        for name,method_result,runtime in methods:
            metrics=score_surfaces(method_result,truth,**{k:v for k,v in acceptance['matching'].items() if k!='one_to_one'})
            failures=acceptance_failures(case['scenario'],method_result,metrics,runtime,acceptance)
            row={**case,'method':name,'status':method_result['status'],'runtime_seconds':runtime,
                 'metrics':metrics,'acceptance_failures':failures,
                 'diagnostics':method_result.get('diagnostics',[])}
            rows.append(row)
            (case_dir/f'{name}-result.json').write_text(json.dumps(method_result,indent=2,allow_nan=False)+'\n')
            print(f"{case['scenario']} seed={case['seed']} {name}: {metrics['matched_count']}/{metrics['truth_count']} matched, {metrics['false_surfaces']} false, {runtime:.3f}s",flush=True)
        # Crash-safe incremental summary; no failed case is dropped.
        (output/'partial-results.json').write_text(json.dumps(rows,indent=2,allow_nan=False)+'\n')
    aggregate={}
    for name in ['mapper','first_echo','plane_grid']:
        subset=[r for r in rows if r['method']==name]
        room=[r for r in subset if r['scenario']=='room']
        matches=[m for r in subset for m in r['metrics']['matches']]
        covered=[m['offset_95pct_covered'] for m in matches if m['offset_95pct_covered'] is not None]
        aggregate[name]={'matched':sum(r['metrics']['matched_count'] for r in subset),
                         'false':sum(r['metrics']['false_surfaces'] for r in subset),
                         'missed':sum(r['metrics']['missed_surfaces'] for r in subset),
                         'room_matches':sum(r['metrics']['matched_count'] for r in room),
                         'runtime_seconds':sum(r['runtime_seconds'] for r in subset),
                         'offset_95pct_coverage_count':sum(covered),
                         'offset_95pct_coverage_denominator':len(covered),
                         'maximum_offset_error_m':max([m['offset_error_m'] for m in matches],default=None),
                         'maximum_normal_error_deg':max([m['normal_error_deg'] for m in matches],default=None)}
    failures=[{'scenario':r['scenario'],'seed':r['seed'],'failures':r['acceptance_failures']} for r in rows
              if r['method']=='mapper' and r['required'] and r['acceptance_failures']]
    if not development and aggregate['mapper']['room_matches']<=aggregate['first_echo']['room_matches']:
        failures.append({'comparison':'mapper room recall must exceed simple first-echo baseline'})
    commit=subprocess.run(['git','rev-parse','HEAD'],cwd=root,capture_output=True,text=True).stdout.strip() or 'uncommitted'
    hashes={str(p.relative_to(root)):hashlib.sha256(p.read_bytes()).hexdigest() for folder in ['echosight','evaluation'] for p in sorted((root/folder).glob('*.py'))}
    report={'schema_version':'1.0','split':'development' if development else 'frozen_held_out',
            'acceptance_sha256':hashlib.sha256(acceptance_path.read_bytes()).hexdigest(),
            'git_commit':commit,'source_sha256':hashes,
            'versions':{'python':platform.python_version(),'numpy':np.__version__,'scipy':scipy.__version__},
            'claims':'Synthetic software evaluation. Not physical-device validation. Alternative inference timings exclude shared waveform extraction; mapper timing includes it.',
            'aggregate':aggregate,'cases':rows,'required_failures':failures,'passed':not failures}
    (output/'results.json').write_text(json.dumps(report,indent=2,allow_nan=False)+'\n')
    return report


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',required=True)
    parser.add_argument('--development',action='store_true')
    args=parser.parse_args()
    result=run(args.output,args.development)
    print(json.dumps({'passed':result['passed'],'aggregate':result['aggregate'],'required_failures':result['required_failures']},indent=2))
    raise SystemExit(0 if result['passed'] else 1)

if __name__=='__main__':main()
