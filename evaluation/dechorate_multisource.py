"""Frozen measured 4-source dEchorate evaluation; no truth enters fitting."""
import copy,csv,hashlib,json,sys,time
from pathlib import Path
import numpy as np
from scipy.signal import fftconvolve
from scipy.io import wavfile
ROOT = None
CORE = None
REFERENCE = None
CORE_COMMIT = None
h5py = None


def dump(p,o):p.write_text(json.dumps(o,indent=2,allow_nan=False)+'\n')
def digest(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def codehash():return {str(p.relative_to(CORE)):digest(p) for folder in ['echosight','evaluation'] for p in sorted((CORE/folder).glob('*.py'))}
def jsdigest(x):return hashlib.sha256(json.dumps(x,sort_keys=True,allow_nan=False).encode()).hexdigest()
def decode(x):return bytes(x).decode('utf8') if isinstance(x,(bytes,np.bytes_)) else str(x)
def poses():
 rows=list(csv.DictReader((ROOT/'data/positions.csv').open()))
 sources=[];receivers=[];centers=[]
 for s in range(1,5):
  row=next(r for r in rows if r['type']=='dir' and int(r['id'])==s)
  sources.append([float(row['x']),float(row['y']),2.355+float(row['z'])])
 for a in [5,6]:
  row=next(r for r in rows if r['type']=='array' and int(r['id'])==a)
  center=np.array([float(row['x']),float(row['y']),2.355+float(row['z'])]);centers.append(center)
  th=np.deg2rad(float(row['theta']));direction=np.array([np.cos(th),np.sin(th),0])
  receivers.extend(center+u*direction for u in [-.1225,-.0825,-.0325,.0325,.1325])
 return np.array(sources),np.array(receivers),np.array(centers)

def prepare():
 spec=json.loads((ROOT/'protocol.json').read_text());assert digest(ROOT/'protocol.json')==(ROOT/'FREEZE.sha256').read_text().split()[0]
 entries=json.loads((ROOT/'retrieval.json').read_text())['files'];audit=[];rir=[]
 for row in entries:
  p=ROOT/'data'/row['filename'];assert p.stat().st_size==row['bytes'] and digest(p)==row['sha256']
  if p.suffix!='.sofa':continue
  with h5py.File(p,'r') as f:
   metadata={str(k):decode(v) for k,v in f.attrs.items()}
   assert 'MIT' in metadata['License'] and 'Diego' in metadata['License']
   assert p.stem in metadata['Title']
   assert np.asarray(f['Data.IR']).shape==(1,5,48000)
   assert float(f['Data.SamplingRate'][0])==48000
   rir.extend(np.asarray(f['Data.IR'][0]))
   audit.append(dict(filename=p.name,sha256=row['sha256'],attributes=metadata,source_position_echo_refined=np.asarray(f['SourcePosition']).tolist(),receiver_position_echo_refined=np.asarray(f['ReceiverPosition']).tolist(),room_temperature_raw=np.asarray(f['RoomTemperature']).tolist()))
 # This metadata output is frozen before numerical fitting, including full licenses.
 dump(ROOT/'metadata-audit.json',audit)
 probe,config=generate_probe(spec['probe']);peak=max(float(np.max(abs(fftconvolve(probe,h)))) for h in rir);gain=.8/peak
 sources,receivers,centers=poses();cal=spec['conditional_calibration'];sessionpaths=[];nullpaths=[]
 for k,s in enumerate(sources):
  folder=ROOT/'recordings'/f'source{k+1}';folder.mkdir(parents=True,exist_ok=True)
  caps=[];nullcaps=[]
  for j,r in enumerate(receivers):
   p=folder/f'mic{j+21}.wav';y=fftconvolve(probe,rir[k*10+j])*gain;wavfile.write(p,48000,y.astype(np.float32))
   cap=dict(capture_id=f'mic{j+21}',device_id=f'microphone{j+21}',receiver_pose_group_id=f'microphone{j+21}',receiver_position_m=r.tolist(),receiver_position_std_m=cal['receiver_position_std_m'],recording_path=str(p),sample_rate_hz=48000,provenance='replayed',external_transform=dict(type='measured_rir_convolved_with_generated_probe',gain=gain,source_file=spec['files'][k*2+j//5]['filename'],float_bits=32,no_time_shift=True))
   caps.append(cap)
   null=folder/f'null{j+21}.wav';wavfile.write(null,48000,np.zeros_like(y,dtype=np.float32));nullcaps.append(dict(cap,recording_path=str(null)))
  session=dict(schema_version='1.0',session_id=f'dechorate-survey-source{k+1}',coordinate_frame_id='dechorate-beacon-metre-zup',source_position_m=s.tolist(),source_position_std_m=cal['source_position_std_m'],sound_speed_m_s=cal['sound_speed_m_s'],sound_speed_std_m_s=cal['sound_speed_std_m_s'],source_clock_scale=1.,source_clock_std_ppm=0.,probe=config,captures=caps)
  p=folder/'session.json';dump(p,session);sessionpaths.append(str(p))
  p=folder/'null-session.json';dump(p,dict(session,captures=nullcaps));nullpaths.append(str(p))
 bundle=dict(schema_version='1.0',scene_id='dechorate-room011111-survey-only',coordinate_frame_id='dechorate-beacon-metre-zup',scene_static=True,sessions=sessionpaths,shared_calibration=dict(effective_speed_m_s=cal['sound_speed_m_s'],effective_speed_std_m_s=cal['sound_speed_std_m_s'],covariance_assumption='explicit_source_pose_covariance_independent_speed',source_pose_joint_covariance_m2=(np.eye(12)*cal['source_position_std_m']**2).tolist()))
 dump(ROOT/'bundle.json',bundle);dump(ROOT/'null-bundle.json',dict(bundle,sessions=nullpaths))
 dump(ROOT/'preparation.json',dict(protocol_sha256=digest(ROOT/'protocol.json'),retrieval_sha256=digest(ROOT/'retrieval.json'),metadata_audit_sha256=digest(ROOT/'metadata-audit.json'),global_gain=gain,source_positions_m=sources.tolist(),receiver_positions_m=receivers.tolist(),source_singular_values_m=np.linalg.svd(sources-sources.mean(0),compute_uv=False).tolist(),receiver_singular_values_m=np.linalg.svd(receivers-receivers.mean(0),compute_uv=False).tolist(),source_code_sha256=codehash(),runner_sha256=digest(Path(__file__)),fitting_executed=False))
 print('prepared40measured+40nullraw; licenses verified; hashes pinned',flush=True)

def altered(processed,arm):
 result=copy.deepcopy(processed);sources,receivers,centers=poses();spec=json.loads((ROOT/'protocol.json').read_text());new=receivers.copy();ids=np.arange(10)
 if arm=='shuffled_geometry':ids=np.roll(ids,3);new=receivers[ids]
 else:
  sign=1 if arm.endswith('plus') else -1
  if '_yaw_' in arm:
   for a in range(2):
    th=np.deg2rad(spec['sensitivity']['yaw_deg']*sign*(1 if a==0 else -1));R=np.array([[np.cos(th),-np.sin(th),0],[np.sin(th),np.cos(th),0],[0,0,1]])
    new[a*5:a*5+5]=(receivers[a*5:a*5+5]-centers[a])@R.T+centers[a]
  else:
   axis='xyz'.index(arm.split('_')[1]);new[:5,axis]+=.02*sign;new[5:,axis]-=.02*sign
 for item in result:
  for target in [item['session']['captures'],item['observations']]:
   for j,o in enumerate(target):o['receiver_position_m']=new[j].tolist();o['receiver_pose_group_id']=f'microphone{ids[j]+21}'
 return result

def acceptance_failures(result, metrics, arm, runtime_seconds, spec):
 """Apply the frozen geometry and output-semantics gates after fitting only."""
 gates=spec['acceptance'];failures=[]
 if arm in ['null','shuffled_geometry']:
  if metrics['predicted_count']!=0:failures.append('definitive_geometry_in_control')
 else:
  if metrics['matched_count']<gates['minimum_matched_room_planes']:failures.append('insufficient_room_planes')
  if metrics['horizontal_matched']<gates['minimum_horizontal_matched']:failures.append('insufficient_horizontal_planes')
  if metrics['false_surfaces']>gates['maximum_unmatched_definitive_planes']:failures.append('unmatched_definitive_planes')
 if runtime_seconds>gates['maximum_runtime_seconds']:failures.append('runtime_limit')
 if gates['forbid_enclosure_claim'] and any(
     surface.get('extent_status')!='unknown' or
     surface.get('mesh_semantics')!='reflection_support_convex_hull_not_physical_edges'
     for surface in result.get('surfaces',[])):
  failures.append('unsupported_physical_extent_or_enclosure_semantics')
 return failures

def fit():
 spec=json.loads((ROOT/'protocol.json').read_text());before=codehash();prep=json.loads((ROOT/'preparation.json').read_text());assert before==prep['source_code_sha256'];assert prep['protocol_sha256']==digest(ROOT/'protocol.json')
 out=ROOT/'results';out.mkdir(exist_ok=True);rows=[];bundle=json.loads((ROOT/'bundle.json').read_text())
 def timed(label,fn,scope):
  start=time.perf_counter();r=fn();sec=time.perf_counter()-start;dump(out/f'{label}.json',r);rows.append(dict(arm=label,status=r['status'],runtime_seconds=sec,runtime_scope=scope,surface_count=len(r.get('surfaces',[])),hypothesis_count=len(r.get('hypotheses',[])),diagnostics=r.get('diagnostics',[])));dump(out/'progress.json',rows);print(label,r['status'],len(r.get('surfaces',[])),round(sec,3),flush=True);return r
 main=timed('joint_mapper',lambda:process_scene_bundle(ROOT/'bundle.json'),'raw_recording_to_result');processed=main['processed_sessions'];inputhash=jsdigest(processed)
 timed('joint_plane_grid',lambda:infer_scene_bundle(processed,bundle,method='plane_grid'),'same_observations_inference')
 timed('independent_source_consensus',lambda:independent_consensus(processed),'same_observations_inference')
 for i,item in enumerate(processed):
  timed(f'single_source_mapper_{i+1}',lambda item=item:infer_scene(item['session'],item['observations']),'same_observations_inference')
  timed(f'single_source_first_echo_{i+1}',lambda item=item:infer_first_echo(item['session'],item['observations']),'same_observations_inference')
 timed('null',lambda:process_scene_bundle(ROOT/'null-bundle.json'),'raw_recording_to_result')
 shuffled=altered(processed,'shuffled_geometry');timed('shuffled_geometry',lambda:infer_scene_bundle(shuffled,bundle),'same_recording_observations_wrong_poses')
 for arm in spec['sensitivity']['arms']:
  changed=altered(processed,arm);timed(arm,lambda changed=changed:infer_scene_bundle(changed,bundle),'same_observations_rigid_array_sensitivity')
 assert inputhash==jsdigest(processed)
 # Evaluation reference planes loaded ONLY after every fit has finished.
 dims=np.asarray(REFERENCE['room_size_m'])
 truth=dict(surfaces=[dict(surface_id=f'{axis}-{side}',normal=np.eye(3)[axis].tolist(),offset_m=float(value)) for axis in range(3) for side,value in [('low',0),('high',dims[axis])]])
 for row in rows:
  result=json.loads((out/f'{row["arm"]}.json').read_text());m=score_surfaces(result,truth,**spec['matching'])
  for match in m['matches']:
   match['offset_95pct_covered']=None;match['normal_95pct_covered']=None
  row['metrics']=m;row['missed_truth_ids']=[t['surface_id'] for t in truth['surfaces'] if t['surface_id'] not in [a['truth_id'] for a in m['matches']]]
  row['unmatched_semantics']='Outside suppliedroomplanes, not independentlyproven nonexistentstructure.'
  row['acceptance_failures']=acceptance_failures(result,m,row['arm'],row['runtime_seconds'],spec)
  row['passed']=not row['acceptance_failures']
  row['residuals']=[dict(surface_id=s.get('surface_id'),support_count=len(s.get('support',[])),rms_s=float(np.sqrt(np.mean([a['residual_s']**2 for a in s['support']]))),maximum_abs_s=max(abs(a['residual_s']) for a in s['support'])) for s in result.get('surfaces',[]) if s.get('support')]
 recordings=[]
 for item in processed:
  recordings.append(dict(session_id=item['session']['session_id'],recordings=[{k:o.get(k) for k in ['capture_id','status','recording_sha256','waveform_sha256','clock','direct_arrival_receiver_s','diagnostics']}|{'candidate_count':len(o.get('candidates',[]))} for o in item['observations']]))
 report=dict(protocol_sha256=digest(ROOT/'protocol.json'),core_commit=CORE_COMMIT,source_code_sha256=before,source_unchanged=before==codehash(),runner_sha256=digest(Path(__file__)),shared_processed_input_sha256=inputhash,shared_input_unchanged=True,rows=rows,recordings=recordings,passed=all(r['passed'] for r in rows if r['arm'] in ['joint_mapper','null','shuffled_geometry']),uncertainty_qualified=False,uncertainty_limits=spec['uncertainty'],reference_dimensions_m=dims.tolist(),evidence_class=spec['evidence_class'])
 dump(out/'report.json',report);print('final',report['passed'],flush=True);return report


def retrieve():
    """Explicit 14.1 MB download; exact pinned lengths and hashes, no overwrite."""
    from urllib.request import urlopen
    manifest=json.loads(Path(__file__).with_name('dechorate_multisource_manifest.json').read_text())
    data=ROOT/'data';data.mkdir(parents=True,exist_ok=True)
    for row in manifest['files']:
        path=data/row['filename']
        if not path.exists():
            with urlopen(row['source_url'],timeout=60) as response:
                payload=response.read(row['bytes']+1)
            if len(payload)!=row['bytes'] or hashlib.sha256(payload).hexdigest()!=row['sha256']:
                raise ValueError('Download differs from frozen bytes/hash: '+row['filename'])
            path.write_bytes(payload)
        if path.stat().st_size!=row['bytes'] or digest(path)!=row['sha256']:
            raise ValueError('Existing data differs from frozen bytes/hash: '+row['filename'])
    dump(ROOT/'retrieval.json',manifest)


def configure(args):
    global ROOT,CORE,REFERENCE,CORE_COMMIT,h5py
    global generate_probe,process_scene_bundle,infer_scene_bundle,infer_scene,infer_first_echo,independent_consensus,score_surfaces
    import importlib
    ROOT=Path(args.workspace).resolve();ROOT.mkdir(parents=True,exist_ok=True)
    CORE=Path(args.core).resolve();CORE_COMMIT=args.core_commit
    manifest=json.loads(Path(__file__).with_name('dechorate_multisource_manifest.json').read_text())
    REFERENCE=manifest['reference']
    # Optional fixture-reader runtime is isolated from the processing core.
    if args.h5py_path:sys.path.insert(0,str(Path(args.h5py_path).resolve()))
    sys.path.insert(0,str(CORE))
    h5py=importlib.import_module('h5py')
    signals=importlib.import_module('echosight.signals');multi=importlib.import_module('echosight.multisource');inference=importlib.import_module('echosight.inference')
    # The invoking evaluation package may already be cached by `python -m`.
    # Load numerical comparators from the chosen immutable core explicitly.
    def core_evaluation(name):
        import importlib.util
        spec=importlib.util.spec_from_file_location('echosight_frozen_'+name,CORE/'evaluation'/f'{name}.py')
        module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
        return module
    baseline=core_evaluation('source_relocation_baseline');metrics=core_evaluation('metrics')
    generate_probe=signals.generate_probe;process_scene_bundle=multi.process_scene_bundle;infer_scene_bundle=multi.infer_scene_bundle
    infer_scene=inference.infer_scene;infer_first_echo=inference.infer_first_echo
    independent_consensus=baseline.independent_consensus;score_surfaces=metrics.score_surfaces
    if not Path(multi.__file__).resolve().is_relative_to(CORE):raise ValueError('Wrong processing core imported')
    actual=codehash();expected=manifest['core_sha256']
    # New evaluation files do not change the numerical core. Compare original paths.
    if not args.allow_different_core and any(actual.get(k)!=v for k,v in expected.items()):
        raise ValueError('Core differs from evaluated de8442b; select immutable snapshot or explicitly use --allow-different-core for a NEW comparison')
    for origin,target in [('dechorate_multisource_protocol.json','protocol.json'),('dechorate_multisource_diagnostic_protocol.json','diagnostic-protocol.json')]:
        payload=Path(__file__).with_name(origin).read_bytes();path=ROOT/target
        if path.exists() and path.read_bytes()!=payload:raise ValueError('Refuse to overwrite changed frozen protocol')
        path.write_bytes(payload)
    (ROOT/'FREEZE.sha256').write_text(digest(ROOT/'protocol.json')+'  protocol.json\n')
    if not (ROOT/'retrieval.json').exists():dump(ROOT/'retrieval.json',manifest)


def main():
    import argparse
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action',choices=['retrieve','prepare','fit'])
    parser.add_argument('--workspace',required=True)
    parser.add_argument('--core',default=str(Path(__file__).resolve().parents[1]))
    parser.add_argument('--core-commit',default='de8442b2dd088c036d2b92eaeaf29a1273785795',help='Provenance label; code hashes are authoritative')
    parser.add_argument('--allow-different-core',action='store_true',help='Explicit new-code comparison; preserves frozen criteria')
    parser.add_argument('--h5py-path',help='Optional path to existing isolated fixture-reader package directory')
    args=parser.parse_args();configure(args)
    if args.action=='retrieve':retrieve()
    elif args.action=='prepare':prepare()
    else:raise SystemExit(0 if fit()['passed'] else 1)


if __name__=='__main__':main()
