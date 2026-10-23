"""Independent scalar saved-output recomputation. Never renders or processes audio."""
import hashlib,json,math,subprocess,wave
from collections import Counter
from pathlib import Path
P=Path(__file__).resolve().parent;B=P.parents[1]/'held-followup';R=P.parents[1]/'publish/EchoSight';OLD=R/'evidence/calibration-room-transfer/replay'
def read(p):return json.loads(p.read_text())
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def close(a,b):
 if isinstance(a,float) or isinstance(b,float):return math.isclose(a,b,rel_tol=1e-10,abs_tol=1e-12)
 return a==b
def assert_dict(a,b):
 for k,v in a.items():
  assert k in b,(k,'missing')
  if isinstance(v,dict):assert_dict(v,b[k])
  elif isinstance(v,list):
   assert len(v)==len(b[k]),k
   for x,y in zip(v,b[k]):
    if isinstance(x,dict):assert_dict(x,y)
    else:assert close(x,y),(k,x,y)
  else:assert close(v,b[k]),(k,v,b[k])
freeze=read(B/'freeze.json');digest=sha(B/'freeze.json');assert digest=='a2e5df60b72c7ba996abab223168705297de1f4a23f44bc21c33a6d0d73b05bc'
for name,h in freeze['input_hashes'].items():
 kind,rel=name.split('/',1);p={'local':B,'repo':R,'replay':OLD}[kind]/rel
 assert sha(p)==h,name
assert sha(B/'static-check.json')==freeze['static_check_sha256']
assert read(B/'root-execution-approval.json')['freeze_sha256']==digest
assert read(B/'render-start.json')['freeze_sha256']==read(B/'render-complete.json')['freeze_sha256']==read(B/'run-start.json')['freeze_sha256']==digest
assert read(B/'root-execution-approval.json')['review_sha256']==sha(P.parent/'REVIEW.md')
assert subprocess.check_output(['git','rev-parse','HEAD'],cwd=R,text=True).strip()==freeze['runtime_commit']
for name,h in freeze['input_hashes'].items():
 if name.startswith('repo/'):
  assert hashlib.sha256(subprocess.check_output(['git','show',freeze['runtime_commit']+':'+name[5:]],cwd=R)).hexdigest()==h,name
settings=read(B/'settings.json');c=settings['acceptance'];old=read(OLD/'expected-results.json')
implementation=hashlib.sha256()
for f in sorted((R/'echosight').glob('*.py')):implementation.update(f.name.encode());implementation.update(f.read_bytes())
extractions={};records=[]
for seed in settings['seeds']:
 folder=B/'raw'/str(seed);manifest=read(folder/'manifest.json');assert len(list(folder.glob('*.wav')))==4
 assert sha(folder/'manifest.json')==read(B/'render-complete.json')['manifests'][str((folder/'manifest.json').relative_to(B))]
 for name,h in manifest.items():assert sha(folder/name)==h
 s=read(folder/'session.json');truth=read(folder/'truth.json');out=read(B/'extractions'/f'{seed}.json');extractions[seed]=out
 assert len(s['captures'])==len(truth)==len(out['observations'])==4
 assert out['status']=='cancelled' and out['surfaces']==[] and out['hypotheses']==[]
 assert out['provenance']['implementation_sha256']==implementation.hexdigest()
 assert out['provenance']['physical_validation'] is False
 assert out['provenance']['runtime_versions']=={k:read(B/'static-check.json')['environment'][k] for k in ('python','numpy','scipy')}
 assert s['source_position_m']==settings['nominal_source_m']!=settings['physical_source_m']
 assert s['sound_speed_m_s']==343. and s['source_clock_scale']==1. and 'effective_speed_m_s' not in s
 assert set(s)=={'schema_version','session_id','coordinate_frame_id','source_position_m','source_position_std_m','sound_speed_m_s','sound_speed_std_m_s','source_clock_scale','source_clock_std_ppm','probe','captures'}
 for k,v in settings['probe'].items():assert s['probe'][k]==v
 for i,(cap,t,o) in enumerate(zip(s['captures'],truth,out['observations'])):
  assert cap['capture_id']==t['capture_id']==o['capture_id']==f'proposed-held-{i:02d}'
  assert t['position_m']==settings['withheld_positions_m'][i] and cap['receiver_position_m']!=t['position_m']
  assert o['receiver_position_m']==cap['receiver_position_m'] and o['recording_sha256']==cap['sha256']==t['recording_sha256']==sha(folder/cap['recording_path'])
  assert not {'paths','physical_source_m','room_size_m','alpha','offset_s'}&set(cap)
  assert len(t['paths'])==7 and {x['kind'] for x in t['paths']}=={'direct'}|{f'wall-{j}-{k}' for j in range(3) for k in (0,1)}
  with wave.open(str(folder/cap['recording_path'])) as w:assert (w.getnchannels(),w.getsampwidth(),w.getframerate())==(1,2,48000)
 records.append(dict(seed=seed,observations=4,recordings=4,extraction_sha256=sha(B/'extractions'/f'{seed}.json'),statuses=[o['status'] for o in out['observations']]))

derived=[];pathcount=0
for seed in settings['seeds']:
 out=extractions[seed]
 for method in settings['methods']:
  fit=read(OLD/f'fits/room-{seed}-{method}.json');result=fit['result'];a=result['acquisition'];source=a['source_position_m'];speed=a.get('effective_speed_m_s',a['sound_speed_m_s']/a['source_clock_scale']);rows=[]
  for surface in result['surfaces']:
   n=surface['normal'];d=surface['offset_m'];dot=sum(x*y for x,y in zip(n,source));image=[x+2*(d-dot)*nn for x,nn in zip(source,n)]
   for observation in out['observations']:
    r=observation['receiver_position_m'];prediction=(math.dist(r,image)-math.dist(r,source))/speed
    eligible=[x for x in observation['candidates'] if not x.get('merged',False) and abs(x['delay_s']-prediction)<=c['withheld_candidate_window_s']]
    row=dict(surface_id=surface['surface_id'],capture_id=observation['capture_id'],predicted_delay_s=prediction,observation_status=observation['status'],candidate_count=len(eligible),status='missing_or_ambiguous')
    if observation['status']=='ok' and len(eligible)==1:row.update(status='unique',candidate_id=eligible[0]['candidate_id'],residual_s=eligible[0]['delay_s']-prediction)
    rows.append(row)
  used=Counter((r['capture_id'],r['candidate_id']) for r in rows if r['status']=='unique')
  for row in rows:
   if row['status']=='unique' and used[(row['capture_id'],row['candidate_id'])]>1:row['status']='candidate_reused_by_multiple_surfaces'
  good=[r['residual_s'] for r in rows if r['status']=='unique'];complete=len(rows)==len(good)==24
  rms=math.sqrt(math.fsum(x*x for x in good)/len(good)) if good else None;mx=max(map(abs,good)) if good else None
  held=dict(rows=rows,expected=24,unique=len(good),complete=complete,unique_subset_rms_s=rms,unique_subset_max_abs_s=mx,complete_rms_s=rms if complete else None,complete_max_abs_s=mx if complete else None,passed=complete and rms<=c['withheld_rms_s'] and mx<=c['withheld_max_s'])
  previous=next(r for r in old['rows'] if (r['seed'],r['family'],r['method'])==(seed,'room',method));geometry=previous['geometry'];passed=geometry['matched']==6 and geometry['horizontal']==2 and geometry['unmatched']==0 and held['passed'] and previous['all_mapping_recordings_accepted']
  assert previous['runtime_pass']==(previous['raw_processing_s']<=c['raw_processing_s'])
  derived.append(dict(seed=seed,method=method,withheld=held,geometry=geometry,geometry_and_prediction_pass=passed,runtime_pass=previous['runtime_pass'],raw_processing_s=previous['raw_processing_s'],all_mapping_recordings_accepted=previous['all_mapping_recordings_accepted'],mapping_runtime_commit=settings['historical_runtime_commit'],mapping_timing_freshly_measured=False,observations_sha256=sha(B/'extractions'/f'{seed}.json')))
  pathcount+=24
benefits=[]
for seed in settings['seeds']:
 cases={r['method']:r for r in derived if r['seed']==seed};j=cases['joint_mapper'];comparisons=[]
 for method in ('nominal_mapper','one_x_mapper'):
  b=cases[method];hj,hb=j['withheld'],b['withheld'];gj,gb=j['geometry'],b['geometry'];comparable=hj['complete'] and hb['complete'] and gj['matched']==gb['matched']==6
  rms_gain=hb['complete_rms_s']-hj['complete_rms_s'] if comparable else None;anchor_gain=gb['six_plane_mean_anchor_error_m']-gj['six_plane_mean_anchor_error_m'] if comparable else None;regress=gj['unmatched']<=gb['unmatched'] and gj['missed']<=gb['missed']
  gain=j['geometry_and_prediction_pass'] and regress and (not b['geometry_and_prediction_pass'] or (comparable and rms_gain>=c['minimum_withheld_rms_gain_s'] and anchor_gain>=c['minimum_mean_anchor_gain_m']))
  comparisons.append(dict(comparator=method,complete_rms_gain_s=rms_gain,mean_anchor_gain_m=anchor_gain,comparator_complete_gate_failed=not b['geometry_and_prediction_pass'],no_false_or_missed_regression=regress,gain=gain))
 benefits.append(dict(seed=seed,comparisons=comparisons,benefit=all(x['gain'] for x in comparisons)))
nulls=[r for r in old['rows'] if r['family']=='direct_only'];joints=[r for r in derived if r['method']=='joint_mapper'];nullpass=all(r['geometry_and_prediction_pass'] and r['runtime_pass'] for r in nulls if r['method']=='joint_mapper');transfer=all(r['geometry_and_prediction_pass'] and r['runtime_pass'] for r in joints) and nullpass
recall=sum(r['geometry']['matched'] for r in joints)>sum(r['geometry']['matched'] for r in derived if r['method']=='joint_first_echo')
independent=dict(rows=derived,benefits=benefits,retained_nulls=nulls,retained_original_transfer_pass=old['transfer_pass'],retained_original_promotion_pass=old['promotion_criteria_pass'],transfer_pass=transfer,promotion_criteria_pass=transfer and recall and all(x['benefit'] for x in benefits),physical_validation=False,uncertainty_bound_status='UNKNOWN')
# Only now compare independent numeric results with the experiment summary.
saved=read(B/'results.json');assert_dict(independent,saved)
assert old['transfer_pass'] is False and old['promotion_criteria_pass'] is False
assert pathcount==240
report=dict(status='passed',required_paths=pathcount,actual_predicted_rows=sum(len(r['withheld']['rows']) for r in derived),records=records,independent=independent,freeze_sha256=digest,results_sha256=sha(B/'results.json'),audio_generated=False,audio_processed=False,mapping_executed=False)
with (P/'verification.json').open('x') as f:json.dump(report,f,indent=2,allow_nan=False);f.write('\n')
print(json.dumps(dict(status='passed',required_paths=pathcount,actual_predicted_rows=report['actual_predicted_rows'],rows=[dict(seed=r['seed'],method=r['method'],unique=r['withheld']['unique'],complete_rms_s=r['withheld']['complete_rms_s'],gate=r['geometry_and_prediction_pass']) for r in derived],benefits=benefits,transfer_pass=transfer,promotion_criteria_pass=independent['promotion_criteria_pass']),indent=2))
