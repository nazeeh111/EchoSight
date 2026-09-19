"""Bounded measured-RIR benchmark. Optional h5py is required only here.

The raw measurements are laboratory RIRs, not device recordings of our probe.
Convolving a generated probe with each RIR yields explicitly HYBRID replay WAVs.
"""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path
import time
import subprocess
from urllib.request import urlopen
import wave
import numpy as np
from scipy.signal import fftconvolve


def manifest():
    return json.loads(Path(__file__).with_name('external_manifest.json').read_text())


def verify(path, entry):
    path=Path(path)
    return (path.is_file() and path.stat().st_size==entry['bytes'] and
            hashlib.sha256(path.read_bytes()).hexdigest()==entry['sha256'])


def retrieve(destination):
    """Explicit opt-in bounded retrieval, with content hashes and no overwrite."""
    destination=Path(destination);destination.mkdir(parents=True,exist_ok=True)
    for entry in manifest()['files']:
        path=destination/entry['filename']
        if path.exists():
            if not verify(path,entry):
                raise ValueError(f'Existing file fails provenance hash: {path}')
            continue
        with urlopen(entry['source_url'],timeout=30) as response:
            data=response.read(entry['bytes']+1)
        if len(data)!=entry['bytes'] or hashlib.sha256(data).hexdigest()!=entry['sha256']:
            raise ValueError(f'Download differs from pinned dataset: {entry["filename"]}')
        path.write_bytes(data)


def prepare_case(path, destination, probe_period_s=None):
    import h5py
    from echosight.signals import generate_probe
    path=Path(path); destination=Path(destination);destination.mkdir(parents=True,exist_ok=True)
    with h5py.File(path,'r') as f:
        rates=np.asarray(f['Data.SamplingRate']).ravel()
        rate=int(rates[0]); responses=np.asarray(f['Data.IR'][0])
        source=np.asarray(f['SourcePosition'][0]).tolist()
        receivers=np.asarray(f['ReceiverPosition'][:,:,0])
        metadata={k:bytes(f.attrs[k]).decode('utf8') for k in ['Title','RoomDescription','License']}
        temperature=float(f['RoomTemperature'][0])
    if rate!=48000 or responses.shape!=(5,48000):
        raise ValueError('Pinned external fixture dimensions changed')
    probe_options={'sample_rate_hz':rate}
    if probe_period_s is not None: probe_options['period_s']=probe_period_s
    probe, config=generate_probe(probe_options)
    captures=[]
    for i, h in enumerate(responses):
        # Preserve the full measured RIR. No time shifting or annotation-guided peak selection.
        samples=fftconvolve(probe,h)
        gain=.8/max(np.max(np.abs(samples)),1e-15)
        samples=samples*gain
        wav_path=destination/f'channel-{i+1}.wav'
        with wave.open(str(wav_path),'wb') as out:
            out.setnchannels(1);out.setsampwidth(2);out.setframerate(rate)
            out.writeframes(np.rint(samples*32767).astype('<i2').tobytes())
        captures.append({'capture_id':f'external-{i+1}','receiver_position_m':receivers[i].tolist(),
                         'receiver_position_std_m':.005,'recording_path':wav_path.name,
                         'provenance':'replayed','sample_rate_hz':rate,
                         'external_transform':{'type':'measured_rir_convolved_with_generated_probe','gain':gain,
                                               'pcm_quantization_bits':16,'source_file':path.name,
                                               'source_sha256':hashlib.sha256(path.read_bytes()).hexdigest()}})
    session={'schema_version':'1.0','session_id':path.stem,'source_position_m':source,
             'source_position_std_m':.005,'sound_speed_m_s':345.844,'sound_speed_std_m_s':1.,
             'source_clock_scale':1.,'source_clock_std_ppm':100.,'probe':config,'captures':captures}
    (destination/'session.json').write_text(json.dumps(session,indent=2,allow_nan=False)+'\n')
    singular=np.linalg.svd(receivers-receivers.mean(0),compute_uv=False)
    return destination/'session.json',{'metadata':metadata,'stored_temperature_kelvin':temperature,
                                     'receiver_singular_values_m':singular.tolist(),
                                     'receiver_affine_rank_1micrometre':int(np.count_nonzero(singular>1e-6))}


def run(data_dir, output_dir, probe_period_s=None):
    from echosight.pipeline import process_session
    import h5py
    data_dir=Path(data_dir);output_dir=Path(output_dir);output_dir.mkdir(parents=True,exist_ok=True)
    root=Path(__file__).resolve().parents[1]
    code_hashes={str(p.relative_to(root)):hashlib.sha256(p.read_bytes()).hexdigest() for folder in ['echosight','evaluation'] for p in sorted((root/folder).glob('*.py'))}
    commit=subprocess.run(['git','rev-parse','HEAD'],cwd=root,capture_output=True,text=True).stdout.strip() or 'uncommitted'
    cases=[]
    for entry in manifest()['files']:
        path=data_dir/entry['filename']
        if not verify(path,entry):
            raise ValueError(f'Missing or changed pinned file: {path}; use --download explicitly')
        case_dir=output_dir/path.stem
        session, audit=prepare_case(path,case_dir,probe_period_s)
        start=time.perf_counter();result=process_session(session);elapsed=time.perf_counter()-start
        (case_dir/'result.json').write_text(json.dumps(result,indent=2,allow_nan=False)+'\n')
        observations=result.get('observations',[])
        cases.append({**entry,**audit,'status':result['status'],'surface_count':len(result.get('surfaces',[])),
                      'runtime_seconds':elapsed,'diagnostics':result.get('diagnostics',[]),
                      'recording_status':[{'capture_id':o['capture_id'],'status':o['status'],
                                           'candidate_count':len(o.get('candidates',[])),
                                           'clock':o.get('clock',{}),'diagnostics':o.get('diagnostics',[])} for o in observations],
                      'passed':not result.get('surfaces') and result['status'] in ['ambiguous','no_result']})
    report={'schema_version':'1.0','git_commit':commit,'source_sha256':code_hashes,'evidence_class':'hybrid replay derived from measured laboratory impulse responses',
            'not_established':['iPhone capture performance','blind room-geometry accuracy','independently measured echo recall'],
            'annotation_policy':'No echo annotations loaded. Collinear receiver poses cannot establish unique unconstrained 3D reflector geometry.',
            'sound_speed_policy':'345.844 m/s is an explicit inherited model constant with 1 m/s uncertainty, not a measured temperature conversion.',
            'probe_period_s':probe_period_s if probe_period_s is not None else .22,
            'h5py_version':h5py.__version__,'cases':cases,'passed':all(c['passed'] for c in cases)}
    (output_dir/'results.json').write_text(json.dumps(report,indent=2,allow_nan=False)+'\n')
    return report


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--data',required=True)
    parser.add_argument('--output',required=True)
    parser.add_argument('--probe-period',type=float,default=None,help='Diagnostic spacing override; keep separately from default benchmark')
    parser.add_argument('--download',action='store_true',help='Explicitly download 8.8 MB from pinned source URLs')
    args=parser.parse_args()
    if args.download:retrieve(args.data)
    report=run(args.data,args.output,args.probe_period)
    print(json.dumps({'passed':report['passed'],'cases':[{k:c[k] for k in ['filename','status','surface_count','runtime_seconds']} for c in report['cases']]},indent=2))
    raise SystemExit(0 if report['passed'] else 1)

if __name__=='__main__':main()
