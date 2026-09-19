from pathlib import Path
import copy,importlib.util,json,sys,time
ROOT=Path('/Users/nazeeh/Documents/Codex/2026-09-18/echosight-autonomous-backend-implementation-lead-a/backend');OUT=Path(__file__).resolve().parent;sys.path.insert(0,str(ROOT))
data=json.loads((ROOT/'work/spatial-finish/fixtures/higher-order-1129-observations.json').read_text());reports=[]
for name in ['original','candidate']:
 spec=importlib.util.spec_from_file_location('echosight.cancel_review_'+name,OUT/f'{name}.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
 original_fit=m.least_squares;state={'cancelled':False,'ols_fits':0,'post_request_fits':0}
 def interrupt_after_first_ols(*args,**kwargs):
  is_ols=kwargs.get('loss','linear')=='linear'
  if is_ols:
   if state['cancelled']:state['post_request_fits']+=1
   state['ols_fits']+=1
  result=original_fit(*args,**kwargs)
  if is_ols:state['cancelled']=True
  return result
 m.least_squares=interrupt_after_first_ols;start=time.perf_counter();result=m.infer_scene_bundle(copy.deepcopy(data['processed_sessions']),copy.deepcopy(data['bundle']),cancel=lambda:state['cancelled'])
 assert state['cancelled']
 if name=='candidate':
  assert result['status']=='cancelled';assert result['surfaces']==[];assert result['hypotheses']==[];assert state['post_request_fits']==0
 reports.append(dict(module=name,**state,status=result['status'],surfaces=len(result['surfaces']),hypotheses=len(result['hypotheses']),seconds=time.perf_counter()-start))
(OUT/'cancellation-results.json').write_text(json.dumps(reports,indent=2)+'\n');print(json.dumps(reports,indent=2))
