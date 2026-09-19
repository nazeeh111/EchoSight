"""Independent laser-reference spatial evaluation on a bounded measured subset."""
import argparse
import hashlib
import json
from pathlib import Path
import time
import subprocess
import numpy as np
from scipy.io import wavfile
from scipy.signal import fftconvolve
from .metrics import score_surfaces


def annotate(points,config):
    rng=np.random.default_rng(config['seed']);remaining=points.copy();planes=[]
    for index in range(config['maximum_planes']):
        if len(remaining)<config['minimum_supporting_laser_points']:break
        best=None
        # Small batches avoid building an unbounded points-by-allhypotheses matrix.
        for _ in range(config['ransac_iterations']//50):
            indices=rng.integers(0,len(remaining),size=(50,3));tri=remaining[indices]
            normals=np.cross(tri[:,1]-tri[:,0],tri[:,2]-tri[:,0]);length=np.linalg.norm(normals,axis=1)
            valid=length>1e-6;normals=normals[valid]/length[valid,None];origins=tri[valid,0]
            if not len(normals):continue
            offsets=np.einsum('ij,ij->i',normals,origins)
            hits=np.abs(remaining@normals.T-offsets)<config['point_plane_tolerance_m'];counts=hits.sum(0)
            j=int(np.argmax(counts))
            if best is None or counts[j]>best[0]:best=(int(counts[j]),hits[:,j])
        if best is None or best[0]<config['minimum_supporting_laser_points']:break
        support=remaining[best[1]];center=support.mean(0);_,_,vh=np.linalg.svd(support-center,full_matrices=False)
        normal=vh[-1];offset=float(normal@center)
        if offset<0:normal=-normal;offset=-offset
        residual=np.abs(support@normal-offset)
        planes.append({'surface_id':f'laser-plane-{index}','normal':normal.tolist(),'offset_m':offset,
                       'independent_annotation':'RANSAC of laserpoints only, before acousticfit',
                       'point_count':len(support),'rms_point_residual_m':float(np.sqrt(np.mean(residual**2))),
                       'support_bbox_m':[support.min(0).tolist(),support.max(0).tolist()]})
        remaining=remaining[~best[1]]
    return {'schema_version':'1.0','surfaces':planes,'reference':'Independently measured laser scan prefix','remaining_points':len(remaining)}


def prepare(subset,output):
    from echosight.signals import generate_probe
    output=Path(output);output.mkdir(parents=True,exist_ok=True)
    config=json.loads(Path(__file__).with_name('flair_acceptance.json').read_text())
    data=np.load(subset,allow_pickle=False)
    # Freeze optical annotations before any processing of acoustic data.
    truth=annotate(data['boundary_points'].T,config['annotation'])
    (output/'truth-laser.json').write_text(json.dumps(truth,indent=2)+'\n')
    positions=data['mic_positions'].T;source=data['spkr_positions'];rate=int(data['fs'].ravel()[0]);c=float(data['c'].ravel()[0])
    probe,metadata=generate_probe({'sample_rate_hz':rate,'period_s':1.0})
    session={'schema_version':'1.0','session_id':'flair-source0-fixed24','source_position_m':source.tolist(),
             'source_position_std_m':.005,'sound_speed_m_s':c,'sound_speed_std_m_s':.6,
             'source_clock_scale':1.,'source_clock_std_ppm':100.,'probe':metadata,'captures':[]}
    parenthash=hashlib.sha256(Path(subset).read_bytes()).hexdigest()
    for i,(position,rir) in enumerate(zip(positions,data['rirs'].T)):
        y=fftconvolve(probe,rir);gain=.75/max(np.max(np.abs(y)),1e-15);y*=gain
        path=output/f'capture-{i:02d}.wav';wavfile.write(path,rate,np.rint(y*32767).astype('<i2'))
        session['captures'].append({'capture_id':f'flair-{i:02d}','receiver_position_m':position.tolist(),
            'receiver_position_std_m':.005,'recording_path':path.name,'sample_rate_hz':rate,'provenance':'replayed',
            'external_transform':{'type':'measured_rir_convolved_with_generated_probe','gain':gain,'parent_subset_sha256':parenthash}})
    (output/'session.json').write_text(json.dumps(session,indent=2)+'\n')
    return output/'session.json'


def run(subset,output):
    from echosight.pipeline import process_session
    from echosight.storage import load_session
    from echosight.inference import infer_baseline,infer_first_echo
    root=Path(__file__).resolve().parents[1]
    hashes={str(p.relative_to(root)):hashlib.sha256(p.read_bytes()).hexdigest() for folder in ['echosight','evaluation'] for p in (root/folder).glob('*.py')}
    output=Path(output);sessionpath=prepare(subset,output);session=load_session(sessionpath)
    start=time.perf_counter();result=process_session(session);elapsed=time.perf_counter()-start
    truth=json.loads((output/'truth-laser.json').read_text());spec=json.loads(Path(__file__).with_name('flair_acceptance.json').read_text())
    observations=result.get('observations',[]);methods=[('mapper',result,elapsed)]
    for name,method in [('plane_grid',infer_baseline),('first_echo',infer_first_echo)]:
        start=time.perf_counter();r=method(session,observations);methods.append((name,r,time.perf_counter()-start))
    rows=[]
    for name,r,seconds in methods:
        metrics=score_surfaces(r,truth,**spec['matching']);req=spec['acceptance'];fails=[]
        for k,v,sign in [('minimum_matched_surfaces',metrics['matched_count'],'min'),('minimum_horizontal_surfaces',metrics['horizontal_matched'],'min'),('maximum_false_surfaces',metrics['false_surfaces'],'max'),('maximum_runtime_seconds',seconds,'max')]:
            if (sign=='min' and v<req[k]) or (sign=='max' and v>req[k]):fails.append(f'{k}: observed{v}, required{req[k]}')
        (output/f'{name}-result.json').write_text(json.dumps(r,indent=2,allow_nan=False)+'\n')
        rows.append({'method':name,'status':r['status'],'metrics':metrics,'runtime_seconds':seconds,'failures':fails,
                     'diagnostics':r.get('diagnostics',[]),'recording_status':[{'capture_id':o['capture_id'],'status':o['status'],'candidates':len(o.get('candidates',[])),'diagnostics':o.get('diagnostics',[])} for o in observations]})
    positions=np.asarray([c['receiver_position_m'] for c in session['captures']]);singular=np.linalg.svd(positions-positions.mean(0),compute_uv=False)
    final_hashes={str(p.relative_to(root)):hashlib.sha256(p.read_bytes()).hexdigest() for folder in ['echosight','evaluation'] for p in (root/folder).glob('*.py')}
    report={'schema_version':'1.0','source_sha256':hashes,'source_unchanged_during_run':hashes==final_hashes,
            'input_subset_sha256':hashlib.sha256(Path(subset).read_bytes()).hexdigest(),
            'git_commit':(root/'EVALUATED_COMMIT').read_text().strip() if (root/'EVALUATED_COMMIT').exists() else subprocess.run(['git','rev-parse','HEAD'],cwd=root,capture_output=True,text=True).stdout.strip(),
            'dataset':'FLAIR measuredRIRhybridreplay with independentlaserreference','laser_annotations':truth,
            'acceptance_sha256':hashlib.sha256(Path(__file__).with_name('flair_acceptance.json').read_bytes()).hexdigest(),
            'pose_singular_values_m':singular.tolist(),'cases':rows,'passed':not rows[0]['failures'] and hashes==final_hashes,
            'limits':spec['interpretation']}
    (output/'results.json').write_text(json.dumps(report,indent=2,allow_nan=False)+'\n');return report

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--subset',required=True);p.add_argument('--output',required=True);a=p.parse_args();r=run(a.subset,a.output);print(json.dumps({'passed':r['passed'],'results':[{k:c[k] for k in ['method','status','metrics','failures']} for c in r['cases']]},indent=2));raise SystemExit(0 if r['passed'] else 1)
