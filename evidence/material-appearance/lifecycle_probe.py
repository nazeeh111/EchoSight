"""Independent current-job context snapshot, cancellation and archive checks."""
import copy, hashlib, json, sys, tempfile, threading, time, zipfile
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[2]))
from echosight.pipeline import process_session
from echosight.storage import SessionStore, load_session
from echosight.simulation import simulate_session
from tests.test_schemas import validator
root=Path(sys.argv[1]) if len(sys.argv)>1 else Path(tempfile.mkdtemp(prefix='lifecycle-',dir='work/material-review'))
root.mkdir(exist_ok=True)
source=load_session(simulate_session(root/'raw',scenario='room',seed=171,capture_count=12))
ctx=dict(schema_version='1.0',route_id='review-chain',profiles=[],maximum_squared_distance=9,minimum_views=1)
def wait(store,jid):
 until=time.monotonic()+40
 while time.monotonic()<until:
  status=store.get_job(jid)['status']
  if status in ('completed','failed','cancelled'):return status
  time.sleep(.02)
 raise AssertionError('job timeout')
with SessionStore(root/'store') as store:
 sid=store.create_session(dict(source,captures=[],interpretation_context=ctx))['session_id']
 for c in source['captures']:
  store.add_recording(sid,c['recording_path'],{k:c[k] for k in ('capture_id','receiver_position_m','receiver_position_std_m','provenance')})
 before=store.public_session(sid);started=threading.Event();release=threading.Event();snapshots=[]
 def blocked_processor(session,**kwargs):
  snapshots.append(copy.deepcopy(session));started.set();assert release.wait(30)
  return process_session(session,**kwargs)
 job=store.start_job(sid,blocked_processor);assert started.wait(10)
 changed=copy.deepcopy(ctx);changed['minimum_views']=3
 store.update_calibration(sid,dict(expected_revision=before['revision'],interpretation_context=changed));release.set()
 assert wait(store,job['job_id'])=='completed'
 prior=store.get_result(sid);assert prior['stale']
 assert prior['acquisition']['interpretation_context']==ctx==snapshots[0]['interpretation_context']
 try:store.material_reference(sid,dict(surface_id='unused',material_id='x',label='x',route_id='x',provenance=dict(kind='supplied',note='x')))
 except FileExistsError:pass
 else:raise AssertionError('stale material reference accepted')
 j=store.start_job(sid,process_session);assert wait(store,j['job_id'])=='completed';current=store.get_result(sid)
 assert current['surfaces']==prior['surfaces'] and current['observations']==prior['observations']
 assert current['result_id']!=prior['result_id']
 validator('result').validate(current)
 artifact=store.export_session(sid)
 with SessionStore(root/'replay') as replay:
  restored=replay.import_archive(artifact);assert restored['replay']['archived_result']['binding_issues']==[]
  try:replay.get_result(sid)
  except KeyError:pass
  else:raise AssertionError('unverified archive published')
  j=replay.start_job(sid,process_session);assert wait(replay,j['job_id'])=='completed'
  replayed=replay.get_result(sid);assert replayed['result_id']==current['result_id'] and replayed['interpretation']==current['interpretation']
 for phase in ('interpretation_entry','terminal_callback'):
  cancelled=[False]
  def progress(fraction,message):
   if (phase=='interpretation_entry' and message=='Interpreting materials and appearance') or (phase=='terminal_callback' and fraction==1.):cancelled[0]=True
  result=process_session(dict(source,interpretation_context=ctx),cancel=lambda:cancelled[0],progress=progress)
  assert result['status']=='cancelled' and not result['surfaces'] and not result.get('interpretation',{}).get('surface_interpretations')
  assert len(result['observations'])==12
  validator('result').validate(result)
  (root/(phase+'.json')).write_text(json.dumps(result,allow_nan=False))
 report=dict(status='passed',active_job_snapshot_preserved=True,stale_reference_rejected=True,geometry_and_observations_equal=True,archive_quarantined_recomputed=True,cancellation_phases=['interpretation_entry','terminal_callback'],scene_schema_passed=True,original_result_id=prior['result_id'],revised_result_id=current['result_id'])
 (root/'report.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
