"""One bounded saved-map follow-up. check never processes or generates audio.

Freeze only after review; render/run each require its exact approved digest.
All artifacts, including partial attempts, are preserved. No retry or seed search.
"""
from pathlib import Path
import argparse, ast, copy, hashlib, importlib.util, json, platform, subprocess, sys, time
P=Path(__file__).resolve().parent
REPO=None

def read(p): return json.loads(Path(p).read_text())
def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def save(p,x):
    with Path(p).open('x') as f: json.dump(x,f,indent=2,allow_nan=False);f.write('\n')
def load_module(path,name):
    spec=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m

def environment():
    import numpy, scipy
    return dict(python=platform.python_version(),numpy=numpy.__version__,scipy=scipy.__version__,python_executable_sha256=sha(Path(sys.executable).resolve()))

def cfg(): return read(P/'settings.json')
def base(): return REPO/'evidence/calibration-room-transfer/replay'
def inputs():
    files={f'local/{p.name}':p for p in P.iterdir() if p.name in ('run.py','settings.json','PROTOCOL.md','proposed-catalog.json','design-assessment.json','policy.json','saved-map-oracle-diagnostic.json')}
    for p in (REPO/'echosight').rglob('*.py'):files[f'repo/{p.relative_to(REPO)}']=p
    for rel in ('evaluation/path_interpretations.py','evaluation/held_path_preflight.py','evaluation/metrics.py','requirements.txt','requirements-test.txt'):
        files[f'repo/{rel}']=REPO/rel
    for rel in read(base()/'manifest.json')['package_sha256']:
        files[f'replay/{rel}']=base()/rel
    files['replay/manifest.json']=base()/'manifest.json'
    return dict(sorted(files.items()))
def hashes():return {name:sha(p) for name,p in inputs().items()}

def check():
    import numpy as np
    c=cfg();old=read(base()/'settings.json');design=read(P/'design-assessment.json');catalog=read(P/'proposed-catalog.json')
    if c['seeds']!=[2821,2833] or c['methods']!=old['methods']:raise ValueError('Fixed instances/methods changed')
    allowed={'runtime_commit','historical_runtime_commit','withheld_positions_m','followup_survey_stream_namespace','followup_audio_stream_namespace','uncertainty_bound_status','execution_scope'}
    if any(c[k]!=v for k,v in old.items() if k not in allowed):raise ValueError('Original assumption/threshold changed')
    if c['withheld_positions_m']!=[row['position_m'] for row in design['selected']]:raise ValueError('Selected positions changed')
    if (c['followup_survey_stream_namespace'],c['followup_audio_stream_namespace'])!=(419740,419741):raise ValueError('Declared streams changed')
    oldstreams={old[k] for k in ('mapping_survey_stream_namespace','room_audio_stream_namespace','null_audio_stream_namespace')}
    if oldstreams & {419740,419741}:raise ValueError('Stream collision')
    if c['uncertainty_bound_status']!='UNKNOWN':raise ValueError('Missing uncertainty cannot be certified')
    if len(c['withheld_positions_m'])!=4 or np.linalg.matrix_rank(np.array(c['withheld_positions_m'])-np.mean(c['withheld_positions_m'],axis=0))!=3:raise ValueError('Held geometry incomplete/degenerate')
    preflight=load_module(REPO/'evaluation/held_path_preflight.py','preflight').check_plan(catalog)
    if not preflight['ideal_gate_pass'] or preflight['unique']!=24:raise ValueError('Ideal design is incompatible')
    # Independently recompute every declared ideal delay from fixed geometry.
    source=np.array(c['physical_source_m']);speed=c['effective_speed_m_s']
    for receiver,cap in zip(c['withheld_positions_m'],catalog['captures']):
        receiver=np.array(receiver)
        for row in cap['paths']:
            _,axis,side=row['path_id'].split('-');axis=int(axis);side=int(side)
            image=source.copy();image[axis]=2*side*c['room_size_m'][axis]-source[axis]
            delay=(np.linalg.norm(receiver-image)-np.linalg.norm(receiver-source))/speed
            if abs(delay-row['excess_delay_s'])>1e-14:raise ValueError('Catalog geometry changed')
    manifest=read(base()/'manifest.json')
    for rel,h in manifest['package_sha256'].items():
        if sha(base()/rel)!=h:raise ValueError(f'Saved package changed: {rel}')
    head=subprocess.check_output(['git','rev-parse','HEAD'],cwd=REPO,text=True).strip()
    if head!=c['runtime_commit']:raise ValueError('Wrong current runtime commit')
    runtime={}
    for name,p in inputs().items():
        if name.startswith('repo/'):
            committed=subprocess.check_output(['git','show',head+':'+name[5:]],cwd=REPO)
            if hashlib.sha256(committed).hexdigest()!=sha(p):raise ValueError(f'Dirty runtime: {name}')
            runtime[name]=sha(p)
    ast.parse((P/'run.py').read_text())
    return dict(status='passed',ideal_preflight=preflight,uncertainty_bound_status='UNKNOWN',
        uncertainty_scope='No validated extraction/systematic-error bound or correlated prediction interval; empirical development permitted, no guarantee.',
        runtime_commit=head,environment=environment(),input_hashes=hashes(),audio_generated=False,audio_processed=False,mapping_executed=False)

def freeze():
    receipt=check();save(P/'static-check.json',receipt)
    save(P/'freeze.json',dict(input_hashes=hashes(),static_check_sha256=sha(P/'static-check.json'),runtime_commit=cfg()['runtime_commit'],execution_authorized=False))
    print(sha(P/'freeze.json'))
def verify(approved):
    if not isinstance(approved,str) or not (P/'freeze.json').is_file() or approved!=sha(P/'freeze.json'):raise ValueError('Exact root-approved freeze digest required')
    f=read(P/'freeze.json')
    if f['input_hashes']!=hashes() or f['static_check_sha256']!=sha(P/'static-check.json'):raise ValueError('Frozen inputs changed')
    if read(P/'static-check.json')['environment']!=environment():raise ValueError('Frozen interpreter/dependency versions changed')

def render_case(seed):
    import numpy as np
    from scipy.signal import fftconvolve
    from scipy.io import wavfile
    c=cfg();h=load_module(REPO/'evaluation/path_interpretations.py','renderer');folder=P/'raw'/str(seed);folder.mkdir()
    points=np.array(c['withheld_positions_m']);rng=np.random.default_rng(np.random.SeedSequence([419741,seed]));survey=np.random.default_rng(np.random.SeedSequence([419740,seed]))
    surveyed=points+survey.normal(0,c['receiver_survey_std_m'],points.shape)
    source=np.array(c['physical_source_m']);v=c['effective_speed_m_s'];fs=c['probe']['sample_rate_hz']
    emitted,probe=h.probe(c['probe']);emitted=fftconvolve(emitted,c['source_fir'])
    session=dict(schema_version='1.0',session_id=f'held-followup-{seed}',coordinate_frame_id='exact-synthetic-frame',source_position_m=c['nominal_source_m'],source_position_std_m=.01,sound_speed_m_s=343.,sound_speed_std_m_s=.6,source_clock_scale=1.,source_clock_std_ppm=80.,probe=probe,captures=[])
    truth=[]
    for i,r in enumerate(points):
        direct=float(np.linalg.norm(r-source));paths=[dict(delay_s=direct/v,amplitude=c['direct_amplitude'],kind='direct',fir_offsets_samples=[0],fir_coefficients=[1.])]
        for axis in range(3):
            for side in (0,1):
                length,_=h.mirror(source,r,np.eye(3)[axis],side*c['room_size_m'][axis]);paths.append(dict(delay_s=length/v,amplitude=c['direct_amplitude']*c['room_reflection_coefficient']*direct/length,kind=f'wall-{axis}-{side}',fir_offsets_samples=[0],fir_coefficients=[1.]))
        wave=fftconvolve(emitted,h.impulse(paths,fs));wave=fftconvolve(wave,c['receiver_fir'])[:len(wave)]
        alpha=1+rng.uniform(*c['recording_alpha_ppm_bounds'])*1e-6;offset=rng.uniform(*c['recording_offset_s_bounds']);times=np.arange(len(wave)+round(c['tail_capture_s']*fs))/fs
        clean=np.interp((times-offset)/alpha,np.arange(len(wave))/fs,wave,left=0,right=0);samples=c['recording_scale']*(clean+rng.normal(0,c['noise_std'],len(clean)))
        if max(abs(samples))>=.95:raise ValueError('Overload: preserve partial tree; no rescale/replacement')
        name=f'capture-{i:02d}.wav';wavfile.write(folder/name,fs,np.rint(samples*32767).astype('<i2'))
        session['captures'].append(dict(capture_id=f'proposed-held-{i:02d}',receiver_position_m=surveyed[i].tolist(),receiver_position_std_m=c['receiver_survey_std_m'],receiver_pose_group_id=f'followup-{seed}-{i}',device_id=f'receiver-{i}',recording_path=name,sha256=sha(folder/name),provenance='simulated'))
        truth.append(dict(capture_id=f'proposed-held-{i:02d}',position_m=r.tolist(),paths=paths,alpha=alpha,offset_s=offset,recording_sha256=sha(folder/name)))
    save(folder/'session.json',session);save(folder/'truth.json',truth)
    save(folder/'manifest.json',{p.name:sha(p) for p in sorted(folder.iterdir())})
def render(approved):
    verify(approved)
    if (P/'raw').exists() or (P/'render-start.json').exists():raise FileExistsError('Preserve existing render attempt')
    save(P/'render-start.json',dict(freeze_sha256=approved));(P/'raw').mkdir()
    for seed in cfg()['seeds']:render_case(seed)
    save(P/'render-complete.json',dict(freeze_sha256=approved,manifests={str(p.relative_to(P)):sha(p) for p in sorted((P/'raw').glob('*/manifest.json'))}))

def validate_extraction(out):
    if out.get('status')!='cancelled' or out.get('surfaces') or len(out.get('observations',[]))!=4:raise ValueError('Extraction did not stop before mapping with four observations')
    if [o['capture_id'] for o in out['observations']]!=[f'proposed-held-{i:02d}' for i in range(4)]:raise ValueError('Observation identities changed')
def held_metrics(fit,out):
    # Exact frozen association code, then make incomplete-set statistics explicit.
    gates=load_module(base()/'frozen_gates.py','frozen_gates');gates.cfg=cfg
    metrics=gates.withheld_metrics(dict(result=fit['result'],withheld_extraction=out))
    metrics['unique_subset_rms_s']=metrics.pop('rms_s');metrics['unique_subset_max_abs_s']=metrics.pop('max_abs_s')
    metrics['complete_rms_s']=metrics['unique_subset_rms_s'] if metrics['complete'] else None
    metrics['complete_max_abs_s']=metrics['unique_subset_max_abs_s'] if metrics['complete'] else None
    return metrics

def summarize(extractions):
    old=read(base()/'expected-results.json');c=cfg();rows=[]
    for seed in c['seeds']:
        for method in c['methods']:
            fit=read(base()/f'fits/room-{seed}-{method}.json');previous=next(r for r in old['rows'] if (r['seed'],r['family'],r['method'])==(seed,'room',method));m=held_metrics(fit,extractions[seed]);g=previous['geometry']
            geometry_ok=g['matched']==6 and g['horizontal']==2 and g['unmatched']==0
            rows.append(dict(seed=seed,method=method,withheld=m,geometry=g,all_mapping_recordings_accepted=previous['all_mapping_recordings_accepted'],geometry_and_prediction_pass=bool(geometry_ok and m['passed'] and previous['all_mapping_recordings_accepted']),runtime_pass=previous['runtime_pass'],raw_processing_s=previous['raw_processing_s'],mapping_runtime_commit=c['historical_runtime_commit'],mapping_timing_freshly_measured=False,observations_sha256=sha(P/'extractions'/f'{seed}.json')))
    benefits=[]
    for seed in c['seeds']:
        cases={r['method']:r for r in rows if r['seed']==seed};j=cases['joint_mapper'];comparisons=[]
        for method in ('nominal_mapper','one_x_mapper'):
            b=cases[method];hj,hb=j['withheld'],b['withheld'];gj,gb=j['geometry'],b['geometry'];comparable=hj['complete'] and hb['complete'] and gj['matched']==gb['matched']==6
            rms_gain=hb['complete_rms_s']-hj['complete_rms_s'] if comparable else None;anchor_gain=gb['six_plane_mean_anchor_error_m']-gj['six_plane_mean_anchor_error_m'] if comparable else None
            no_regression=gj['unmatched']<=gb['unmatched'] and gj['missed']<=gb['missed'];gain=j['geometry_and_prediction_pass'] and no_regression and (not b['geometry_and_prediction_pass'] or (comparable and rms_gain>=c['acceptance']['minimum_withheld_rms_gain_s'] and anchor_gain>=c['acceptance']['minimum_mean_anchor_gain_m']))
            comparisons.append(dict(comparator=method,complete_rms_gain_s=rms_gain,mean_anchor_gain_m=anchor_gain,comparator_complete_gate_failed=not b['geometry_and_prediction_pass'],no_false_or_missed_regression=no_regression,gain=bool(gain)))
        benefits.append(dict(seed=seed,comparisons=comparisons,benefit=all(x['gain'] for x in comparisons)))
    nulls=[r for r in old['rows'] if r['family']=='direct_only'];null_pass=all(r['geometry_and_prediction_pass'] and r['runtime_pass'] for r in nulls if r['method']=='joint_mapper')
    joints=[r for r in rows if r['method']=='joint_mapper'];transfer=all(r['geometry_and_prediction_pass'] and r['runtime_pass'] for r in joints) and null_pass
    recall=sum(r['geometry']['matched'] for r in joints)>sum(r['geometry']['matched'] for r in rows if r['method']=='joint_first_echo')
    return dict(rows=rows,benefits=benefits,retained_nulls=nulls,retained_original_transfer_pass=old['transfer_pass'],retained_original_promotion_pass=old['promotion_criteria_pass'],transfer_pass=transfer,promotion_criteria_pass=transfer and recall and all(b['benefit'] for b in benefits),physical_validation=False,uncertainty_bound_status='UNKNOWN',scope='Separate eight-record synthetic development follow-up, never automatic feature or hardware promotion.')

def run(approved):
    verify(approved);complete=read(P/'render-complete.json')
    if complete['freeze_sha256']!=approved:raise ValueError('Wrong render freeze')
    for rel,h in complete['manifests'].items():
        p=P/rel
        if sha(p)!=h or any(sha(p.parent/name)!=value for name,value in read(p).items()):raise ValueError('Rendered bytes changed')
    if (P/'run-start.json').exists() or (P/'extractions').exists():raise FileExistsError('Preserve previous or partial run')
    import numpy as np, scipy
    save(P/'run-start.json',dict(freeze_sha256=approved,python=sys.version,platform=platform.platform(),numpy=np.__version__,scipy=scipy.__version__))
    (P/'extractions').mkdir();sys.path.insert(0,str(REPO))
    from echosight.storage import load_session
    from echosight.pipeline import process_session
    extractions={}
    for seed in cfg()['seeds']:
        state={'stop':False}
        def progress(fraction,message=''):
            if fraction>=.65:state['stop']=True
        started=time.perf_counter();out=process_session(load_session(P/'raw'/str(seed)/'session.json'),cancel=lambda:state['stop'],progress=progress)
        elapsed=time.perf_counter()-started
        save(P/'extractions'/f'{seed}.json',out)
        save(P/'extractions'/f'{seed}-timing.json',dict(seconds=elapsed,scope='New held extraction only, excludes serialization and historical mapping timing'))
        validate_extraction(out);extractions[seed]=out
    save(P/'results.json',summarize(extractions));verify(approved)

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('action',choices=['check','freeze','render','run']);p.add_argument('--repo',type=Path,required=True);p.add_argument('--approved-freeze');a=p.parse_args();REPO=a.repo.resolve()
    if a.action=='check':print(json.dumps(check(),indent=2))
    elif a.action=='freeze':freeze()
    elif a.action=='render':render(a.approved_freeze)
    else:run(a.approved_freeze)
