"""Independent, frozen source-relocation fixtures. Truth never enters sessions.

The same room and receiver survey are reused across source poses. Source-buffer
propagation delays use c/kappa, not c, where kappa is actual/nominal source
sample rate (nominal buffer seconds per physical second). No inverse code is used to render paths.
"""
from __future__ import annotations
import argparse
import json
from pathlib import Path
import numpy as np
from scipy.io import wavfile
from scipy.signal import fftconvolve
from echosight.signals import generate_probe
from .stress_simulation import fractional_rir, lattice_images, reflected

FAMILIES = ('room_two_sources','room_four_sources','higher_order_four_sources',
    'hidden_corner_four_sources','hidden_corner_fixed_sources',
    'hidden_corner_tangential_sources','finite_panel_four_sources','coordinate_frame_mismatch')


def source_positions(anchor, family):
    if family == 'hidden_corner_fixed_sources':
        offsets = np.zeros((4,3))
    elif family == 'hidden_corner_tangential_sources':
        offsets = np.array([[0,0,0],[0,0,.2],[0,0,.4],[0,0,.6]])
    else:
        offsets = np.array([[0,0,0],[.75,0,0],[0,.75,0],[.15,.2,.6]])
        if family == 'room_two_sources': offsets = offsets[:2]
    return np.asarray(anchor)+offsets


def corner_image(source):
    return np.asarray(source)*np.array([-1.,-1.,1.])


def equivalent_plane(source, image):
    """Evaluation-only plane whose source image is the supplied point."""
    delta=np.asarray(image)-source
    normal=delta/np.linalg.norm(delta)
    return normal, float(normal@(np.asarray(image)+source)/2)


def simulate(output, family, seed, receiver_count=12):
    if family not in FAMILIES: raise ValueError('Unknown source-relocation family')
    if receiver_count not in (4,12): raise ValueError('receiver_count must be4or12')
    root=Path(output);root.mkdir(parents=True,exist_ok=True)
    rng=np.random.default_rng(seed);rate=48000
    size=np.array([5.5,4.8,3.2])+rng.uniform(-.2,.2,3)
    sources=source_positions(size*np.array([.28,.31,.32]),family)
    receivers=rng.uniform([.65,.65,.35],[3.35,size[1]-.65,size[2]-.35],size=(12,3))
    theta=rng.uniform(-2.6,2.6)
    rotation=np.array([[np.cos(theta),-np.sin(theta),0],[np.sin(theta),np.cos(theta),0],[0,0,1.]])
    translation=rng.uniform(-2,2,3)
    world=lambda x: np.asarray(x)@rotation.T+translation
    physical_speed=343.45;source_clock_scale=1.00035
    effective_speed=physical_speed/source_clock_scale
    # Shared and independent survey errors are drawn once, not anew per capture.
    source_common_std=.003;source_independent_std=.004;receiver_std=.006
    source_common=rng.normal(0,source_common_std,3)
    surveyed_sources=world(sources)+source_common+rng.normal(0,source_independent_std,sources.shape)
    surveyed_receivers=world(receivers)+rng.normal(0,receiver_std,receivers.shape)
    receivers=receivers[:receiver_count];surveyed_receivers=surveyed_receivers[:receiver_count]
    source_cov=np.kron(np.ones((len(sources),len(sources))),np.eye(3)*source_common_std**2)
    source_cov+=np.eye(3*len(sources))*source_independent_std**2
    # Exact repetition is declared for the fixed-source control, not independently resurveyed.
    if family=='hidden_corner_fixed_sources':
        surveyed_sources[:]=surveyed_sources[0]
        source_cov=np.kron(np.ones((len(sources),len(sources))),np.eye(3)*(source_common_std**2+source_independent_std**2))
    frame=f'survey-{family}-{seed}'
    bundle={'schema_version':'1.0','scene_id':f'relocation-{family}-{seed}',
        'coordinate_frame_id':frame,'scene_static':True,'sessions':[],
        'shared_calibration':{'effective_speed_m_s':343.,'effective_speed_std_m_s':.6,
            'covariance_assumption':'explicit_source_pose_covariance_independent_speed',
            'source_pose_joint_covariance_m2':source_cov.tolist()}}
    surfaces=[]
    for axis in range(3):
        n=rotation[:,axis]
        for side in [0,1]:
            surfaces.append({'surface_id':f'wall-{axis}-{side}','normal':n.tolist(),
                'offset_m':float(side*size[axis]+n@translation)})
    panel_offset=float(size[0]-.9);panel_center=np.array([panel_offset,size[1]/2,size[2]/2])
    panel_half_width=1.65;panel_half_height=1.15
    if family=='finite_panel_four_sources':
        n=rotation[:,0]
        surfaces.append({'surface_id':'finite-panel','normal':n.tolist(),
            'offset_m':float(panel_offset+n@translation),
            'independent_extent_annotation':{'center_m':world(panel_center).tolist(),
                'half_width_m':panel_half_width,'half_height_m':panel_half_height}})
    truth={'schema_version':'1.0','family':family,'seed':seed,'surfaces':surfaces,'sessions':[],
        'source_positions_m':world(sources).tolist(),'receiver_positions_m':world(receivers).tolist(),
        'physical_speed_m_s':physical_speed,'source_clock_scale':source_clock_scale,
        'effective_speed_m_s':effective_speed,'physical_room_size_m':size.tolist(),
        'scope':'Synthetic specular image paths, finite aperture; no diffraction or hardware validation.',
        'receiver_count':receiver_count,
        'calibration':'One common effective speed and receiver survey error reused across source sessions.'}
    probe,metadata=generate_probe({'period_s':.35,'high_hz':14000.})
    emitted=fftconvolve(probe,[.82,.13,-.045,.025])
    hidden=family.startswith('hidden_corner')
    for j,source in enumerate(sources):
        folder=root/f'source-{j:02d}';folder.mkdir(exist_ok=True)
        session={'schema_version':'1.0','session_id':f'{bundle["scene_id"]}-source-{j:02d}',
            'coordinate_frame_id':frame if family!='coordinate_frame_mismatch' or j!=1 else 'unrelated-frame',
            'source_position_m':surveyed_sources[j].tolist(),
            'source_position_std_m':float(np.sqrt(source_common_std**2+source_independent_std**2)),
            'sound_speed_m_s':343.,'sound_speed_std_m_s':.6,'source_clock_scale':1.,'source_clock_std_ppm':80.,
            'effective_speed_m_s':343.,
            'source_effective_speed_covariance':np.diag([source_common_std**2+source_independent_std**2]*3+[.6**2]).tolist(),
            'probe':metadata,'captures':[]}
        sessiontruth={'session_id':session['session_id'],'captures':[]}
        for i,receiver in enumerate(receivers):
            direct=float(np.linalg.norm(receiver-source))
            if hidden:
                ceiling=source.copy();ceiling[2]=2*size[2]-source[2]
                images=[(source,0,'direct'),(ceiling,1,'wall-2-1'),(corner_image(source),2,'hidden-corner-double-bounce')]
            else:
                order=2 if family=='higher_order_four_sources' else 1
                images=[(q,k,'direct' if k==0 else f'order-{k}') for q,k in lattice_images(source,size,order)]
            paths=[]
            for q,degree,kind in images:
                length=float(np.linalg.norm(receiver-q))
                amplitude=.55*(.7**degree)*direct/max(length,.2)
                paths.append((length/effective_speed,amplitude,kind))
            if family=='finite_panel_four_sources':
                reflection=reflected(source,receiver,np.array([1.,0,0]),panel_offset)
                if reflection:
                    image,point=reflection
                    if abs(point[1]-panel_center[1])<=panel_half_width and abs(point[2]-panel_center[2])<=panel_half_height:
                        length=float(np.linalg.norm(receiver-image))
                        paths.append((length/effective_speed,.34*direct/length,'finite-panel'))
            wave=fftconvolve(emitted,fractional_rir(paths,rate))
            alpha=1+rng.uniform(-250,250)*1e-6;offset=rng.uniform(.04,.08)
            times=np.arange(len(wave)+round(.12*rate))/rate
            samples=np.interp((times-offset)/alpha,np.arange(len(wave))/rate,wave,left=0,right=0)
            samples=.45*(samples+rng.normal(0,.00012,len(samples)))
            if np.max(np.abs(samples))>.95: raise ValueError('Renderer clipping')
            name=f'capture-{i:02d}.wav';wavfile.write(folder/name,rate,np.rint(samples*32767).astype('<i2'))
            session['captures'].append({'capture_id':f'capture-{i:02d}',
                'receiver_position_m':surveyed_receivers[i].tolist(),'receiver_position_std_m':receiver_std,
                'receiver_pose_group_id':f'receiver-pose-{i:02d}','device_id':f'receiver-{i%4:02d}',
                'sample_rate_hz':rate,'recording_path':name,'provenance':'simulated'})
            sessiontruth['captures'].append({'capture_id':f'capture-{i:02d}',
                'paths':[{'delay_s':float(t),'amplitude':float(a),'kind':kind} for t,a,kind in paths]})
        (folder/'session.json').write_text(json.dumps(session,indent=2)+'\n')
        bundle['sessions'].append(str(Path(folder.name)/'session.json'));truth['sessions'].append(sessiontruth)
    (root/'bundle.json').write_text(json.dumps(bundle,indent=2)+'\n')
    (root/'truth.json').write_text(json.dumps(truth,indent=2)+'\n')
    return root/'bundle.json'

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',required=True);parser.add_argument('--family',choices=FAMILIES,required=True)
    parser.add_argument('--seed',type=int,required=True)
    parser.add_argument('--receiver-count',type=int,choices=[4,12],default=12)
    args=parser.parse_args();print(simulate(args.output,args.family,args.seed,args.receiver_count))
