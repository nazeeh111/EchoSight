"""Frozen two-fit transfer experiment. freeze/check are read-only except receipts.

render/run require the exact coordinator-approved freeze digest and refuse reruns.
"""
from pathlib import Path
import argparse, ast, copy, hashlib, importlib.util, json, platform, subprocess, sys, time
import numpy as np

P=Path(__file__).resolve().parent
ROOT=P.parents[1]
REF=ROOT/'work/source-calibration-mismatch/run-v2/raw'
JOINT=ROOT/'evidence/joint-reference-trial/results.json'

def read(p): return json.loads(Path(p).read_text())
def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def digest(x): return hashlib.sha256(json.dumps(x,sort_keys=True,allow_nan=False).encode()).hexdigest()
def save(p,x):
    p=Path(p);p.parent.mkdir(parents=True,exist_ok=True)
    if p.exists(): raise FileExistsError(f'Preserve prior artifact: {p.name}')
    p.write_text(json.dumps(x,indent=2,allow_nan=False)+'\n')
def cfg(): return read(P/'settings.json')
def runtime_files():
    return sorted((ROOT/'echosight').glob('*.py'))
def input_paths():
    paths=[P/'run.py',P/'settings.json',P/'PROTOCOL.md',JOINT,
           ROOT/'evaluation/path_interpretations.py',ROOT/'evaluation/metrics.py',
           ROOT/'work/source-calibration-mismatch/run_v2.py',
           ROOT/'evidence/joint-reference-trial/PROTOCOL.md',ROOT/'evidence/joint-reference-trial/freeze.json']
    for seed in cfg()['seeds']:
        for plane in ('x','y'):
            folder=REF/f'single-{seed}-{plane}'
            paths.extend(folder/name for name in ('session.json','reference.json','calibration.json','manifest.json','truth.json'))
            paths.extend(folder/name for name in read(folder/'manifest.json')['raw'])
    return sorted(set(paths+runtime_files()))
def hashes(): return {str(p.relative_to(ROOT)):sha(p) for p in input_paths()}

def check():
    """No renderer, optimizer, pipeline or waveform helper executes."""
    c=cfg();assert c['seeds']==[2821,2833]
    ast.parse((P/'run.py').read_text());compile((P/'run.py').read_text(),str(P/'run.py'),'exec')
    fits=read(JOINT);assert fits['all_single_controls_passed']
    assert all(not a['admitted'] for a in fits['admissions'] if a['pattern']!='single')
    assert [f['seed'] for f in fits['fits']]==c['seeds']
    points=np.array(c['mapping_positions_m']+c['withheld_positions_m']);size=np.array(c['room_size_m'])
    assert points.shape==(16,3) and np.all(points>0) and np.all(points<size)
    assert np.linalg.matrix_rank(points[:12]-points[:12].mean(0))==3
    assert np.linalg.matrix_rank(points[12:]-points[12:].mean(0))==3
    assert min(np.linalg.norm(points[i]-points[j]) for i in range(16) for j in range(i))>.01
    assert len(set(c[k] for k in ('mapping_survey_stream_namespace','room_audio_stream_namespace','null_audio_stream_namespace')))==3
    committed=[]
    for path in runtime_files():
        rel=str(path.relative_to(ROOT))
        original=subprocess.check_output(['git','show',c['runtime_commit']+':'+rel],cwd=ROOT)
        assert hashlib.sha256(original).hexdigest()==sha(path),f'Runtime changed: {rel}'
        committed.append(rel)
    for seed in c['seeds']:
        f=next(f for f in fits['fits'] if f['seed']==seed)
        assert f['passed'] and np.linalg.eigvalsh(np.array(f['parameter_covariance'])).min()>0
        for plane in ('x','y'):
            folder=REF/f'single-{seed}-{plane}';s=read(folder/'session.json');t=read(folder/'truth.json');m=read(folder/'manifest.json')
            assert np.allclose(t['primary_m'],c['physical_source_m'],rtol=0,atol=1e-14)
            assert t['effective_speed_m_s']==c['effective_speed_m_s'] and t['pattern']=='single'
            assert s['source_position_m']==c['nominal_source_m'] and s['probe']==c['probe']
            assert read(folder/'calibration.json')['status']=='calibration_proposal'
            assert sha(folder/'truth.json')==m['truth_sha256']
            assert all(sha(folder/name)==h for name,h in m['raw'].items())
    return dict(status='static_checks_passed',source_config_verified_against_retained_inputs=True,
                runtime_commit=c['runtime_commit'],runtime_files_checked=len(committed),
                generation_executed=False,calibration_fit_executed=False,mapping_executed=False,
                limitations='Syntax, fixed settings, input integrity and runtime identity only. Renderer and fit workers have not executed.')

def freeze():
    receipt=check();save(P/'static-check.json',receipt)
    save(P/'freeze.json',dict(schema_version='1.0',input_hashes=hashes(),static_check_sha256=sha(P/'static-check.json'),
         runtime_commit=cfg()['runtime_commit'],generation_executed=False,execution_authorized=False))
    print(sha(P/'freeze.json'))

def verify(approved):
    if approved!=sha(P/'freeze.json'): raise ValueError('Exact approved freeze digest required')
    frozen=read(P/'freeze.json')
    if hashes()!=frozen['input_hashes']: raise ValueError('Frozen input bytes changed; stop for review')
    if sha(P/'static-check.json')!=frozen['static_check_sha256']: raise ValueError('Static receipt changed')
    return frozen

def helper():
    # Reuse fixed existing independent waveform arithmetic; no production synthesis.
    spec=importlib.util.spec_from_file_location('transfer_renderer_helper',ROOT/'evaluation/path_interpretations.py')
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);return module

def render_case(seed,family):
    from scipy.signal import fftconvolve
    from scipy.io import wavfile
    c=cfg();h=helper();folder=P/'raw'/f'{family}-{seed}'
    folder.mkdir(parents=True,exist_ok=False)
    allpoints=np.array(c['mapping_positions_m']+c['withheld_positions_m'])
    points=allpoints if family=='room' else allpoints[:12]
    survey_rng=np.random.default_rng(np.random.SeedSequence([c['mapping_survey_stream_namespace'],seed]))
    surveyed=allpoints+survey_rng.normal(0,c['receiver_survey_std_m'],allpoints.shape)
    namespace=c['room_audio_stream_namespace'] if family=='room' else c['null_audio_stream_namespace']
    rng=np.random.default_rng(np.random.SeedSequence([namespace,seed]))
    source=np.array(c['physical_source_m']);v=c['effective_speed_m_s'];fs=c['probe']['sample_rate_hz']
    emitted,probe=h.probe(c['probe']);emitted=fftconvolve(emitted,c['source_fir'])
    planes=[dict(surface_id=f'wall-{axis}-{side}',normal=np.eye(3)[axis].tolist(),offset_m=float(side*c['room_size_m'][axis]),
                 anchor_m=[float(side*c['room_size_m'][j]) if j==axis else c['room_size_m'][j]/2 for j in range(3)])
            for axis in range(3) for side in (0,1)] if family=='room' else []
    truth=dict(family=family,seed=seed,source_position_m=source.tolist(),effective_speed_m_s=v,surfaces=planes,captures=[],
               source_model='Exact retained V2 point-source FIR and speed; no physical route claim')
    sessions={part:dict(schema_version='1.0',session_id=f'transfer-{family}-{seed}-{part}',coordinate_frame_id='exact-synthetic-frame',
        source_position_m=c['nominal_source_m'],source_position_std_m=.01,sound_speed_m_s=343.,sound_speed_std_m_s=.6,
        source_clock_scale=1.,source_clock_std_ppm=80.,probe=probe,captures=[]) for part in ('mapping','withheld')}
    for i,r in enumerate(points):
        direct=float(np.linalg.norm(r-source));paths=[dict(delay_s=direct/v,amplitude=c['direct_amplitude'],kind='direct',fir_offsets_samples=[0],fir_coefficients=[1.])]
        for plane in planes:
            length,_=h.mirror(source,r,np.array(plane['normal']),plane['offset_m'])
            paths.append(dict(delay_s=length/v,amplitude=c['direct_amplitude']*c['room_reflection_coefficient']*direct/length,
                              kind=plane['surface_id'],fir_offsets_samples=[0],fir_coefficients=[1.]))
        wave=fftconvolve(emitted,h.impulse(paths,fs));wave=fftconvolve(wave,c['receiver_fir'])[:len(wave)]
        alpha=1+rng.uniform(*c['recording_alpha_ppm_bounds'])*1e-6;offset=rng.uniform(*c['recording_offset_s_bounds'])
        times=np.arange(len(wave)+round(c['tail_capture_s']*fs))/fs
        clean=np.interp((times-offset)/alpha,np.arange(len(wave))/fs,wave,left=0,right=0)
        samples=c['recording_scale']*(clean+rng.normal(0,c['noise_std'],len(clean)))
        if max(abs(samples))>=.95: raise ValueError('Renderer overload; no normalization or seed replacement')
        name=f'capture-{i:02d}.wav';wavfile.write(folder/name,fs,np.rint(samples*32767).astype('<i2'))
        part='mapping' if i<12 else 'withheld'
        sessions[part]['captures'].append(dict(capture_id=f'capture-{i:02d}',receiver_position_m=surveyed[i].tolist(),
          receiver_position_std_m=c['receiver_survey_std_m'],receiver_pose_group_id=f'new-survey-{seed}-{i}',
          device_id=f'receiver-{i%4}',recording_path=name,sha256=sha(folder/name),provenance='simulated'))
        truth['captures'].append(dict(capture_id=f'capture-{i:02d}',position_m=r.tolist(),paths=paths,alpha=alpha,offset_s=offset,
                                       recording_sha256=sha(folder/name),peak_absolute_before_pcm=float(max(abs(samples)))))
    save(folder/'mapping.json',sessions['mapping'])
    if family=='room': save(folder/'withheld.json',sessions['withheld'])
    save(folder/'truth.json',truth)
    save(folder/'manifest.json',dict(seed=seed,family=family,freeze_sha256=sha(P/'freeze.json'),
        files={p.name:sha(p) for p in sorted(folder.iterdir())},waveforms=len(points)))

def render(approved):
    verify(approved)
    if (P/'raw').exists(): raise FileExistsError('Raw tree already exists; preserve even partial generation')
    save(P/'render-start.json',dict(freeze_sha256=approved))
    for seed in cfg()['seeds']:
        for family in ('room','direct_only'): render_case(seed,family)
    save(P/'render-complete.json',dict(freeze_sha256=approved,manifests={str(p.relative_to(P)):sha(p) for p in sorted((P/'raw').glob('*/manifest.json'))}))

def calibration(seed,method):
    # No generating truth or calibration fitter is accessed by this boundary.
    if method.startswith('nominal'): return {}
    if method.startswith('one_x'): return read(REF/f'single-{seed}-x/calibration.json')['calibration']
    f=next(f for f in read(JOINT)['fits'] if f['seed']==seed)
    return dict(source_position_m=f['source_position_m'],effective_speed_m_s=f['effective_speed_m_s'],
                source_effective_speed_covariance=f['parameter_covariance'])

def extract_withheld(session):
    """Use existing admission pipeline; its public cancellation boundary stops inference.

    The artifact remains explicitly cancelled-after-extraction. Only observations
    feed the prospective prediction check; no geometry is fitted to held audio.
    """
    from echosight.pipeline import process_session
    state={'stop':False}
    def progress(fraction,message=''):
        if fraction>=.65: state['stop']=True
    out=process_session(session,cancel=lambda:state['stop'],progress=progress)
    assert out['status']=='cancelled' and not out['surfaces']
    assert len(out['observations'])==4
    return out

def fit_worker(seed,family,method):
    # This worker never reads truth.json or settings' physical source/room geometry.
    sys.path.insert(0,str(ROOT))
    from echosight.storage import load_session
    from echosight.pipeline import process_session
    from echosight.inference import infer_first_echo
    folder=P/'raw'/f'{family}-{seed}'
    session=load_session(folder/'mapping.json');session.update(calibration(seed,method))
    started=time.perf_counter()
    result=process_session(session,method='baseline' if method=='joint_grid' else 'mapper')
    if method=='joint_first_echo':
        # Public pipeline admission stays authoritative; first-echo comparator uses identical observations.
        result=infer_first_echo(result['acquisition'],result['observations']) | {'observations':result['observations'],'acquisition':result['acquisition']}
    seconds=time.perf_counter()-started
    withheld=None
    if family=='room':
        held=load_session(folder/'withheld.json');held.update(calibration(seed,method));withheld=extract_withheld(held)
    save(P/'fits'/f'{family}-{seed}-{method}.json',dict(seed=seed,family=family,method=method,result=result,
        raw_processing_s=seconds,runtime_scope='raw pipeline plus additional first-echo inference' if method=='joint_first_echo' else 'raw recording to result',withheld_extraction=withheld,calibration=calibration(seed,method),
        observation_hash=digest(result['observations']),physical_validation=False))

def score(result,truth):
    from scipy.optimize import linear_sum_assignment
    from evaluation.metrics import score_surfaces
    predicted=result.get('surfaces',[]);expected=truth['surfaces'];c=cfg()['acceptance'];matches=[]
    errors=np.zeros((len(predicted),len(expected),2))
    for i,p in enumerate(predicted):
        n=np.array(p['normal']);n=n/np.linalg.norm(n)
        for j,t in enumerate(expected):
            errors[i,j]=[np.degrees(np.arccos(np.clip(abs(n@t['normal']),0,1))),abs(n@t['anchor_m']-p['offset_m'])]
    if predicted and expected:
        valid=(errors[:,:,0]<=c['normal_error_deg'])&(errors[:,:,1]<=c['anchor_error_m'])
        cost=(~valid)*(max(len(predicted),len(expected))+1)+np.minimum(errors[:,:,0]/c['normal_error_deg']+errors[:,:,1]/c['anchor_error_m'],2)/2
        ii,jj=linear_sum_assignment(cost)
        for i,j in zip(ii,jj):
            if valid[i,j]: matches.append(dict(predicted_id=predicted[i]['surface_id'],truth_id=expected[j]['surface_id'],
                normal_error_deg=float(errors[i,j,0]),anchor_error_m=float(errors[i,j,1]),horizontal=abs(expected[j]['normal'][2])>=.9))
    return dict(matched=len(matches),unmatched=len(predicted)-len(matches),missed=len(expected)-len(matches),
        horizontal=sum(m['horizontal'] for m in matches),matches=matches,
        six_plane_mean_anchor_error_m=float(np.mean([m['anchor_error_m'] for m in matches])) if len(matches)==6 else None,
        historical_offset_015m=score_surfaces(result,truth))

def withheld_metrics(fit):
    result=fit['result'];held=fit['withheld_extraction'];c=cfg()['acceptance'];rows=[]
    session=result['acquisition'];s=np.array(session['source_position_m']);v=session.get('effective_speed_m_s',session['sound_speed_m_s']/session['source_clock_scale'])
    for surface in result.get('surfaces',[]):
        n=np.array(surface['normal']);d=surface['offset_m'];q=s+2*(d-n@s)*n
        for o in held['observations']:
            r=np.array(o['receiver_position_m']);prediction=float((np.linalg.norm(r-q)-np.linalg.norm(r-s))/v)
            candidates=[p for p in o.get('candidates',[]) if not p.get('merged',False) and abs(p['delay_s']-prediction)<=c['withheld_candidate_window_s']]
            row=dict(surface_id=surface['surface_id'],capture_id=o['capture_id'],predicted_delay_s=prediction,
                observation_status=o['status'],candidate_count=len(candidates),status='missing_or_ambiguous')
            if o['status']=='ok' and len(candidates)==1:
                row.update(status='unique',candidate_id=candidates[0]['candidate_id'],residual_s=float(candidates[0]['delay_s']-prediction))
            rows.append(row)
    # One observed peak cannot validate two distinct predicted paths.
    selected={}
    for row in rows:
        if row['status']=='unique':selected.setdefault((row['capture_id'],row['candidate_id']),[]).append(row)
    for values in selected.values():
        if len(values)>1:
            for row in values:row['status']='candidate_reused_by_multiple_surfaces'
    good=[r['residual_s'] for r in rows if r['status']=='unique']
    complete=len(rows)==24 and len(good)==24
    rms=float(np.sqrt(np.mean(np.square(good)))) if good else None
    maximum=float(max(abs(x) for x in good)) if good else None
    groups=[]
    for surface in result.get('surfaces',[]):
        sub=[r for r in rows if r['surface_id']==surface['surface_id']];values=[r['residual_s'] for r in sub if r['status']=='unique']
        groups.append(dict(surface_id=surface['surface_id'],expected=4,unique=len(values),rms_s=float(np.sqrt(np.mean(np.square(values)))) if values else None))
    return dict(rows=rows,per_surface=groups,expected=24,unique=len(good),complete=complete,rms_s=rms,max_abs_s=maximum,
                passed=bool(complete and rms<=c['withheld_rms_s'] and maximum<=c['withheld_max_s']))

def summarize():
    rows=[];c=cfg();sys.path.insert(0,str(ROOT))
    # All fits must exist before any evaluation truth is loaded.
    paths=[P/'fits'/f'{family}-{seed}-{method}.json' for seed in c['seeds'] for family in ('room','direct_only') for method in c['methods']]
    assert all(p.is_file() for p in paths)
    fits=[read(p) for p in paths]
    for fit in fits:
        truth=read(P/'raw'/f"{fit['family']}-{fit['seed']}"/'truth.json');m=score(fit['result'],truth)
        held=withheld_metrics(fit) if fit['family']=='room' else None
        admission_pass=len(fit['result']['observations'])==12 and all(o['status']=='ok' for o in fit['result']['observations'])
        passed=(m['matched']==6 and m['horizontal']==2 and m['unmatched']==0 and held['passed']) if held else not fit['result']['surfaces']
        rows.append(dict(seed=fit['seed'],family=fit['family'],method=fit['method'],status=fit['result']['status'],geometry=m,withheld=held,
            raw_processing_s=fit['raw_processing_s'],runtime_pass=fit['raw_processing_s']<=c['acceptance']['raw_processing_s'],
            geometry_and_prediction_pass=bool(passed and admission_pass),all_mapping_recordings_accepted=admission_pass,runtime_scope=fit['runtime_scope'],observation_hash=fit['observation_hash'],
            admission=[dict(capture_id=o['capture_id'],status=o['status'],candidate_count=len(o.get('candidates',[])),diagnostics=o.get('diagnostics',[])) for o in fit['result']['observations']]))
    benefits=[]
    for seed in c['seeds']:
        cases={r['method']:r for r in rows if r['seed']==seed and r['family']=='room'};j=cases['joint_mapper']
        comparisons=[]
        for comparator in ('nominal_mapper','one_x_mapper'):
            b=cases[comparator];gj,gb=j['geometry'],b['geometry'];hj,hb=j['withheld'],b['withheld']
            # No favorable subset. Incomplete comparator counts as recovery gain,
            # but never invents its missing residual/geometry error.
            comparable=hj['complete'] and hb['complete'] and gj['matched']==gb['matched']==6
            recovery_gain=gj['matched']==6 and gb['matched']<6
            lower_rms=comparable and hb['rms_s']-hj['rms_s']>=c['acceptance']['minimum_withheld_rms_gain_s']
            lower_anchor=comparable and gb['six_plane_mean_anchor_error_m']-gj['six_plane_mean_anchor_error_m']>=c['acceptance']['minimum_mean_anchor_gain_m']
            no_regression=gj['unmatched']<=gb['unmatched'] and gj['missed']<=gb['missed']
            comparisons.append(dict(comparator=comparator,comparable_complete_error_sets=comparable,recovery_gain=recovery_gain,
                lower_withheld_rms=lower_rms,lower_mean_anchor_error=lower_anchor,no_false_or_missed_regression=no_regression,
                comparator_complete_gate_failed=not b['geometry_and_prediction_pass'],
                gain=bool(j['geometry_and_prediction_pass'] and no_regression and (not b['geometry_and_prediction_pass'] or (lower_rms and lower_anchor)))))
        benefits.append(dict(seed=seed,comparisons=comparisons,benefit=all(x['gain'] for x in comparisons)))
    comparable_hashes=all(len({r['observation_hash'] for r in rows if r['seed']==seed and r['family']==family})==1 for seed in c['seeds'] for family in ('room','direct_only'))
    joint=[r for r in rows if r['method']=='joint_mapper'];recall_gain=sum(r['geometry']['matched'] for r in joint if r['family']=='room')>sum(r['geometry']['matched'] for r in rows if r['method']=='joint_first_echo' and r['family']=='room')
    transfer=all(r['geometry_and_prediction_pass'] and r['runtime_pass'] for r in joint)
    save(P/'results.json',dict(rows=rows,benefits=benefits,identical_observations=comparable_hashes,transfer_pass=transfer,
         first_echo_recall_gain=recall_gain,promotion_criteria_pass=transfer and comparable_hashes and recall_gain and all(b['benefit'] for b in benefits),
         decision_semantics='Development transfer evidence only. A pass requires independent review, not automatic public feature promotion.',limits=c['limits']))

def run(approved):
    verify(approved);completed=read(P/'render-complete.json');assert completed['freeze_sha256']==approved
    for name,h in completed['manifests'].items():
        manifest=P/name;assert sha(manifest)==h
        assert all(sha(manifest.parent/n)==d for n,d in read(manifest)['files'].items())
    if (P/'run-start.json').exists() or (P/'fits').exists(): raise FileExistsError('Preserve prior/partial run')
    save(P/'run-start.json',dict(freeze_sha256=approved,environment=dict(python=sys.version,platform=platform.platform(),numpy=np.__version__)))
    for seed in cfg()['seeds']:
        for family in ('room','direct_only'):
            for method in cfg()['methods']:
                subprocess.run([sys.executable,str(P/'run.py'),'worker','--approved-freeze',approved,'--seed',str(seed),'--family',family,'--method',method],cwd=ROOT,check=True,timeout=120)
    summarize();verify(approved)

if __name__=='__main__':
    a=argparse.ArgumentParser(description=__doc__);a.add_argument('action',choices=['check','freeze','render','run','worker']);a.add_argument('--approved-freeze');a.add_argument('--seed',type=int,choices=[2821,2833]);a.add_argument('--family',choices=['room','direct_only']);a.add_argument('--method',choices=['nominal_mapper','one_x_mapper','joint_mapper','joint_grid','joint_first_echo']);args=a.parse_args()
    if args.action=='check':print(json.dumps(check(),indent=2))
    elif args.action=='freeze':freeze()
    elif args.action=='render':render(args.approved_freeze)
    elif args.action=='run':run(args.approved_freeze)
    else:
        verify(args.approved_freeze)
        if not all((args.seed,args.family,args.method)):a.error('Worker requires exact seed/family/method')
        fit_worker(args.seed,args.family,args.method)
