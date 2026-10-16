"""Released Li et al. Fig2 measured-NLOS route, adapted under CC BY4.0.

Published source and changes: notices/li2025/NOTICE.md (packaged with EchoSight). This ports the
released no-envelope/native-grid code; filtering and calibration are unresolved.
"""
from pathlib import Path
from contextlib import contextmanager
import hashlib
import io
import json
import math
import os
import resource
import shutil
import stat
import subprocess
import sys
import tempfile
import time
import numpy as np
from scipy import fft

C=343.0;WALL=.42;K=3;THRESHOLD_DIVISOR=4.5

def stolt_slabs(tdata,n,m,coefficient,slab=48):
    """Source interpn(q,y,x) reduces to linear z interpolation at exact xy nodes."""
    zaxis=np.arange(-m,m,dtype=np.float64)/m
    xy=np.arange(-n,n,dtype=np.float64)/n
    radial=coefficient**2*(xy[:,None]**2+xy[None,:]**2)
    result=np.zeros_like(tdata)
    iy=np.arange(2*n)[None,:,None];ix=np.arange(2*n)[None,None,:]
    # z<=0 is multiplied by zero in the source. Skip those queries exactly.
    for start in range(m+1,2*m,slab):
        stop=min(start+slab,2*m);z=zaxis[start:stop,None,None]
        q=np.sqrt(np.abs(radial[None,:,:]+z*z))
        valid=q<=zaxis[-1]
        lo=np.searchsorted(zaxis,q,side='right')-1
        np.clip(lo,0,2*m-2,out=lo)
        weight=(q-zaxis[lo])/(zaxis[lo+1]-zaxis[lo])
        values=tdata[lo,iy,ix]*(1-weight)+tdata[lo+1,iy,ix]*weight
        values*=np.abs(z)/np.maximum(q,1e-6)
        values[~valid]=0
        result[start:stop]=values
    return result

def reconstruct(raw,k=K,slab=48):
    if raw.ndim!=3 or raw.shape[0]!=raw.shape[1] or raw.dtype!=np.float64 or not np.isfinite(raw).all():raise ValueError('Expected finite square-grid float64 measured cube')
    data=raw
    for _ in range(k):
        if data.shape[2]%2:raise ValueError('Published pairwise sums need even temporal length at each step')
        data=data[:,:,::2]+data[:,:,1::2]
    n,_,m=data.shape
    data=np.transpose(data,(2,1,0)).copy()
    data*=np.linspace(0,1,m)[:,None,None];data*=2
    coefficient=n*C*(1e-6*2**k)/((WALL/2)*4)
    spectral=fft.fftshift(fft.fftn(data,s=tuple(2*v for v in data.shape),workers=1))
    del data
    migrated=stolt_slabs(spectral,n,m,coefficient,slab=slab)
    del spectral
    migrated=fft.ifftshift(migrated)
    reconstructed=fft.ifftn(migrated,workers=1,overwrite_x=True)
    volume=np.abs(reconstructed[:m,:n,:n]);del reconstructed,migrated
    volume=np.flip(np.transpose(volume,(0,2,1)),axis=(1,2)).copy()
    threshold=float(volume.max())/THRESHOLD_DIVISOR
    detected=volume>threshold
    first=detected.argmax(axis=0)
    depth=(first+1)*C*(1e-6*2**k)/2
    depth[~detected.any(axis=0)]=np.nan
    return volume,depth,threshold


PRESET='li2025-fig2-phase-native'
INPUT_BYTES=239719404
INPUT_SHA256='bddb46d4c26457b8364bb63c646c6d558c4db0d3004f36de0bd87d34f2a702f4'
ESTIMATED_MEMORY_BYTES=6*1024**3
FILES=('volume.npy','depth_m.npy','maximum_amplitude.npy','depth-amplitude.png','amplitude.png','axial-display.bin','inspection.html','threshold-diagnostics.json')
LIMITS=[
    'Published released-code route port, not a new f-k or adaptive-sampling method.',
    'Paper Methods describes a ±30 kHz band-pass absent from released Fig2 scripts; input prefilter status is unknown.',
    'No native MATLAB numerical-output equivalence established; small independent arithmetic checks and qualitative published comparison only.',
    'Source coordinates/depth are unregistered: no relay-wall/world transform, time-zero offset or independently calibrated sound speed.',
    'Published figure depth labels differ; no guessed calibration offset applied.',
    'First threshold crossing and 1.372mm source depth-bin spacing are not physical surface truth, resolution or uncertainty bounds.',
    'Actual external measured data, not acquisition or hardware validation by EchoSight.',
    '6 GiB working-memory estimate is not an OS memory ceiling or a free-RAM measurement; local POSIX command only.'
]

def digest_file(path):
    h=hashlib.sha256()
    with Path(path).open('rb') as f:
        for chunk in iter(lambda:f.read(1024*1024),b''):h.update(chunk)
    return h.hexdigest()

def _json_new(path,value):
    with Path(path).open('x',encoding='utf-8') as f:
        json.dump(value,f,indent=2,allow_nan=False);f.write('\n')

def estimate(preset,sample_rate_hz,memory_budget_gib):
    if preset!=PRESET or sample_rate_hz!=1000000:raise ValueError('Only declared li2025-fig2-phase-native at 1000000 Hz is supported')
    if not math.isfinite(memory_budget_gib) or not 6<=memory_budget_gib<=64:raise ValueError('Declare a finite memory budget from 6 to 64 GiB; this route conservatively estimates6 GiB')
    return {'schema':'echosight.nlos-preflight/1','preset':PRESET,'sample_rate_hz':1000000,
        'expected_input':{'bytes':INPUT_BYTES,'sha256':INPUT_SHA256,'variable':'data_origin','shape':[55,55,25000],'dtype':'float64'},
        'source_assumptions':{'wall_plane_m':.42,'sound_speed_m_per_s':343,'downsample_pair_sums':3,'envelope':False,'spatial_upsampling':False,'threshold_divisor':4.5},
        'resources':{'working_memory_estimate_bytes':ESTIMATED_MEMORY_BYTES,'declared_memory_budget_gib':memory_budget_gib,
            'estimate_is_hard_memory_limit':False,'minimum_free_disk_bytes_per_location':1024**3,
            'snapshot_bytes':INPUT_BYTES,'saved_volume_bytes':75625128,'padded_complex_array_bytes':1210000000,
            'fft_workers':1,'worker_wall_timeout_s':300,'worker_soft_cpu_limit_s':240,'worker_hard_cpu_limit_s':250},
        'limits':LIMITS}

@contextmanager
def verified_snapshot(path):
    """Only exact known bytes reach scipy.io; original path is never reopened."""
    path=Path(path)
    try:
        info=path.lstat()
        if not stat.S_ISREG(info.st_mode) or info.st_size!=INPUT_BYTES:raise ValueError('Input must be the exact bounded regular official Fig2 MAT file')
        fd=os.open(path,os.O_RDONLY|os.O_NOFOLLOW)
        with os.fdopen(fd,'rb') as original,tempfile.TemporaryFile(mode='w+b') as snapshot:
            info=os.fstat(original.fileno())
            if not stat.S_ISREG(info.st_mode) or info.st_size!=INPUT_BYTES:raise ValueError('Input file identity/size changed')
            count=0;h=hashlib.sha256()
            while True:
                chunk=original.read(min(1024*1024,INPUT_BYTES-count+1))
                if not chunk:break
                count+=len(chunk)
                if count>INPUT_BYTES:raise ValueError('Input byte budget exceeded')
                h.update(chunk);snapshot.write(chunk)
            if count!=INPUT_BYTES or h.hexdigest()!=INPUT_SHA256:raise ValueError('Input SHA256 differs from official pinned Fig2 MAT; no decoding performed')
            snapshot.flush();snapshot.seek(0);yield snapshot
    except OSError as error:raise ValueError('Cannot snapshot explicit regular input: '+str(error)) from error

def process_fig2(source,destination,*,preset,sample_rate_hz,memory_budget_gib=6,estimate_only=False):
    """Offline known-input command; no download, source execution or room mutation."""
    preflight=estimate(preset,sample_rate_hz,memory_budget_gib)
    source=Path(source).absolute();destination=Path(destination).absolute()
    if destination.exists() or destination.is_symlink():raise ValueError('Output exists; choose a fresh directory, no files were changed')
    if not destination.parent.is_dir():raise ValueError('Output parent must already be a directory')
    for location in (destination.parent,Path(tempfile.gettempdir())):
        if shutil.disk_usage(location).free<1024**3:raise ValueError('At least 1 GiB free disk is required at output and temporary-snapshot locations')
    with verified_snapshot(source) as snapshot:
        preflight['source_path_supplied']=str(source)
        if estimate_only:return {**preflight,'status':'verified_input_estimate_only','output_created':False}
        destination.mkdir(mode=0o700,exist_ok=False)
        _json_new(destination/'preflight.json',preflight)
        print('EchoSight measuredNLOS: verified pinned input; estimated 6 GiB working memory, 300s wall deadline. Output: '+str(destination),file=sys.stderr,flush=True)
        entry=Path(__file__).with_name('_nlos_worker.py');started=time.monotonic();worker=None
        env={**os.environ,'OPENBLAS_NUM_THREADS':'1','OMP_NUM_THREADS':'1','MKL_NUM_THREADS':'1','PYTHONNOUSERSITE':'1'}
        try:
            with (destination/'worker.log').open('xb') as log:
                worker=subprocess.Popen([sys.executable,'-I',str(entry),str(snapshot.fileno()),str(destination),str(source)],
                    pass_fds=(snapshot.fileno(),),stdin=subprocess.DEVNULL,stdout=log,stderr=subprocess.STDOUT,env=env)
                _json_new(destination/'run.json',{'worker_pid':worker.pid,'wall_timeout_s':300,'source_snapshot':'private verified inherited descriptor; no original path read by worker'})
                code=worker.wait(timeout=300)
            if code!=0:raise RuntimeError(f'Measured NLOS worker exit {code}; inspect retained worker.log')
            raw=(destination/'report.json').read_bytes()
            if len(raw)>1024*1024:raise RuntimeError('Worker report exceeded byte budget')
            report=json.loads(raw)
            if report.get('status')!='completed':raise RuntimeError('Worker did not complete')
            return {'status':'completed','report':str(destination/'report.json'),'inspection':str(destination/'inspection.html'),
                    'source_sha256':INPUT_SHA256,'controller_wall_s':time.monotonic()-started,'evidence_class':'external_measured_published_code_route'}
        except BaseException as error:
            if worker is not None and worker.poll() is None:worker.kill();worker.wait()
            _json_new(destination/'FAILED.json',{'status':'failed_or_inconclusive','reason':f'{type(error).__name__}: {error}','partial_output_preserved':True})
            raise


def worker_main():
    """Fixed package-owned subprocess entry; argv source name is report-only."""
    from scipy.io import loadmat
    from .nlos_display import save_display
    fd=int(sys.argv[1]);destination=Path(sys.argv[2]);source_name=sys.argv[3]
    soft,hard=resource.getrlimit(resource.RLIMIT_CPU)
    hard=250 if hard==resource.RLIM_INFINITY else min(hard,250)
    resource.setrlimit(resource.RLIMIT_CPU,(min(240,hard),hard))
    started=time.monotonic()
    with os.fdopen(fd,'rb',closefd=False) as stream:
        loaded=loadmat(stream,variable_names=['data_origin'])
    data=loaded.pop('data_origin');del loaded
    if data.shape!=(55,55,25000) or data.dtype!=np.float64:raise ValueError('Pinned input did not contain the declared float64 cube')
    volume,depth,threshold=reconstruct(data);del data
    amplitude=volume.max(axis=0)
    for name,array in [('volume.npy',volume),('depth_m.npy',depth),('maximum_amplitude.npy',amplitude)]:
        with (destination/name).open('xb') as f:np.save(f,array,allow_pickle=False)
    finite=np.isfinite(depth)
    report={'schema':'echosight.nlos-fig2-report/1','status':'completed','route':'PHANTOM measuredNLOS published Fig2 code route',
        'evidence_class':'external_measured_published_code_route','preset':PRESET,
        'source':{'path_supplied_for_provenance_only':source_name,'variable':'data_origin','shape':[55,55,25000],'dtype':'float64',
            'bytes':INPUT_BYTES,'sha256':INPUT_SHA256,'record':'https://researchdata.gla.ac.uk/2046/','dataset_doi':'10.5525/gla.researchdata.2046',
            'archive_url':'https://researchdata.gla.ac.uk/2046/3/Fig2.zip','archive_sha256':'ad6f7a44562e4fc74b4a61cd15223ce9f49338f879a16142bf4bb25782c656fd','license':'CC BY4.0'},
        'method':{'paper_doi':'10.1038/s42005-025-02335-3','code_zip_sha256':'a66b0de38f08ae92243855dd522e9acf1b11f563e37b0c9416e0a99f5c4e5446',
            'sampling_hz':1000000,'K':3,'temporal_reduction':'three adjacent pairwise sums','envelope':False,'spatial_interpolation':False,'threshold_divisor':4.5},
        'coordinates':{'volume_axes':['source_depth_bin','source_spatial_axis1_reversed','source_spatial_axis2_reversed'],
            'lateral_source_extent_m':[-.21,.21],'depth_formula':'(first strict threshold index, counted from1)*343*(8e-6)/2',
            'depth_bin_spacing_m':.001372,'invalid_depth':'NaN in NPY = no threshold crossing; not zero distance',
            'registered_to_room_world':False,'independent_calibration':False,'display':'reverse both array axes to follow source imagesc descending ticks'},
        'result':{'volume_shape':list(volume.shape),'threshold':threshold,'finite_depth_pixels':int(finite.sum()),
            'depth_min_m':float(depth[finite].min()) if finite.any() else None,'depth_max_m':float(depth[finite].max()) if finite.any() else None},
        'resources':{'working_memory_estimate_bytes':ESTIMATED_MEMORY_BYTES,'estimate_is_hard_memory_limit':False,'wall_s':time.monotonic()-started,
            'peak_worker_rss_bytes':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss if sys.platform=='darwin' else resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024,
            'fft_workers':1,'cpu_limit_s':[min(240,hard),hard]},'implementation_sha256':digest_file(__file__),'limits':LIMITS}
    save_display(destination,volume,depth,amplitude,report)
    report['resources']['wall_s']=time.monotonic()-started
    report['resources']['peak_worker_rss_bytes']=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*(1 if sys.platform=='darwin' else 1024)
    report['files']={name:{'bytes':(destination/name).stat().st_size,'sha256':digest_file(destination/name)} for name in FILES}
    _json_new(destination/'report.json',report)
    return 0
