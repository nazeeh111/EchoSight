"""Paired immutable raw-recording trial; no truth supplied to either estimator."""
import argparse,copy,hashlib,importlib.util,json,sys,time
from pathlib import Path
ROOT=Path(__file__).resolve().parent;REPO=ROOT.parents[2];sys.path.insert(0,str(ROOT/'snapshot'))
from echosight import inference,guard_inference,signals
from echosight.pipeline import process_session
from echosight.storage import load_session
from evaluation.metrics import score_surfaces,acceptance_failures
ORIGINAL_INFER=inference.infer_scene;ORIGINAL_SIGNAL=signals.process_recording

def guarded(session,observations,cancel=None,progress=None):
    baseline=ORIGINAL_INFER(session,observations,cancel=cancel,progress=progress)
    if baseline['status']=='cancelled':return baseline
    result=guard_inference.infer_scene(session,observations,cancel=cancel,progress=progress)
    if result['status']=='cancelled':return result
    if result.get('held_guard',{}).get('status')=='unavailable':
        baseline['held_guard']=result['held_guard'];baseline['diagnostics'].append('held_guard_unavailable_result_is_original_uncalibrated_mapper');return baseline
    # The statistical stage may lose a parent. Do not erase existing physical alternatives.
    if 'first_order_vs_higher_order_ambiguity' in baseline.get('diagnostics',[]):
        if result['surfaces']:result['hypotheses'].append(dict(hypothesis_id='held_guard_survivors_still_order_ambiguous',surfaces=result['surfaces'],reason='Passing conditional clutter test does not remove baseline physical path-order ambiguity.'))
        result['surfaces']=[];result['dimensions']=[];result['status']='ambiguous';result['diagnostics'].append('baseline_first_order_vs_higher_order_ambiguity_preserved')
        result['hypotheses']+=baseline['hypotheses'];result['higher_order_explanations']=baseline.get('higher_order_explanations',[]);result['guidance']+=baseline['guidance']
    return result

def joint_processor():
    spec=importlib.util.spec_from_file_location('echosight.joint_trial_signals',ROOT/'snapshot/echosight/joint_trial_signals.py');mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod)
    def process(*args,**kwargs):return mod.process_recording(*args,**kwargs,estimator='joint_kernel')
    return process

def failures(suite,case,result,metrics,runtime,spec):
    if suite=='flair':
        return acceptance_failures('flair',result,metrics,runtime,dict(requirements={'flair':spec['acceptance']}))
    if suite!='stress':return acceptance_failures(case['scenario'],result,metrics,runtime,spec)
    criteria={**spec['common'],**spec['family_requirements'][case['family']]};out=[]
    for key,observed,sense in [('maximum_false_surfaces',metrics['false_surfaces'],'max'),('maximum_runtime_seconds',runtime,'max'),('minimum_matched_surfaces',metrics['matched_count'],'min'),('minimum_horizontal_surfaces',metrics['horizontal_matched'],'min'),('maximum_definitive_surfaces',metrics['predicted_count'],'max')]:
        if key in criteria and ((sense=='max' and observed>criteria[key]) or (sense=='min' and observed<criteria[key])):out.append(f'{key}: {observed} versus {criteria[key]}')
    if criteria.get('require_diagnostics') and not result.get('diagnostics'):out.append('required diagnostics absent')
    return out

def cases():
    result=[]
    for suite,filename in [('twelve','acceptance_extended.json'),('stress','stress_acceptance.json')]:
        spec=json.loads((ROOT/'snapshot/evaluation'/filename).read_text())
        for case in spec.get('held_out_cases',spec.get('cases')):
            family=case.get('scenario',case.get('family'));folder=REPO/'work/physics-estimator'/f'control-{suite}'/f"{family}-{case['seed']}"
            result.append((suite,case,spec,folder,'joint_kernel'))
    spec=json.loads((ROOT/'snapshot/evaluation/flair_acceptance.json').read_text())
    for estimator in ['matched_filter','joint_kernel']:
        result.append(('flair',{'family':'flair','seed':0},spec,REPO/'work/physics-estimator/control-flair',estimator))
    return result

def main():
    rows=[];inputs=[]
    for suite,case,spec,folder,estimator in cases():
        if not (folder/'session.json').exists():raise FileNotFoundError(folder)
        session=load_session(folder/'session.json')
        inputs.append(dict(suite=suite,case=case,estimator=estimator,session_sha256=hashlib.sha256((folder/'session.json').read_bytes()).hexdigest(),recordings={c['capture_id']:hashlib.sha256(Path(c['recording_path']).read_bytes()).hexdigest() for c in session['captures']}))
    (ROOT/'combination-input-manifest.json').write_text(json.dumps(inputs,indent=2)+'\n')
    codehash=lambda:{str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted((ROOT/'snapshot/echosight').glob('*.py'))}
    before=codehash()
    for index,(suite,case,spec,folder,estimator) in enumerate(cases()):
        signals.process_recording=ORIGINAL_SIGNAL if estimator=='matched_filter' else joint_processor();paired=[]
        for method,func in [('original',ORIGINAL_INFER),('held_guard',guarded)]:
            inference.infer_scene=func;started=time.perf_counter();result=process_session(folder/'session.json');runtime=time.perf_counter()-started
            result['experimental_trial']=dict(method=method,estimator=estimator,base_commit='198d365f3b13f221ac258332eaaccdf96506a641',physical_validation=False)
            result['result_id']+='-'+method+'-'+estimator
            # Evaluation labels are opened only after processing.
            truth=json.loads((folder/('truth-laser.json' if suite=='flair' else 'truth.json')).read_text());metrics=score_surfaces(result,truth,**{k:v for k,v in spec['matching'].items() if k!='one_to_one'})
            family=case.get('scenario',case.get('family'));name=f"{suite}-{family}-{case['seed']}-{estimator}-{method}";(ROOT/'combination-results').mkdir(exist_ok=True)
            (ROOT/'combination-results'/f'{name}.json').write_text(json.dumps(result,indent=2,allow_nan=False)+'\n')
            row=dict(suite=suite,case=case,estimator=estimator,method=method,status=result['status'],runtime_s=runtime,metrics=metrics,failures=failures(suite,case,result,metrics,runtime,spec),guard=result.get('held_guard',{}).get('status'),guard_reason=result.get('held_guard',{}).get('reason'),diagnostics=result['diagnostics'],rejected_captures=sum(o['status']!='ok' for o in result['observations']))
            rows.append(row);paired.append(result);print(name,metrics['matched_count'],metrics['false_surfaces'],metrics['missed_surfaces'],result['status'],row['guard'],flush=True)
        assert paired[0]['observations']==paired[1]['observations'],'Extraction differs between arms'
        assert {o['capture_id']:o['recording_sha256'] for o in paired[0]['observations'] if 'recording_sha256' in o}=={k:v for k,v in inputs[index]['recordings'].items() if k in {o['capture_id'] for o in paired[0]['observations'] if 'recording_sha256' in o}}
        (ROOT/'combination-results.json').write_text(json.dumps(dict(base_commit='198d365f3b13f221ac258332eaaccdf96506a641',rows=rows,source_unchanged=before==codehash(),source_sha256=before,same_raw_and_extracted_observations=True),indent=2,allow_nan=False)+'\n')
    inference.infer_scene=ORIGINAL_INFER;signals.process_recording=ORIGINAL_SIGNAL
if __name__=='__main__':main()
