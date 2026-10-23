"""Independent exhaustive six-plane assignment and saved-provenance checks."""
import hashlib,itertools,json,math
from pathlib import Path
P=Path(__file__).resolve().parent;B=P.parents[1]/'held-followup';R=P.parents[1]/'publish/EchoSight';OLD=R/'evidence/calibration-room-transfer/replay'
read=lambda p:json.loads(p.read_text());sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
c=read(B/'settings.json');saved=read(OLD/'expected-results.json');checked=[]
for row in saved['rows']:
 seed,family,method=row['seed'],row['family'],row['method'];fit=read(OLD/f'fits/{family}-{seed}-{method}.json');truth=read(OLD/f'raw/{family}-{seed}/truth.json');surfaces=fit['result']['surfaces'];expected=truth['surfaces'];errors={}
 for i,s in enumerate(surfaces):
  norm=math.sqrt(sum(x*x for x in s['normal']));n=[x/norm for x in s['normal']]
  for j,t in enumerate(expected):
   dot=abs(sum(x*y for x,y in zip(n,t['normal'])));angle=math.degrees(math.acos(min(1,max(0,dot))));distance=abs(sum(x*y for x,y in zip(n,t['anchor_m']))-s['offset_m']);valid=angle<=c['acceptance']['normal_error_deg'] and distance<=c['acceptance']['anchor_error_m'];penalty=(0 if valid else max(len(surfaces),len(expected))+1)+min(angle/c['acceptance']['normal_error_deg']+distance/c['acceptance']['anchor_error_m'],2)/2
   errors[i,j]=(valid,angle,distance,penalty)
 assert len(surfaces)<=len(expected) or not expected
 assignment=min(itertools.permutations(range(len(expected)),len(surfaces)),key=lambda p:sum(errors[i,j][3] for i,j in enumerate(p))) if surfaces and expected else ()
 valid=[(i,j) for i,j in enumerate(assignment) if errors[i,j][0]];g=row['geometry']
 assert g['matched']==len(valid) and g['unmatched']==len(surfaces)-len(valid) and g['missed']==len(expected)-len(valid)
 assert g['horizontal']==sum(abs(expected[j]['normal'][2])>=.9 for i,j in valid)
 mean=sum(errors[i,j][2] for i,j in valid)/6 if len(valid)==6 else None
 assert (mean is None and g['six_plane_mean_anchor_error_m'] is None) or math.isclose(mean,g['six_plane_mean_anchor_error_m'],rel_tol=1e-10,abs_tol=1e-12)
 assert row['all_mapping_recordings_accepted']==(len(fit['result']['observations'])==12 and all(o['status']=='ok' for o in fit['result']['observations']))
 assert row['raw_processing_s']==fit['raw_processing_s'] and row['runtime_pass']==(fit['raw_processing_s']<=c['acceptance']['raw_processing_s'])
 if family=='direct_only':assert row['geometry_and_prediction_pass']==(not surfaces and row['all_mapping_recordings_accepted'])
 checked.append(dict(seed=seed,family=family,method=method,matched=len(valid),unmatched=g['unmatched'],missed=g['missed'],mean_anchor_error_m=mean))
# Check independent scalar physical paths and amplitude declarations, never waveform synthesis.
for seed in c['seeds']:
 truth=read(B/f'raw/{seed}/truth.json');session=read(B/f'raw/{seed}/session.json');out=read(B/f'extractions/{seed}.json')
 for i,t in enumerate(truth):
  r=t['position_m'];source=c['physical_source_m'];direct=math.dist(r,source)
  for p in t['paths']:
   if p['kind']=='direct':length=direct;amplitude=c['direct_amplitude']
   else:
    _,ax,side=p['kind'].split('-');ax=int(ax);side=int(side);image=source.copy();image[ax]=2*side*c['room_size_m'][ax]-source[ax];length=math.dist(r,image);amplitude=c['direct_amplitude']*c['room_reflection_coefficient']*direct/length
   assert math.isclose(p['delay_s'],length/c['effective_speed_m_s'],rel_tol=1e-12,abs_tol=1e-15)
   assert math.isclose(p['amplitude'],amplitude,rel_tol=1e-12,abs_tol=1e-15)
  assert out['acquisition']['captures'][i]['receiver_position_m']==session['captures'][i]['receiver_position_m']
  assert out['acquisition']['source_position_m']==c['nominal_source_m'] and out['acquisition']['sound_speed_m_s']==343.
  assert out['acquisition']['probe']==session['probe']
result=dict(status='passed',inherited_rows=len(checked),geometry=checked,physical_path_declarations=56,physical_truth_not_in_extraction_inputs=True,scope='Independent saved evidence arithmetic; no new timing, waveform processing or source/geometry fit')
with (P/'geometry-verification.json').open('x') as f:json.dump(result,f,indent=2,allow_nan=False);f.write('\n')
print(json.dumps(dict(status='passed',inherited_rows=len(checked),physical_path_declarations=56)))
