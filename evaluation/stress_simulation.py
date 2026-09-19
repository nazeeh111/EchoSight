"""Independent evaluation forward model. Never imported by reconstruction.

Exact rectangular image-lattice paths through order 2, independent fractional
impulse rendering, finite specular aperture, and explicitly approximate edge
scattering. This does not claim wave-equation diffraction accuracy.
"""
from __future__ import annotations
import itertools
import json
from pathlib import Path
import numpy as np
from scipy.io import wavfile
from scipy.signal import fftconvolve
from echosight.signals import generate_probe


def lattice_images(source, size, order=2):
    """q_j=2*m_j*L_j+(-1)**p_j*s_j; order=sum(abs(2*m_j-p_j))."""
    rows=[]
    for m in itertools.product(range(-1,2),repeat=3):
        for parity in itertools.product((0,1),repeat=3):
            degree=sum(abs(2*a-b) for a,b in zip(m,parity))
            if degree>order:continue
            q=2*np.asarray(m)*size+((-1.)**np.asarray(parity))*source
            rows.append((q,degree))
    return rows


def reflected(source, receiver, normal, offset):
    if (source@normal-offset)*(receiver@normal-offset)<=0:return None
    q=source+2*(offset-source@normal)*normal
    den=normal@(q-receiver)
    if abs(den)<1e-12:return None
    point=receiver+((offset-normal@receiver)/den)*(q-receiver)
    return q,point


def fractional_rir(paths, rate, duration=.16):
    impulse=np.zeros(round(duration*rate));half=24
    for delay, amplitude, _ in paths:
        coordinate=delay*rate; center=int(np.floor(coordinate))
        indices=np.arange(center-half,center+half+1)
        kernel=np.sinc(indices-coordinate)*np.hanning(2*half+1)
        kernel/=kernel.sum()
        mask=(indices>=0)&(indices<len(impulse))
        impulse[indices[mask]]+=amplitude*kernel[mask]
    return impulse


def simulate(output, family, seed):
    root=Path(output);root.mkdir(parents=True,exist_ok=True)
    rng=np.random.default_rng(seed);rate=48000;speed=343.
    size=np.array([5.2,4.1,3.0])+rng.uniform(-.5,.5,3)
    source=size*np.array([.37,.43,.38])
    receivers=rng.uniform([.5,.5,.35],size-[.5,.5,.35],size=(12,3))
    # Twelve fresh random positions and rotated world coordinates, unlike legacy fixtures.
    theta=rng.uniform(-2.8,2.8);rotation=np.array([[np.cos(theta),-np.sin(theta),0],[np.sin(theta),np.cos(theta),0],[0,0,1.]])
    translation=rng.uniform(-3,3,3)
    world=lambda a: (rotation@np.asarray(a).T).T+translation
    probe,metadata=generate_probe({'period_s':.35,'high_hz':14000.})
    emitted=probe.copy()
    if family=='source_nonlinearity':emitted=np.tanh(4*emitted)/3.
    # Causal source colour and group delay, distinct from the matched template.
    emitted=fftconvolve(emitted,[.75,.12,-.09,.06,.03])
    surfaces=[]
    for axis in range(3):
        n=np.eye(3)[axis]
        for side in (0,1):
            wn=rotation@n;d=float(side*size[axis]+wn@translation)
            surfaces.append({'surface_id':f'wall-{axis}-{side}','normal':wn.tolist(),'offset_m':d})
    panel_normal=np.array([1.,0,0]);panel_offset=float(source[0]+.85)
    panel_center=np.array([panel_offset,source[1],1.4]);panel_half=np.array([.0,.85,.65])
    if family in ['finite_panel','edge_scattering_surrogate']:
        wn=rotation@panel_normal
        surfaces.append({'surface_id':'finite-panel','normal':wn.tolist(),'offset_m':float(panel_offset+wn@translation),
                         'independent_extent_annotation':{'center_m':world(panel_center).tolist(),'half_height_m':.65,'half_width_m':.85}})
    if family=='diffuse_null':surfaces=[]
    session={'schema_version':'1.0','session_id':f'stress-{family}-{seed}',
             'source_position_m':world(source).tolist(),'source_position_std_m':.01,
             'sound_speed_m_s':speed,'sound_speed_std_m_s':.6,'source_clock_scale':1.,
             'source_clock_std_ppm':100.,'probe':metadata,'captures':[]}
    truth={'schema_version':'1.0','family':family,'seed':seed,'surfaces':surfaces,'paths':[],
           'scope':'Synthetic independent path renderer; no wave-equation diffraction or physical validation.',
           'model_violations':[]}
    if family=='distributed_source':truth['model_violations'].append('Two emitters separated by0.18m, point-source calibration supplied at first emitter.')
    if family=='edge_scattering_surrogate':truth['model_violations'].append('Weak edge-point broken-path scattering surrogate, not validated diffraction amplitude/phase.')
    for i,r in enumerate(receivers):
        direct=float(np.linalg.norm(r-source));paths=[]
        if family=='diffuse_null':
            paths=[(direct/speed,.55,'direct')]+[(direct/speed+t,float(a),'diffuse-null') for t,a in zip(rng.uniform(.002,.06,15),rng.uniform(.02,.09,15))]
        else:
            maxorder=2 if family in ['higher_order','edge_scattering_surrogate','distributed_source'] else 1
            for q,order in lattice_images(source,size,maxorder):
                distance=float(np.linalg.norm(r-q))
                amplitude=.55*(.68**order)*direct/max(distance,.2)
                paths.append((distance/speed,amplitude,'direct' if order==0 else f'order-{order}'))
            if family=='overlap':
                # A physically separate nearby plane generates closely spaced echoes.
                n=np.array([0.,0.,1.]);offset=size[2]-.035
                reflection=reflected(source,r,n,offset)
                if reflection:
                    q,_=reflection;distance=np.linalg.norm(q-r)
                    paths.append((distance/speed,.19*direct/distance,'near-ceiling-panel'))
                if i==0:
                    wn=rotation@n;surfaces.append({'surface_id':'near-ceiling-panel','normal':wn.tolist(),'offset_m':float(offset+wn@translation)})
            if family in ['finite_panel','edge_scattering_surrogate']:
                reflection=reflected(source,r,panel_normal,panel_offset)
                if reflection:
                    q,point=reflection
                    if abs(point[1]-panel_center[1])<=panel_half[1] and abs(point[2]-panel_center[2])<=panel_half[2]:
                        distance=float(np.linalg.norm(r-q));paths.append((distance/speed,.3*direct/distance,'finite-panel'))
                if family=='edge_scattering_surrogate':
                    for dy,dz in itertools.product([-panel_half[1],panel_half[1]],[-panel_half[2],panel_half[2]]):
                        edge=panel_center+np.array([0,dy,dz]);distance=float(np.linalg.norm(source-edge)+np.linalg.norm(edge-r))
                        paths.append((distance/speed,.035*direct/distance,'edge-surrogate'))
            if family=='distributed_source':
                second=source+np.array([.18,0,0])
                for q,order in lattice_images(second,size,1):
                    distance=float(np.linalg.norm(r-q));paths.append((distance/speed,.2*(.68**order)*direct/distance,'second-emitter'))
        rir=fractional_rir(paths,rate)
        wave=fftconvolve(emitted,rir)
        # Different receive clocks; interpolation runs once on complete convolved physical sound.
        alpha=1+rng.uniform(-350,350)*1e-6;offset=rng.uniform(.04,.08)
        u=np.arange(len(wave)+int(.12*rate))/rate
        source_time=(u-offset)/alpha
        if family=='nonaffine_clock':source_time+=.0012*np.sin(2*np.pi*source_time/1.15)
        samples=np.interp(source_time,np.arange(len(wave))/rate,wave,left=0,right=0)
        samples+=rng.normal(0,.00015,len(samples));samples*=.45
        if np.max(np.abs(samples))>.95:raise ValueError('Renderer overload; never normalize to hide clipping')
        wav=root/f'capture-{i:02d}.wav';wavfile.write(wav,rate,np.rint(samples*32767).astype('<i2'))
        session['captures'].append({'capture_id':f'capture-{i:02d}','receiver_position_m':world(r).tolist(),
                                     'receiver_position_std_m':.01,'sample_rate_hz':rate,
                                     'recording_path':wav.name,'provenance':'simulated'})
        truth['paths'].append({'capture_id':f'capture-{i:02d}','paths':[{'delay_s':float(t),'amplitude':float(a),'kind':k} for t,a,k in paths]})
    (root/'truth.json').write_text(json.dumps(truth,indent=2)+'\n')
    (root/'session.json').write_text(json.dumps(session,indent=2)+'\n')
    return root/'session.json'
