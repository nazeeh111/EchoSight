from pathlib import Path
import json,hashlib,sys,importlib.util,difflib,time
import numpy as np
from scipy.optimize import linear_sum_assignment
root=Path(__file__).resolve().parent.parent;p=root/'work/clock-refinement';raw=json.loads((p/'run-v1/results.json').read_text());rows=raw['rows'];freeze=json.loads((p/'run-v1/freeze.json').read_text())
for rel,sha in freeze['hashes'].items():assert hashlib.sha256((root/rel).read_bytes()).hexdigest()==sha
assert raw['hashes']==freeze['hashes']
sys.path.insert(0,str(p));spec=importlib.util.spec_from_file_location('independent_clock_runner',p/'runner.py');runner=importlib.util.module_from_spec(spec);spec.loader.exec_module(runner)
assert hashlib.sha256(runner.changed.encode()).hexdigest()==freeze['candidate_source_sha256']==raw['candidate_source_sha256']
(root/'work/clock-refinement-independent-candidate.diff').write_text(''.join(difflib.unified_diff(runner.source.splitlines(keepends=True),runner.changed.splitlines(keepends=True),fromfile='frozen_baseline_signals.py',tofile='frozen_candidate_signals.py')))
def valid(r):return r['truth']['affine'] and not r['truth']['weak_direct']
def ok(r,side):return r[side]['status']=='ok'
def key(r):return [r['cohort'],r['key'],r.get('source_index'),r.get('capture_id')]
def counts(r,side):
    truth=np.array(r['truth']['path_delays_s']);truth=truth-truth.min();truth=truth[(truth>1e-12)&(truth<=.08)];pred=np.array([x['delay_s'] for x in r[side]['candidates']]);matched=0
    if len(truth) and len(pred):
        distance=abs(pred[:,None]-truth);i,j=linear_sum_assignment(np.where(distance<=75e-6,distance,100));matched=sum(distance[a,b]<=75e-6 for a,b in zip(i,j))
    return int(len(pred)-matched),int(len(truth)-matched)
for r in rows:
    for side in ('original','candidate'):
        false,miss=counts(r,side);assert [false,miss]==[r[side]['false_candidates'],r[side]['missed_paths']]
        if r['truth']['affine'] and r[side]['clock']:
            clock=r[side]['clock'];error=(clock['alpha']-r['truth']['alpha'])*1e6
            assert abs(error-r[side]['rate_error_ppm'])<1e-9
            assert abs(error/clock['alpha_std']/1e6-r[side]['rate_standardized_error'])<1e-8
common=[r for r in rows if valid(r) and ok(r,'original') and ok(r,'candidate')]
changed=[r for r in common if r['original']['clock']!=r['candidate']['clock']]
negatives=[r for r in rows if r['truth']['weak_direct'] or not r['truth']['affine']]
missworse=[r for r in common if counts(r,'candidate')[1]>counts(r,'original')[1]]
falseworse=[r for r in common if counts(r,'candidate')[0]>counts(r,'original')[0]]
rateworse=[r for r in changed if abs(r['candidate']['rate_error_ppm'])>abs(r['original']['rate_error_ppm'])]
selected=[]
for r in rows:
    if r in missworse or r in falseworse or r in negatives or (valid(r) and ok(r,'original') and abs(r['original'].get('rate_error_ppm',0))>50):selected.append(r)
worst=max(common,key=lambda r:abs(r['candidate']['rate_standardized_error']));
if worst not in selected:selected.append(worst)
# Re-execute baseline/candidate from original bytes on consequential cases, not just report arithmetic.
for r in selected:
    if r['cohort']=='targeted':
        entry=next(x for x in json.loads((p/'run-v1/raw/manifest.json').read_text()) if x['case_id']==r['key']);path=p/'run-v1/raw'/entry['recording_path'];probe=entry['probe'];cid=r['key']
    else:
        folder=root/'work/source-model-diagnostic'/r['cohort']/'fresh'/r['key'];bundle=json.loads((folder/'bundle.json').read_text());sp=folder/bundle['sessions'][r['source_index']];session=json.loads(sp.read_text());capture=next(x for x in session['captures'] if x['capture_id']==r['capture_id']);path=sp.parent/capture['recording_path'];probe=session['probe'];cid=r['capture_id']
    assert hashlib.sha256(path.read_bytes()).hexdigest()==r['raw_sha256']
    samples,rate=runner.read_recording(path)
    for side,fn in [('original',runner.process_recording),('candidate',runner.module.process_recording)]:
        result=fn(samples,rate,probe,cid)
        for field in ['status','clock','candidates','diagnostics']:assert result.get(field)==r[side].get(field),(key(r),side,field)
summary={'records':len(rows),'common_accepted_valid_affine':len(common),'changed_common_accepted_clocks':len(changed),'hashes_verified':True,'candidate_source_sha256':raw['candidate_source_sha256'],'raw_records_independently_reexecuted':len(selected),'large_accepted_affine_rate_errors':{side:sum(valid(r) and ok(r,side) and abs(r[side].get('rate_error_ppm',0))>50 for r in rows) for side in ['original','candidate']},'null_false_candidates':{side:sum(r[side]['false_candidates'] for r in rows if r['truth']['family']=='direct_null' and ok(r,side)) for side in ['original','candidate']},'common_false_and_missed':{side:[sum(counts(r,side)[i] for r in common) for i in [0,1]] for side in ['original','candidate']},'lost_valid_admission':[key(r) for r in rows if valid(r) and ok(r,'original') and not ok(r,'candidate')],'negative_admissions':{side:sum(ok(r,side) for r in negatives) for side in ['original','candidate']},'new_negative_admissions':[key(r) for r in negatives if ok(r,'candidate') and not ok(r,'original')],'changed_clock_worst_error_over_sd':max(abs(r['candidate']['rate_standardized_error']) for r in changed),'changed_clock_worsening_count':len(rateworse),'max_changed_clock_worsening_ppm':max([abs(r['candidate']['rate_error_ppm'])-abs(r['original']['rate_error_ppm']) for r in rateworse],default=0),'miss_worsening':[{'key':key(r),'old':counts(r,'original'),'new':counts(r,'candidate'),'old_rate_error_ppm':r['original']['rate_error_ppm'],'new_rate_error_ppm':r['candidate']['rate_error_ppm']} for r in missworse],'false_worsening':[{'key':key(r),'old':counts(r,'original'),'new':counts(r,'candidate')} for r in falseworse],'worst_standardized_rate':{'key':key(worst),'old':worst['original']['rate_standardized_error'],'new':worst['candidate']['rate_standardized_error']},'max_candidate_runtime_s':max(r['candidate_runtime_s'] for r in rows)}
(root/'work/clock-refinement-independent-outcome.json').write_text(json.dumps(summary,indent=2)+'\n');print(json.dumps(summary,indent=2))
