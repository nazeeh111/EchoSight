"""Independent development waveform renderer; annotations never enter fitting."""
from pathlib import Path
import json,sys,copy
import numpy as np
from scipy.signal import fftconvolve
from scipy.io import wavfile
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT))
from evaluation.path_interpretations import geometry,probe,impulse,mirror,sha,save,specification
FAMILIES=['single_room','dual_room','near_reflector','direct_null','receiver_filter','dual_phase']
SEEDS=[2401,2411]

def render(folder,family,seed):
 assert family in FAMILIES and seed in SEEDS
 folder=Path(folder)
 if folder.exists() and any(folder.iterdir()):raise FileExistsError('Preserve previous case')
 folder.mkdir(parents=True,exist_ok=True);cfg=copy.deepcopy(specification()['render']);cfg['receiver_lower_m'][2]=.95
 rng,size,sources,receivers,R,T,surveyed_s,surveyed_r,C=geometry(seed,cfg);world=lambda x:np.asarray(x)@R.T+T;rate=48000;v=343.45/1.00035;delta=np.array([.18,-.11,.07]);driver=.00008
 planes=[(np.eye(3)[a],side*size[a],f'wall-{a}-{side}') for a in range(3) for side in [0,1]]
 if family=='near_reflector':planes.append((np.array([0.,0.,1.]),.8,'near-reflector'))
 if family=='direct_null':planes=[]
 surfaces=[dict(surface_id=label,normal=(R@n).tolist(),offset_m=float(d+(R@n)@T)) for n,d,label in planes]
 scene=f'source-diagnostic-{family}-{seed}';frame='survey-'+scene;bundle=dict(schema_version='1.0',scene_id=scene,coordinate_frame_id=frame,scene_static=True,sessions=[],shared_calibration=dict(effective_speed_m_s=343.,effective_speed_std_m_s=.6,covariance_assumption='explicit_source_pose_covariance_independent_speed',source_pose_joint_covariance_m2=C.tolist()))
 truth=dict(family=family,seed=seed,surfaces=surfaces,source_positions_m=world(sources).tolist(),receiver_positions_m=world(receivers).tolist(),secondary_offset_m=(R@delta).tolist() if family in ['dual_room','dual_phase'] else None,driver_delay_s=driver if family in ['dual_room','dual_phase'] else None,constant_orientation=True,sessions=[],scope='Synthetic source/phase/filter controls; no physical device claim')
 emitted,metadata=probe(cfg['probe']);emitted=fftconvolve(emitted,cfg['source_fir']);variance=.003**2+.004**2
 for j,source in enumerate(sources):
  sub=folder/f'source-{j:02d}';sub.mkdir();sid=scene+f'-source-{j:02d}'
  session=dict(schema_version='1.0',session_id=sid,coordinate_frame_id=frame,source_position_m=surveyed_s[j].tolist(),source_position_std_m=float(np.sqrt(variance)),sound_speed_m_s=343.,sound_speed_std_m_s=.6,source_clock_scale=1.,source_clock_std_ppm=80.,effective_speed_m_s=343.,source_effective_speed_covariance=np.diag([variance]*3+[.6**2]).tolist(),probe=metadata,captures=[]);st=dict(session_id=sid,captures=[])
  for i,receiver in enumerate(receivers):
   paths=[]
   for k,(emitter,gain,lag) in enumerate([(source,1.,0.)]+([(source+delta,.65,driver)] if family in ['dual_room','dual_phase'] else [])):
    direct=np.linalg.norm(emitter-receiver)
    def add(length,amplitude,label):paths.append(dict(delay_s=float(length/v+lag),path_length_m=float(length),amplitude=float(amplitude),kind=label+f'-emitter-{k}',fir_offsets_samples=[0,5,13] if family=='dual_phase' and k else [0],fir_coefficients=[1.,-.35,.18] if family=='dual_phase' and k else [1.]))
    add(direct,.55*gain,'direct')
    for n,d,label in planes:
     reflected=mirror(emitter,receiver,n,d)
     if reflected is None:raise ValueError('Physical same-side scene failure; no resampling')
     length,bounce=reflected;add(length,gain*(.35 if label=='near-reflector' else .55*.7)*direct/length,label)
   wave=fftconvolve(emitted,impulse(paths,rate));wave=fftconvolve(wave,cfg['receiver_fir'])[:len(wave)]
   if family=='receiver_filter':
    bearing=np.arctan2(receiver[1]-source[1],receiver[0]-source[0]);f=np.zeros(10);f[[0,3,9]]=[1.,.18*np.sin(bearing),-.08];wave=fftconvolve(wave,f)[:len(wave)]
   alpha=1+rng.uniform(-250,250)*1e-6;offset=rng.uniform(.04,.08);times=np.arange(len(wave)+round(.12*rate))/rate;clean=np.interp((times-offset)/alpha,np.arange(len(wave))/rate,wave,left=0,right=0);noise=rng.normal(0,.00012,len(clean));y=.45*(clean+noise)
   if max(abs(y))>.95:raise ValueError('Overload; never normalize')
   name=f'capture-{i:02d}.wav';wavfile.write(sub/name,rate,np.rint(y*32767).astype('<i2'));session['captures'].append(dict(capture_id=f'capture-{i:02d}',receiver_position_m=surveyed_r[i].tolist(),receiver_position_std_m=.006,receiver_pose_group_id=f'receiver-pose-{i:02d}',device_id=f'receiver-{i%4:02d}',sample_rate_hz=rate,recording_path=name,provenance='simulated'));st['captures'].append(dict(capture_id=f'capture-{i:02d}',paths=paths,alpha=alpha,offset_s=offset,recording_sha256=sha(sub/name),peak=float(max(abs(y)))))
  save(sub/'session.json',session);bundle['sessions'].append(f'{sub.name}/session.json');truth['sessions'].append(st)
 save(folder/'bundle.json',bundle);save(folder/'truth.json',truth);save(folder/'manifest.json',dict(recordings={str(p.relative_to(folder)):sha(p) for p in sorted(folder.glob('source-*/*.wav'))},truth_sha256=sha(folder/'truth.json')))
 return folder/'bundle.json'
