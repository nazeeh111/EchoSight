"""Independent affected cancellation follow-up; no held-out/science refitting."""
from pathlib import Path
import argparse,contextlib,copy,hashlib,io,json,signal,sys
from unittest.mock import patch
parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('--checkout',type=Path,required=True)
parser.add_argument('--output',type=Path,required=True)
a=parser.parse_args();S=a.checkout.resolve();P=a.output.resolve();P.mkdir(parents=True,exist_ok=True);sys.path.insert(0,str(S))
from evaluation.controlled_development import recording_protocol
from echosight.pipeline import process_session,save_result
from echosight import controlled,inference,multisource
from echosight.cli import main
from tests.test_schemas import validator
from jsonschema import ValidationError
COMMIT='5f778a887817761b9db0626256698c5f678b497f'
owned=['echosight/'+n+'.py' for n in ('controlled','pipeline','inference','multisource')]+['schemas/result.schema.json','schemas/controlled-result.schema.json']
sourcehashes={n:hashlib.sha256((S/n).read_bytes()).hexdigest() for n in owned}
report={'commit':COMMIT,'source_hashes':sourcehashes,'scope':'Four raw development epochs, exact cached epoch boundary injections, no held-out evaluation or scientific threshold changes','cases':[]}
protocol=recording_protocol(P/'raw','moved')
results=[process_session(e['session']) for e in protocol['epochs']]
assert all(r['status']=='ok' and r['surfaces'] for r in results)
originals=json.dumps(results,sort_keys=True)
report['raw_epoch_statuses']=[r['status'] for r in results]
report['raw_epoch_surfaces']=[len(r['surfaces']) for r in results]
report['recording_hashes']=[[o['recording_sha256'] for o in r['observations']] for r in results]

def validate_controlled(out):
 assert out['status']=='cancelled' and out['conditional_spatial_changes']==[] and out['receiver_evidence']==[]
 assert len(out['epoch_results'])==4
 for e,r in zip(out['epoch_results'],results):
  assert e['result']==controlled._compact_epoch(r)
 assert not out['physical_scene_change_established'];validator('controlled-result').validate(out)
 assert json.dumps(results,sort_keys=True)==originals

for boundary in ('spatial','first_receiver','last_receiver_no_change'):
 for cli in (False,True):
  state={'cancelled':False,'calls':0};p=copy.deepcopy(protocol)
  if boundary=='last_receiver_no_change':p['controls']['differential_timing_std_s']=.001
  target='_spatial_changes' if boundary=='spatial' else '_receiver_evidence';fn=getattr(controlled,target)
  def wrapped(*args,**kwargs):
   value=fn(*args,**kwargs);state['calls']+=1
   if boundary!='last_receiver_no_change' or state['calls']==12:
    state['cancelled']=True
    if cli:signal.raise_signal(signal.SIGINT)
   return value
  cache=copy.deepcopy(results);cachebefore=json.dumps(cache,sort_keys=True)
  with patch('echosight.pipeline.process_session',side_effect=cache),patch('echosight.controlled.'+target,side_effect=wrapped):
   if cli:
    path=P/'protocol.json';save_result(p,path);output=P/f'controlled-{boundary}.json'
    with contextlib.redirect_stdout(io.StringIO()):code=main(['controlled',str(path),'--output',str(output)])
    assert code==130;out=json.loads(output.read_text())
   else:out=controlled.process_controlled_protocol(p,cancel=lambda:state['cancelled'])
  validate_controlled(out);assert json.dumps(cache,sort_keys=True)==cachebefore
  report['cases'].append(dict(boundary=boundary,cli=cli,status=out['status'],conditional_changes=len(out['conditional_spatial_changes']),receiver_evidence=len(out['receiver_evidence']),retained_epochs=len(out['epoch_results']),input_unchanged=True))

# Successful comparison remains available, but relabelled cancellation is invalid.
with patch('echosight.pipeline.process_session',side_effect=copy.deepcopy(results)):
 completed=controlled.process_controlled_protocol(protocol)
assert completed['status']=='conditional_spatial_change' and completed['conditional_spatial_changes']
validator('controlled-result').validate(completed)
for schema,obj in [('controlled-result',completed),('result',results[0])]:
 bad=copy.deepcopy(obj);bad['status']='cancelled'
 try:validator(schema).validate(bad)
 except ValidationError:report['cases'].append(dict(schema=schema,cancelled_claims_rejected=True))
 else:raise AssertionError('cancelled claim accepted by '+schema)

for method in ('mapper','baseline'):
 for cli in (False,True):
  state={'cancelled':False};session=copy.deepcopy(protocol['epochs'][0]['session'])
  def final(f,m=''):
   if f==1 and m in ('ok','partial','ambiguous','no_result'):
    state['cancelled']=True
    if cli:signal.raise_signal(signal.SIGINT)
  if cli:
   save_result(session,P/'session.json')
   def cli_process(*args,**kwargs):return process_session(*args,**kwargs,progress=final)
   with patch('echosight.cli.process_session',side_effect=cli_process),contextlib.redirect_stdout(io.StringIO()):
    code=main(['process',str(P/'session.json'),'--method',method,'--output',str(P/f'scene-{method}.json')])
   assert code==130;out=json.loads((P/f'scene-{method}.json').read_text())
  else:out=process_session(session,method=method,cancel=lambda:state['cancelled'],progress=final)
  assert state['cancelled'] and out['status']=='cancelled'
  for k in ('surfaces','hypotheses','dimensions','guidance'):assert out[k]==[]
  assert len(out['observations'])==12 and len(out['provenance']['recordings'])==12
  assert [o['recording_sha256'] for o in out['observations']]==report['recording_hashes'][0]
  validator('result').validate(out)
  report['cases'].append(dict(boundary='outer_terminal_callback',method=method,cli=cli,status=out['status'],surfaces=len(out['surfaces']),observations=len(out['observations']),recording_hashes_preserved=True))

# Shared helper is a copy: it must not erase the caller's source objects or mutate
# nested diagnostics/search. Both finally blocks must update the returned copy.
input_result={'status':'ok','search':{'complete':True},'diagnostics':['old'],
 'surfaces':[{'surface_id':'unfinished'}],'observations':[{'recording_sha256':'raw'}],
 'processed_sessions':[{'session':{'session_id':'original'}}]}
for field in ('shared_image_source_covariance_m2','shared_plane_parameter_covariance_m2','score','higher_order_explanations','parent_model_comparison','path_model_comparison'):input_result[field]=['unfinished']
before=copy.deepcopy(input_result);clean=inference._cancelled_result(input_result)
assert input_result==before and inference._cancelled_result(clean)==clean
assert clean['observations']==before['observations'] and clean['processed_sessions']==before['processed_sessions']
for field in ('shared_image_source_covariance_m2','shared_plane_parameter_covariance_m2','score','higher_order_explanations','parent_model_comparison','path_model_comparison'):assert field not in clean
with patch('echosight.inference.time.perf_counter',side_effect=[10.,13.]):
 single=inference.infer_scene({},[],cancel=lambda:True)
with patch('echosight.multisource.time.perf_counter',side_effect=[20.,25.]):
 joint=multisource.infer_scene_bundle([],{},cancel=lambda:True)
assert single['status']==joint['status']=='cancelled' and single['runtime_s']==3 and joint['runtime_s']==5
report['helper']={'input_preserved':True,'idempotent':True,'single_finally_runtime_s':single['runtime_s'],'joint_finally_runtime_s':joint['runtime_s']}
report['findings_closed']=['controlled_cancelled_claims','outer_pipeline_terminal_callback']
(P/'results.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps({'commit':COMMIT,'cases_passed':len(report['cases']),'helper':report['helper'],'findings_closed':report['findings_closed']},indent=2))
