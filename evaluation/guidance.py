"""Exploratory, recording-level next-view comparison on a development scene.

The simulator ground truth is used ONLY by an independent new-view waveform
renderer and post-inference metrics. View selection only receives fit hypotheses.
"""
from __future__ import annotations
import argparse
import copy
import hashlib
import json
from pathlib import Path
import numpy as np
from scipy.io import wavfile
from .metrics import score_surfaces


def append_view(session,truth,position,destination,seed=4):
    from echosight.signals import generate_probe
    from echosight.storage import load_session
    destination=Path(destination);destination.mkdir(parents=True,exist_ok=True)
    original=load_session(session) if isinstance(session,(str,Path)) else session
    updated=copy.deepcopy(original)
    probe,metadata=generate_probe(updated['probe'])
    rate=metadata['sample_rate_hz'];source=np.asarray(updated['source_position_m']);receiver=np.asarray(position)
    # Independent interpolation renderer: one direct and each visible first-order path.
    time=np.arange(len(probe)+int(.2*rate))/rate
    nominal=np.arange(len(probe))/rate
    samples=np.zeros(len(time));rng=np.random.default_rng(seed)
    paths=[(np.linalg.norm(source-receiver)/343.,.6)]
    for plane in truth['surfaces']:
        normal=np.asarray(plane['normal']);offset=plane['offset_m']
        if (normal@source-offset)*(normal@receiver-offset)<=0:continue
        image=source+2*(offset-normal@source)*normal
        paths.append((np.linalg.norm(image-receiver)/343.,.2))
    for delay,amplitude in paths:
        samples+=amplitude*np.interp((time-.06)/1.00015-delay,nominal,probe,left=0,right=0)
    samples=.6*(samples+rng.normal(0,.00025,len(samples)))
    wav=destination/'new-view.wav';wavfile.write(wav,rate,np.rint(samples*32767).astype(np.int16))
    updated['captures'].append({'capture_id':'additional-guided-view','receiver_position_m':list(map(float,position)),
                                'receiver_position_std_m':.01,'recording_path':str(wav.resolve()),
                                'sample_rate_hz':rate,'provenance':'simulated'})
    path=destination/'session.json';path.write_text(json.dumps(updated,indent=2)+'\n')
    return path


def run(output_dir):
    from echosight.simulation import simulate_session
    from echosight.pipeline import process_session
    from echosight.storage import load_session
    from echosight.inference import recommend_next_view
    output=Path(output_dir);output.mkdir(parents=True,exist_ok=True)
    path=simulate_session(output/'initial',scenario='coplanar',seed=4)
    before=process_session(path)
    session=load_session(path)
    source=np.asarray(session['source_position_m'])
    candidate_positions=[(source+np.array([1.,.5,z])).tolist() for z in [0.,.4,.8,-.6]]
    recommendation=recommend_next_view(session,before,candidate_positions)
    # Selection occurs before reading truth. Candidate[0] is deliberately coplanar.
    selected=recommendation['suggested_position_m']
    truth=json.loads((path.parent/'truth.json').read_text())
    results={}
    for label,position in [('suggested',selected),('coplanar_control',candidate_positions[0])]:
        newpath=append_view(session,truth,position,output/label)
        result=process_session(newpath)
        (output/label/'result.json').write_text(json.dumps(result,indent=2,allow_nan=False)+'\n')
        invariant=[p for h in result.get('hypotheses',[]) if h.get('hypothesis_id')=='invariant_supported_surfaces' for p in h.get('surfaces',[])]
        unresolved=[p for h in result.get('hypotheses',[]) if h.get('hypothesis_id')=='primary' for p in h.get('surfaces',[])]
        results[label]={'invariant_hypothesis_metrics':score_surfaces({'surfaces':invariant},truth),
                        'unresolved_mirror_surfaces':len(unresolved),'position_m':position,'status':result['status'],'metrics':score_surfaces(result,truth),
                        'diagnostics':result['diagnostics']}
    report={'schema_version':'1.0','split':'exploratory_development','before_status':before['status'],
            'recommendation':recommendation,'results':results,
            'claim':'Conditional geometric discrimination under visible first-order echoes, not guaranteed real-world audibility.',
            'source_sha256':{str(p.relative_to(Path(__file__).resolve().parents[1])):hashlib.sha256(p.read_bytes()).hexdigest()
                for p in (Path(__file__).resolve().parents[1]/'echosight').glob('*.py')}}
    (output/'results.json').write_text(json.dumps(report,indent=2,allow_nan=False)+'\n')
    return report

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--output',required=True)
    args=parser.parse_args();print(json.dumps(run(args.output),indent=2))
