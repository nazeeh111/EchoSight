"""Regenerate permitted synthetic files and verify against frozen input hashes."""
import argparse,hashlib,json
from run import ROOT,cases
from echosight.simulation import simulate_session
from echosight.storage import load_session
from evaluation.stress_simulation import simulate
p=argparse.ArgumentParser();p.add_argument('--case',help='Optional one family-seed, e.g. null-137; omit for full corpus');a=p.parse_args()
expected=json.loads((ROOT/'input-manifest.json').read_text());checks=[];done=set()
for suite,case,spec,folder,estimator in cases():
 name=f"{case.get('scenario',case.get('family'))}-{case['seed']}"
 if a.case and a.case!=name:continue
 if (suite,name) in done:continue
 done.add((suite,name));destination=ROOT/'raw'/suite/name
 if not (destination/'session.json').exists():
  if suite=='stress':simulate(destination,case['family'],case['seed'])
  else:simulate_session(destination,scenario=case['scenario'],seed=case['seed'],capture_count=case.get('capture_count',8))
 session=load_session(destination/'session.json');hashes={c['capture_id']:hashlib.sha256(__import__('pathlib').Path(c['recording_path']).read_bytes()).hexdigest() for c in session['captures']};target=next(x for x in expected if x['suite']==suite and x['case']==case)
 assert hashes==target['recordings'],f'Generated recording bytes differ: {suite}/{name}'
 checks.append(dict(suite=suite,case=name,recording_count=len(hashes),identical=True))
(ROOT/'regeneration-check.json').write_text(json.dumps(checks,indent=2)+'\n');print(checks)
