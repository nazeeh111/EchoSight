"""Reproduce a real late-cancelled legacy scene reaching display comparison."""
import copy,inspect,importlib.util,json,pathlib,sys
ROOT=pathlib.Path(__file__).resolve().parents[1];SNAP=ROOT/'work/review-3745665-snapshot';sys.path.insert(0,str(SNAP))
from tests.test_inference import fixture
from echosight.inference import infer_scene
from echosight.evolution import compare_results

def late_cancel():
    frame=inspect.currentframe()
    while frame:
        if frame.f_code.co_name=='_run' and frame.f_globals.get('__name__')=='echosight.inference':
            return bool(frame.f_locals.get('out',{}).get('surfaces'))
        frame=frame.f_back
    return False
s,obs,_=fixture(coplanar=True)
complete=infer_scene(s,obs)
cancelled=infer_scene(s,obs,cancel=late_cancel)
assert complete['status']=='ambiguous' and not complete['surfaces']
assert cancelled['status']=='cancelled' and len(cancelled['surfaces'])==1
normal_s,normal_obs,_=fixture();prior=infer_scene(normal_s,normal_obs)
for output,session,observations,rid,sid in [(prior,normal_s,normal_obs,'prior','A'),(cancelled,s,obs,'cancelled','B')]:
    output.update(schema_version='1.0',result_id=rid,session_id=sid,observations=observations)
    acquisition=copy.deepcopy(session);acquisition.update(session_id=sid,coordinate_frame_id='same-survey',probe={'probe_id':'same-probe'})
    output['acquisition']=acquisition
comparison=compare_results(prior,cancelled)
assert comparison['status']=='comparable' and len(comparison['correspondences'])==1
assert comparison['correspondences'][0]['additional_support_count']==8
spec=importlib.util.spec_from_file_location('prior_evolution',ROOT/'work/review-3745665-parent-evolution.py');old=importlib.util.module_from_spec(spec);spec.loader.exec_module(old)
old_comparison=old.compare_results(prior,cancelled)
assert old_comparison['status']=='comparable' and len(old_comparison['correspondences'])==1
reverse=compare_results(cancelled,prior);assert reverse['status']=='comparable' and len(reverse['correspondences'])==1
report={'parent_also_continues_cancelled_track':True,'cancelled_previous_also_continues_track':True,'commit':'3745665352f59bc88e432b1f703054ab29398ce1','uncancelled_coplanar_status':complete['status'],'uncancelled_surfaces':len(complete['surfaces']),'late_cancelled_status':cancelled['status'],'late_cancelled_surfaces':len(cancelled['surfaces']),'comparison':comparison,'method':'Public cancellation predicate observes whether the local inference result has acquired selected surfaces; it changes no fit data or implementation. Comparison metadata mirrors pipeline decoration with explicit compatible frame/probe.'}
(ROOT/'work/review-3745665-cancelled-probe.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps({k:v for k,v in report.items() if k!='comparison'},indent=2));print('comparison: comparable, one continued track, eight additional supports')
