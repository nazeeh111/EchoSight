"""Retrieve a <=12 MB prefix subset of CC-BY-4.0 FLAIR, never the116 MB file.

This reads independently compressed MATLAB5 variables. The RIR prefix yields
source0, receivers0..59 before selecting24 fixed microphones. A point-cloud
prefix covers the scene but is not a claim to retain the complete laser scan.
The full-file upstream MD5 cannot verify partial downloads; each exact returned
range gets its own SHA256 and the variable header/shape is checked.
"""
import argparse
import hashlib
import io
import json
from pathlib import Path
import struct
from urllib.request import Request,urlopen
import zlib
import numpy as np
from scipy.io import loadmat

URL='https://zenodo.org/api/records/17037517/files/data_FLAIR.mat/content'
SIZE=115821339
UPSTREAM_MD5='41e06a449ff39d271e32b3b82ab29341'
SELECTION=[base+i for base in [0,15,30,45] for i in [0,3,6,9,12,14]]
VARIABLES={'boundary_points':(40249804,38242508),'c':(78492320,42),'fs':(78492370,39),
           'mic_positions':(78492417,3177),'rirs':(78495602,37325615),'spkr_positions':(115821225,106)}


def matrix_header(data):
    """Parse MATLAB v5 numeric matrix metadata, including small-data names."""
    if len(data)<8 or struct.unpack('<I',data[:4])[0]!=14:raise ValueError('Not MATLAB matrix')
    offset=8;parts=[]
    for _ in range(3):
        if len(data)<offset+8:raise ValueError('Incomplete matrix header')
        tag,count=struct.unpack('<II',data[offset:offset+8]);small=tag>>16
        if small:
            kind=tag&65535;payload=data[offset+4:offset+4+small];offset+=8
        else:
            kind=tag;payload=data[offset+8:offset+8+count];offset+=8+((count+7)//8)*8
        parts.append((kind,payload))
    name=parts[2][1].decode('ascii');shape=tuple(np.frombuffer(parts[1][1],dtype='<i4'))
    kind,count=struct.unpack('<II',data[offset:offset+8])
    if kind!=9:raise ValueError('Expected double payload')
    return name,shape,offset+8,count


def retrieve(destination):
    root=Path(destination);root.mkdir(parents=True,exist_ok=True)
    if (root/'subset.npz').exists():raise ValueError('Refuse to overwrite an existing retrieved subset')
    rows=[];transferred=0
    pinned_path=Path(__file__).with_name('flair_subset_manifest.json')
    pinned=json.loads(pinned_path.read_text()) if pinned_path.exists() else None
    expected={(r['start'],r['length']):r['sha256'] for r in pinned['ranges']} if pinned else {}
    def get(start,count):
        nonlocal transferred
        if transferred+count>12_000_000:raise ValueError('12 MB transfer budget exceeded')
        with urlopen(Request(URL,headers={'Range':f'bytes={start}-{start+count-1}'}),timeout=45) as f:
            if f.status!=206 or f.headers.get('Content-Range')!=f'bytes {start}-{start+count-1}/{SIZE}':raise ValueError('Server did not honor exact range')
            b=f.read(count+1)
        if len(b)!=count:raise ValueError('Unexpected range length')
        if expected and hashlib.sha256(b).hexdigest()!=expected.get((start,count)):
            raise ValueError('Retrieved bytes differ from the pinned subset manifest')
        transferred+=len(b);rows.append({'start':start,'length':count,'sha256':hashlib.sha256(b).hexdigest()})
        return b
    header=get(0,128);values={}
    for name in ['c','fs','mic_positions','spkr_positions']:
        start,size=VARIABLES[name];b=get(start,size+8)
        values[name]=loadmat(io.BytesIO(header+b))[name]
    # The first4990-ish laserpoints are shuffled spatially and span the room.
    start,_=VARIABLES['boundary_points'];b=get(start+8,65536);d=zlib.decompressobj().decompress(b)
    name,shape,begin,total=matrix_header(d)
    if name!='boundary_points' or shape[0]!=3:raise ValueError('Wrong point-cloud variable')
    n=(len(d)-begin)//24;values['boundary_points']=np.frombuffer(d[begin:begin+24*n],dtype='<f8').reshape(3,n,order='F').copy()
    start,_=VARIABLES['rirs'];decompressor=zlib.decompressobj();decoded=bytearray();cursor=start+8
    needed=None
    while needed is None or len(decoded)<needed:
        b=get(cursor,262144);cursor+=len(b);decoded.extend(decompressor.decompress(b))
        if needed is None:
            name,shape,begin,total=matrix_header(decoded)
            if name!='rirs' or shape!=(17873,135,2):raise ValueError('Pinned RIR shape changed')
            needed=begin+17873*60*8
        print(f'{transferred} transferred bytes, {len(decoded)}/{needed} decoded',flush=True)
    values['rirs']=np.frombuffer(decoded[begin:needed],dtype='<f8').reshape(17873,60,order='F')[:,SELECTION].copy()
    values['mic_positions']=values['mic_positions'][:,SELECTION]
    values['spkr_positions']=values['spkr_positions'][:,0]
    np.savez_compressed(root/'subset.npz',**values)
    report={'schema_version':'1.0','dataset':'FLAIR','version':'Zenodo17037517v1','source_url':URL,
            'license':'CC-BY-4.0','citation':'Sundstrom, Elvander, Jakobsson, FLAIR: Room Impulse Response Dataset with Laser-Calibrated Room Geometry,2025,doi:10.5281/zenodo.17037517',
            'source_total_bytes':SIZE,'source_reported_md5':UPSTREAM_MD5,'source_full_checksum_verified':False,
            'integrity_limit':'Partial compressed prefixes do not include zlib trailing integrity checks or full-file MD5. Exact retrieved ranges are locallySHA256hashed, header shapes are validated; upstream authenticity not independently certified.',
            'ranges':rows,'bytes_transferred':transferred,'source_index':0,'receiver_indices_zero_based':SELECTION,
            'point_count':values['boundary_points'].shape[1],
            'selection_policy':'Fixed firstsource, six microphones per firstfour arrayplacements, before fitting. Laserprefix only for independent evaluation, never fitted acousticinput.',
            'subset_sha256':hashlib.sha256((root/'subset.npz').read_bytes()).hexdigest()}
    (root/'manifest.json').write_text(json.dumps(report,indent=2)+'\n');return report

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--destination',required=True);a=p.parse_args();print(json.dumps(retrieve(a.destination),indent=2))
