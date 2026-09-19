"""Frozen raw path-interpretation evaluation; no fitting labels enter processing.

Renderer uses independent path arithmetic and waveform construction. First unseen
execution requires an identified immutable integration commit and explicit flag.
"""
from __future__ import annotations
import argparse
import hashlib
import io
import json
import math
from pathlib import Path
import resource
import subprocess
import sys
import tarfile
import time
import numpy as np
from scipy.io import wavfile
from scipy.signal import chirp,fftconvolve
from scipy.signal.windows import tukey
from scipy.stats import chi2

ROOT=Path(__file__).resolve().parents[1]
SPEC=Path(__file__).with_name('path_interpretations_acceptance.json')

def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def save(path,value):
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(value,indent=2,allow_nan=False)+'\n')
def specification():return json.loads(SPEC.read_text())
def source_hashes():
    return {str(p.relative_to(ROOT)):sha(p) for p in [Path(__file__).resolve(),SPEC,ROOT/'docs/audit/PATH_ALTERNATIVES.md']}
def probe(config):
    p=dict(config);fs=int(p['sample_rate_hz']);length=round(p['duration_s']*fs)
    pulse=.7*chirp(np.arange(length)/fs,p['low_hz'],p['duration_s'],p['high_hz'],method='linear')*tukey(length,.25)
    starts=[round((p['lead_s']+i*p['period_s'])*fs) for i in range(p['repetitions'])]
    y=np.zeros(starts[-1]+length+round(p['tail_s']*fs))
    for start in starts:y[start:start+length]=pulse
    p.update(schema_version='1.0',kind='repeated_linear_chirp',pilot_start_samples=starts,sample_count=len(y),waveform_sha256=hashlib.sha256(y.astype('<f8').tobytes()).hexdigest(),timing_unit='source_buffer_seconds')
    return y,p

def impulse(paths,rate):
    response=np.zeros(round(.16*rate))
    for path in paths:
        for offset,coefficient in zip(path['fir_offsets_samples'],path['fir_coefficients']):
            center=path['delay_s']*rate+offset;integer=int(np.floor(center));indices=np.arange(integer-24,integer+25)
            weights=np.sinc(indices-center)*np.hanning(49);weights/=weights.sum();valid=(indices>=0)&(indices<len(response))
            response[indices[valid]]+=path['amplitude']*coefficient*weights[valid]
    return response

def mirror(source,receiver,normal,offset):
    if (normal@source-offset)*(normal@receiver-offset)<=0:return None
    image=source+2*(offset-normal@source)*normal
    denominator=normal@(image-receiver)
    if abs(denominator)<1e-12:return None
    fraction=(offset-normal@receiver)/denominator
    if not 0<fraction<1:return None
    point=receiver+fraction*(image-receiver)
    return float(np.linalg.norm(image-receiver)),point

def geometry(seed,cfg):
    # Exact draw order from immutable be5c70a source-relocation generator.
    rng=np.random.default_rng(seed);size=np.array(cfg['room_nominal_m'])+rng.uniform(*cfg['room_jitter_uniform_m'],3)
    sources=size*np.array(cfg['source_anchor_fraction'])+np.array(cfg['source_offsets_m'])
    receivers=rng.uniform(cfg['receiver_lower_m'],[3.35,size[1]-.65,size[2]-.35],size=(12,3))
    theta=rng.uniform(*cfg['world_yaw_uniform_rad']);c,s=np.cos(theta),np.sin(theta);rotation=np.array([[c,-s,0],[s,c,0],[0,0,1.]])
    translation=rng.uniform(*cfg['world_translation_uniform_m'],3)
    world=lambda x:np.asarray(x)@rotation.T+translation
    common=rng.normal(0,cfg['source_common_survey_std_m'],3)
    surveyed_sources=world(sources)+common+rng.normal(0,cfg['source_independent_survey_std_m'],sources.shape)
    surveyed_receivers=world(receivers)+rng.normal(0,cfg['receiver_survey_std_m'],receivers.shape)
    covariance=np.kron(np.ones((4,4)),np.eye(3)*cfg['source_common_survey_std_m']**2)+np.eye(12)*cfg['source_independent_survey_std_m']**2
    return rng,size,sources,receivers,rotation,translation,surveyed_sources,surveyed_receivers,covariance

def render(output,family,seed):
    spec=specification();cfg=spec['render']
    if family not in spec['families'] or seed not in spec['development_seeds']+spec['heldout_seeds']:raise ValueError('case outside frozen specification')
    folder=Path(output)
    if folder.exists() and any(folder.iterdir()):raise FileExistsError('Preserve previous fixture; choose an empty output')
    folder.mkdir(parents=True,exist_ok=True)
    rng,size,sources,receivers,rotation,translation,surveyed_sources,surveyed_receivers,covariance=geometry(seed,cfg)
    extra=np.random.default_rng(seed+19000);world=lambda x:np.asarray(x)@rotation.T+translation
    rate=cfg['rate_hz'];speed=cfg['physical_speed_m_s']/cfg['source_clock_actual_over_nominal'];point=receivers.mean(axis=0)+[1.5,1.5,.8]
    panel_center=np.array([size[0]-.9,size[1]/2,size[2]/2]);normal=np.array(cfg['panel_normal_unnormalized']);normal/=np.linalg.norm(normal)
    height=np.array([0.,0.,1.])-normal*normal[2];height/=np.linalg.norm(height);width=np.cross(height,normal);panel_offset=normal@panel_center
    physical_planes=[(np.eye(3)[axis],side*size[axis],f'wall-{axis}-{side}') for axis in range(3) for side in [0,1]]
    surfaces=[]
    if family in ['room','finite_tilted_panel','two_emitters']:
        for n,d,label in physical_planes:
            wn=rotation@n;surfaces.append(dict(surface_id=label,normal=wn.tolist(),offset_m=float(d+wn@translation)))
    if family=='finite_tilted_panel':
        wn=rotation@normal;surfaces.append(dict(surface_id='finite-panel',normal=wn.tolist(),offset_m=float(panel_offset+wn@translation),extent_annotation=dict(center_m=world(panel_center).tolist(),half_width_m=1.65,half_height_m=1.15,height_axis=(rotation@height).tolist(),width_axis=(rotation@width).tolist())))
    scene=f'paths-{family}-{seed}';frame=f'survey-{scene}';bundle=dict(schema_version='1.0',scene_id=scene,coordinate_frame_id=frame,scene_static=True,sessions=[],shared_calibration=dict(effective_speed_m_s=343.,effective_speed_std_m_s=.6,covariance_assumption='explicit_source_pose_covariance_independent_speed',source_pose_joint_covariance_m2=covariance.tolist()))
    truth=dict(schema_version='1.0',family=family,seed=seed,surfaces=surfaces,point_position_m=world(point).tolist() if family in ['ideal_point','dispersive_point'] else None,source_positions_m=world(sources).tolist(),receiver_positions_m=world(receivers).tolist(),physical_speed_m_s=cfg['physical_speed_m_s'],source_clock_scale=cfg['source_clock_actual_over_nominal'],effective_speed_m_s=speed,source_separation_m=.24 if family=='two_emitters' else 0.,physical_room_size_m=size.tolist(),source_fir=cfg['source_fir'],receiver_fir=cfg['receiver_fir'],sessions=[],scope='Independent synthetic geometric paths; ideal point/FIR surrogates are not measured furniture or diffraction.',panel_visible_receivers_per_source=[])
    source_variance=cfg['source_common_survey_std_m']**2+cfg['source_independent_survey_std_m']**2
    emitted,metadata=probe(cfg['probe']);emitted=fftconvolve(emitted,cfg['source_fir'])
    for j,source in enumerate(sources):
        sub=folder/f'source-{j:02d}';sub.mkdir();sid=f'{scene}-source-{j:02d}'
        session=dict(schema_version='1.0',session_id=sid,coordinate_frame_id=frame,source_position_m=surveyed_sources[j].tolist(),source_position_std_m=float(np.sqrt(source_variance)),sound_speed_m_s=343.,sound_speed_std_m_s=.6,source_clock_scale=1.,source_clock_std_ppm=80.,effective_speed_m_s=343.,source_effective_speed_covariance=np.diag([source_variance]*3+[.6**2]).tolist(),probe=metadata,captures=[])
        sessiontruth=dict(session_id=sid,captures=[]);visible=0
        for i,receiver in enumerate(receivers):
            paths=[];direct=float(np.linalg.norm(source-receiver))
            def add(length,amplitude,kind,offsets=None,taps=None):
                paths.append(dict(delay_s=float(length/speed),path_length_m=float(length),amplitude=float(amplitude),kind=kind,fir_offsets_samples=offsets or [0],fir_coefficients=taps or [1.]))
            emitters=[(source,1.)] if family!='two_emitters' else [(source,1.),(source+cfg['second_source_displacement_room_m'],.8)]
            for emitter_index,(emitter,gain) in enumerate(emitters):
                emitter_direct=float(np.linalg.norm(emitter-receiver));add(emitter_direct,gain*.55,f'direct-emitter-{emitter_index}')
                if family in ['room','finite_tilted_panel','two_emitters']:
                    for n,d,label in physical_planes:
                        path=mirror(emitter,receiver,n,d)
                        if path is None:raise ValueError('Room path unexpectedly invalid')
                        length,_=path;add(length,gain*.55*.7*emitter_direct/length,label+f'-emitter-{emitter_index}')
            if family=='finite_tilted_panel':
                panel=mirror(source,receiver,normal,panel_offset)
                if panel is not None:
                    length,bounce=panel;delta=bounce-panel_center
                    if abs(delta@width)<=1.65 and abs(delta@height)<=1.15:
                        add(length,.34*direct/length,'finite-panel');visible+=1
            if family in ['ideal_point','dispersive_point']:
                length=float(np.linalg.norm(source-point)+np.linalg.norm(point-receiver));bearing=math.atan2(source[1]-point[1],source[0]-point[0])
                add(length,.35*direct/length,'compact-scattering',cfg['dispersive_fir_offsets_samples'] if family=='dispersive_point' else [0],[1.,-.5+.15*np.sin(bearing),.25] if family=='dispersive_point' else [1.])
            if family=='diffuse_null':
                delays=extra.uniform(.003,.065,6);amplitudes=extra.uniform(.03,.20,6)*extra.choice([-1.,1.],6)
                for delay,amplitude in zip(delays,amplitudes):add(direct+delay*speed,amplitude,'independent-diffuse')
            wave=fftconvolve(emitted,impulse(paths,rate));wave=fftconvolve(wave,cfg['receiver_fir'])[:len(wave)]
            alpha=1+rng.uniform(-250,250)*1e-6;offset=rng.uniform(.04,.08);times=np.arange(len(wave)+round(.12*rate))/rate
            clean=np.interp((times-offset)/alpha,np.arange(len(wave))/rate,wave,left=0,right=0);noise=rng.normal(0,.00012,len(clean));samples=.45*(clean+noise)
            if np.max(np.abs(samples))>.95:raise ValueError('Renderer overload; never normalize away clipping')
            name=f'capture-{i:02d}.wav';wavfile.write(sub/name,rate,np.rint(samples*32767).astype('<i2'))
            session['captures'].append(dict(capture_id=f'capture-{i:02d}',receiver_position_m=surveyed_receivers[i].tolist(),receiver_position_std_m=.006,receiver_pose_group_id=f'receiver-pose-{i:02d}',device_id=f'receiver-{i%4:02d}',sample_rate_hz=rate,recording_path=name,provenance='simulated'))
            active=np.abs(clean)>max(1e-6,np.max(np.abs(clean))*1e-3)
            sessiontruth['captures'].append(dict(capture_id=f'capture-{i:02d}',paths=paths,relative_recording_clock_alpha=alpha,recording_clock_actual_over_nominal=alpha*cfg['source_clock_actual_over_nominal'],offset_s=offset,snr_active_db=float(10*np.log10(np.mean(clean[active]**2)/np.mean(noise[active]**2))),snr_full_buffer_db=float(10*np.log10(np.mean(clean**2)/np.mean(noise**2))),recording_sha256=sha(sub/name),peak_absolute_before_pcm=float(np.max(abs(samples)))))
        save(sub/'session.json',session);bundle['sessions'].append(f'{sub.name}/session.json');truth['sessions'].append(sessiontruth);truth['panel_visible_receivers_per_source'].append(visible)
    save(folder/'bundle.json',bundle);save(folder/'truth.json',truth)
    save(folder/'render-manifest.json',dict(source_sha256=source_hashes(),spec_sha256=sha(SPEC),truth_sha256=sha(folder/'truth.json'),bundle_sha256=sha(folder/'bundle.json'),recordings={str(p.relative_to(folder)):sha(p) for p in sorted(folder.glob('source-*/*.wav'))},truth_available_before_fitting=True))
    return folder/'bundle.json'

def metrics(result,truth,spec):
    from evaluation.metrics import score_surfaces
    geometry_score=score_surfaces(result,truth,**spec['matching']);modes=[];unique_count=0
    location=truth.get('point_position_m');quantile=float(chi2.ppf(.95,3))
    for h in result.get('hypotheses',[]):
        if h.get('kind')!='compact_scattering_location':continue
        unique=h.get('location_status')=='unique_conditional_mode';unique_count+=int(unique)
        for mode in h.get('location_modes',[]):
            position=np.asarray(mode['position_m'],float);error=None if location is None else float(np.linalg.norm(position-location));coverage=None;mahal=None
            C=mode.get('conditional_covariance_m2')
            if location is not None and C is not None:
                C=np.asarray(C,float)
                if C.shape==(3,3) and np.isfinite(C).all() and np.linalg.eigvalsh((C+C.T)/2).min()>0:
                    delta=position-location;mahal=float(delta@np.linalg.solve(C,delta));coverage=bool(mahal<=quantile)
            modes.append(dict(position_m=position.tolist(),position_error_m=error,unique_conditional=unique,local_rank=mode.get('local_rank'),search_boundary_limited=mode.get('search_boundary_limited'),nominal_95pct_ellipsoid_covered=coverage,mahalanobis_squared=mahal,score=mode.get('score',{})))
    fail=[];family=truth['family'];req=spec['requirements'][family]
    for key,value,cmp in [('minimum_matched_surfaces',geometry_score['matched_count'],'min'),('minimum_horizontal_surfaces',geometry_score['horizontal_matched'],'min'),('maximum_false_surfaces',geometry_score['false_surfaces'],'max'),('maximum_definitive_surfaces',geometry_score['predicted_count'],'max'),('maximum_supported_point_modes',len(modes),'max'),('maximum_unique_compact_locations',unique_count,'max')]:
        if key in req and ((cmp=='min' and value<req[key]) or (cmp=='max' and value>req[key])):fail.append(f'{key}: observed {value}, required {req[key]}')
    if req.get('require_supported_point_hypothesis') and not any(m['position_error_m'] is not None and m['position_error_m']<=req['maximum_point_location_error_m'] for m in modes):fail.append('No supported compact-location mode within0.15m')
    if req.get('unique_point_nominal_ellipsoid_coverage_required') and any(m['unique_conditional'] and m['nominal_95pct_ellipsoid_covered'] is not True for m in modes):fail.append('Unique wrong-model point excludes generating location or has no valid conditional covariance')
    if req.get('require_truth_id') and not any(m['truth_id']==req['require_truth_id'] for m in geometry_score['matches']):fail.append('Required finite tilted panel missed')
    visibility=truth.get('panel_visible_receivers_per_source',[])
    if 'minimum_panel_visible_receivers_per_source' in req and min(visibility)<req['minimum_panel_visible_receivers_per_source']:fail.append('Frozen scene fails required finite-panel visibility; scene not regenerated')
    return dict(surfaces=geometry_score,point_mode_count=len(modes),unique_compact_hypotheses=unique_count,point_modes=modes,minimum_point_error_m=min((m['position_error_m'] for m in modes if m['position_error_m'] is not None),default=None),point_capability_missed=location is not None and not any(m['position_error_m'] is not None and m['position_error_m']<=.15 for m in modes),mismatch_unresolved=family in ['two_emitters','dispersive_point'] and (result.get('status') in ['ambiguous','no_result'] or not modes),failures=fail)

def checkout(commit,destination):
    full=subprocess.check_output(['git','rev-parse',commit+'^{commit}'],cwd=ROOT,text=True).strip();destination=Path(destination)/full
    if not destination.exists():
        data=subprocess.check_output(['git','archive',full,'echosight'],cwd=ROOT);destination.mkdir(parents=True)
        with tarfile.open(fileobj=io.BytesIO(data)) as archive:archive.extractall(destination,filter='data')
    # Never trust an already existing snapshot without byte verification.
    names=subprocess.check_output(['git','ls-tree','-r','--name-only',full,'echosight'],cwd=ROOT,text=True).splitlines()
    for name in names:
        expected=subprocess.check_output(['git','show',full+':'+name],cwd=ROOT)
        if (destination/name).read_bytes()!=expected:raise ValueError('Immutable checkout differs: '+name)
    return full,destination

def worker(checkout_path,bundle,method,output):
    sys.path.insert(0,str(Path(checkout_path).resolve()))
    from echosight.multisource import process_scene_bundle
    started=time.perf_counter();result=process_scene_bundle(bundle,method=method);seconds=time.perf_counter()-started
    rss=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss;bytes_used=int(rss if sys.platform=='darwin' else rss*1024)
    save(output,dict(result=result,runtime_s=seconds,peak_process_rss_bytes=bytes_used,rss_scope='Process high-water mark including imports, raw processing and result before JSON serialization'))

def freeze(output):
    out=Path(output);out.mkdir(parents=True,exist_ok=True)
    value=dict(schema_version='1.0',source_sha256=source_hashes(),spec=specification(),frozen_unix_time=time.time(),heldout_not_generated=True)
    destination=out/'freeze.json'
    if destination.exists():
        previous=json.loads(destination.read_text())
        if previous['source_sha256']!=value['source_sha256']:raise ValueError('Existing freeze differs; preserve it and choose another output')
        return previous
    save(destination,value);return value

def verify_freeze(output):
    frozen=json.loads((Path(output)/'freeze.json').read_text())
    if frozen['source_sha256']!=source_hashes():raise ValueError('Renderer/spec/doc changed since freeze')
    return frozen

def development(output):
    out=Path(output);verify_freeze(out);spec=specification();reports=[]
    # Probe construction agrees exactly with the known public waveform contract.
    from echosight.signals import generate_probe
    independent,meta=probe(spec['render']['probe']);reference,reference_meta=generate_probe(spec['render']['probe'])
    if not np.array_equal(independent,reference) or meta!=reference_meta:raise AssertionError('Canonical probe disagreement')
    checks={'canonical_probe_exact':True,'fractional_delay_centroid_errors_samples':[]}
    for fraction in [0.,.1,.37,.73,.99]:
        sample=100+fraction;rir=impulse([dict(delay_s=sample/48000,amplitude=1.,fir_offsets_samples=[0],fir_coefficients=[1.])],48000)
        error=float(abs(np.arange(len(rir))@rir-sample));checks['fractional_delay_centroid_errors_samples'].append(error)
        if error>.01:raise AssertionError('Fractional impulse moment inaccurate')
    for family in spec['families']:
        folder=out/'development'/f'{family}-1001';render(folder,family,1001);truth=json.loads((folder/'truth.json').read_text());bundle=json.loads((folder/'bundle.json').read_text())
        # No solver invocation occurs in renderer verification.
        files=list(folder.glob('source-*/*.wav'));assert len(files)==48
        for path in files:
            fs,y=wavfile.read(path);assert fs==48000 and y.dtype==np.int16 and y.ndim==1
        C=np.array(bundle['shared_calibration']['source_pose_joint_covariance_m2']);assert C.shape==(12,12) and np.linalg.eigvalsh(C).min()>0
        positions=np.array(truth['source_positions_m']);assert np.linalg.matrix_rank(positions-positions.mean(axis=0))==3
        report=dict(family=family,seed=1001,recordings=48,truth_sha256=sha(folder/'truth.json'),panel_visibility=truth['panel_visible_receivers_per_source'],minimum_active_snr_db=min(c['snr_active_db'] for s in truth['sessions'] for c in s['captures']),maximum_peak=max(c['peak_absolute_before_pcm'] for s in truth['sessions'] for c in s['captures']))
        reports.append(report)
    save(out/'renderer-development.json',dict(passed=True,checks=checks,cases=reports,no_fitting_executed=True,heldout_not_generated=True,source_sha256=source_hashes()));return reports

def evaluate(output,integrated_commit):
    out=Path(output);verify_freeze(out);spec=specification()
    base,basepath=checkout(spec['baseline_commit'],out/'checkouts');updated,updatedpath=checkout(integrated_commit,out/'checkouts')
    if base==updated:raise ValueError('Integration must be a distinct identified commit')
    methods=[('original_mapper',base,basepath,'mapper'),('updated_mapper',updated,updatedpath,'mapper'),('updated_plane_grid',updated,updatedpath,'plane_grid')]
    plans=[]
    # Render and fingerprint the entire frozen corpus before any fit executes.
    for family in spec['families']:
        for seed in spec['heldout_seeds']:
            folder=out/'heldout'/f'{family}-{seed}';path=render(folder,family,seed);plans.append((family,seed,folder,path))
    save(out/'execution-plan.json',dict(methods=[dict(name=n,commit=c,method=m) for n,c,p,m in methods],cases=[dict(family=f,seed=s,manifest_sha256=sha(d/'render-manifest.json')) for f,s,d,p in plans],source_sha256=source_hashes()))
    rows=[]
    for family,seed,folder,path in plans:
        outputs=[];manifest=json.loads((folder/'render-manifest.json').read_text())
        for name,commit,snapshot,method in methods:
            output_file=folder/f'{name}.json';command=[sys.executable,str(Path(__file__).resolve()),'_worker','--checkout',str(snapshot.resolve()),'--bundle',str(path.resolve()),'--method',method,'--output',str(output_file.resolve())]
            started=time.perf_counter()
            try:
                done=subprocess.run(command,cwd=ROOT,capture_output=True,text=True,timeout=spec['execution']['worker_timeout_s'])
                if done.returncode:raise RuntimeError(done.stderr[-8000:])
                data=json.loads(output_file.read_text());outputs.append((name,commit,data,None))
            except (subprocess.TimeoutExpired,RuntimeError) as exc:
                error=str(exc);save(folder/f'{name}-error.json',dict(error=error,wall_s=time.perf_counter()-started));outputs.append((name,commit,dict(result=dict(status='failed',surfaces=[],hypotheses=[],diagnostics=[error]),runtime_s=time.perf_counter()-started,peak_process_rss_bytes=None),error))
        # Open labels only after all methods finish. Input hashes must remain equal.
        truth=json.loads((folder/'truth.json').read_text());unchanged=all(sha(folder/name)==h for name,h in manifest['recordings'].items())
        fingerprints=[]
        for name,commit,data,error in outputs:
            result=data['result'];score=metrics(result,truth,spec)
            if error:score['failures'].append('Processing failed: '+error)
            if not unchanged:score['failures'].append('Raw recording bytes changed')
            processed=result.get('processed_sessions',[]);fingerprint=hashlib.sha256(json.dumps(processed,sort_keys=True,allow_nan=False).encode()).hexdigest();fingerprints.append(fingerprint)
            row=dict(family=family,seed=seed,method=name,commit=commit,status=result.get('status'),metrics=score,runtime_s=data['runtime_s'],peak_process_rss_bytes=data['peak_process_rss_bytes'],diagnostics=result.get('diagnostics',[]),path_model_comparison=result.get('path_model_comparison'),candidate_counts=[[len(o.get('candidates',[])) for o in item['observations']] for item in processed],processed_input_sha256=fingerprint,raw_unchanged=unchanged)
            rows.append(row);print(family,seed,name,score['surfaces']['matched_count'],score['surfaces']['false_surfaces'],score['point_mode_count'],score['failures'],flush=True)
        save(out/'partial-results.json',rows)
    report=dict(schema_version='1.0',baseline_commit=base,integrated_commit=updated,source_sha256=source_hashes(),cases=rows,passed=not any(r['metrics']['failures'] for r in rows if r['method']=='updated_mapper'),interpretation='Frozen synthetic raw-recording evaluation; no hardware or measured furniture accuracy claim')
    save(out/'results.json',report);return report

def main():
    parser=argparse.ArgumentParser(description=__doc__);sub=parser.add_subparsers(dest='action',required=True)
    for action in ['freeze','development','evaluate']:
        p=sub.add_parser(action);p.add_argument('--output',required=True)
        if action=='evaluate':p.add_argument('--integrated-commit',required=True);p.add_argument('--allow-unseen',action='store_true')
    p=sub.add_parser('_worker');p.add_argument('--checkout',required=True);p.add_argument('--bundle',required=True);p.add_argument('--method',choices=['mapper','plane_grid'],required=True);p.add_argument('--output',required=True)
    a=parser.parse_args()
    if a.action=='freeze':print(json.dumps(freeze(a.output)['source_sha256']))
    elif a.action=='development':print(json.dumps(development(a.output),indent=2))
    elif a.action=='evaluate':
        if not a.allow_unseen:parser.error('Unseen execution requires coordinator authorization and --allow-unseen')
        result=evaluate(a.output,a.integrated_commit);raise SystemExit(0 if result['passed'] else 1)
    else:worker(a.checkout,a.bundle,a.method,a.output)

if __name__=='__main__':main()
