"""Run the separately frozen, harder recording benchmark, preserving failures."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import time
from .metrics import score_surfaces
from .stress_simulation import simulate


def run(output):
    from echosight.pipeline import process_session
    from echosight.storage import load_session
    from echosight.inference import infer_baseline,infer_first_echo
    root=Path(__file__).resolve().parents[1];out=Path(output);out.mkdir(parents=True,exist_ok=True)
    specpath=Path(__file__).with_name('stress_acceptance.json');spec=json.loads(specpath.read_text())
    code=lambda:{str(p.relative_to(root)):hashlib.sha256(p.read_bytes()).hexdigest() for folder in ['echosight','evaluation'] for p in (root/folder).glob('*.py')}
    hashes=code();rows=[]
    for case in spec['cases']:
        folder=out/f"{case['family']}-{case['seed']}";sessionpath=simulate(folder,case['family'],case['seed'])
        session=load_session(sessionpath);start=time.perf_counter();result=process_session(session);elapsed=time.perf_counter()-start
        # Only now load evaluation truth; alternatives receive observations and supplied poses only.
        truth=json.loads((folder/'truth.json').read_text());observations=result.get('observations',[])
        methods=[('mapper',result,elapsed)]
        for name,method in [('plane_grid',infer_baseline),('first_echo',infer_first_echo)]:
            start=time.perf_counter();r=method(session,observations);methods.append((name,r,time.perf_counter()-start))
        for name,r,elapsed in methods:
            score=score_surfaces(r,truth,**spec['matching']);criteria={**spec['common'],**spec['family_requirements'][case['family']]};fails=[]
            for key,observed,sense in [('maximum_false_surfaces',score['false_surfaces'],'max'),('maximum_runtime_seconds',elapsed,'max'),
                ('minimum_matched_surfaces',score['matched_count'],'min'),('minimum_horizontal_surfaces',score['horizontal_matched'],'min'),
                ('maximum_definitive_surfaces',score['predicted_count'],'max')]:
                if key in criteria and ((sense=='max' and observed>criteria[key]) or (sense=='min' and observed<criteria[key])):fails.append(f'{key}: {observed} versus {criteria[key]}')
            if criteria.get('require_diagnostics') and not r.get('diagnostics'):fails.append('required diagnostics absent')
            (folder/f'{name}-result.json').write_text(json.dumps(r,indent=2,allow_nan=False)+'\n')
            rows.append({**case,'method':name,'status':r['status'],'runtime_seconds':elapsed,'metrics':score,
                         'failures':fails,'diagnostics':r.get('diagnostics',[]),
                         'candidate_counts':[len(o.get('candidates',[])) for o in observations],
                         'rejected_captures':sum(o['status']!='ok' for o in observations)})
            print(case['family'],case['seed'],name,r['status'],f"{score['matched_count']}/{score['truth_count']} true,{score['false_surfaces']} false",flush=True)
        (out/'partial.json').write_text(json.dumps(rows,indent=2,allow_nan=False)+'\n')
    unchanged=hashes==code()
    report={'schema_version':'1.0','split':'new_frozen_forward_model_families','spec_sha256':hashlib.sha256(specpath.read_bytes()).hexdigest(),
            'git_commit':(root/'EVALUATED_COMMIT').read_text().strip() if (root/'EVALUATED_COMMIT').exists() else subprocess.run(['git','rev-parse','HEAD'],cwd=root,capture_output=True,text=True).stdout.strip(),
            'source_sha256':hashes,'source_unchanged_during_run':unchanged,'cases':rows,
            'passed':unchanged and not any(row['failures'] for row in rows if row['method']=='mapper'),
            'limits':'Synthetic image-lattice and edge-path surrogate. Not measured validation or full-wave diffraction. Competitors reuse same extracted observations, with inference-only runtime.'}
    (out/'results.json').write_text(json.dumps(report,indent=2,allow_nan=False)+'\n');return report

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--output',required=True)
    args=parser.parse_args();r=run(args.output);print(json.dumps({'passed':r['passed'],'failures':[{k:c[k] for k in ['family','seed','failures']} for c in r['cases'] if c['method']=='mapper' and c['failures']]},indent=2));raise SystemExit(0 if r['passed'] else 1)
