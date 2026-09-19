import sys,json,tempfile,copy,argparse,subprocess
from pathlib import Path
parser=argparse.ArgumentParser(description='Reproduce historical de8442b delivery findings in an immutable checkout.')
parser.add_argument('--checkout',type=Path,required=True)
parser.add_argument('--output',type=Path,required=True)
args=parser.parse_args()
snapshot=args.checkout.resolve()
commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=snapshot,text=True).strip()
if commit!='de8442b2dd088c036d2b92eaeaf29a1273785795':raise ValueError('Historical reproduction requires de8442b checkout')
if subprocess.check_output(['git','status','--porcelain'],cwd=snapshot,text=True).strip():raise ValueError('Historical checkout must be clean')
sys.path.insert(0,str(snapshot))
import numpy as np
from scipy.io.wavfile import write
from echosight.storage import import_recording,validate_session
from echosight.pipeline import process_session
from echosight.signals import generate_probe
from echosight.evolution import compare_results
from tests.test_schemas import validator
out={}
with tempfile.TemporaryDirectory() as tmp:
    d=Path(tmp); cases=[]
    for rate,duration in [(8000,1),(192000,1),(48000,31)]:
        path=d/f'{rate}-{duration}.wav';write(path,rate,np.zeros(rate*duration,dtype=np.int16))
        imported=import_recording(path,d/f'import-{rate}-{duration}')
        _,probe=generate_probe()
        result=process_session({'session_id':'limits','source_position_m':[1,1,1],'probe':probe,'captures':[dict(imported,capture_id='one',receiver_position_m=[2,2,2])]})
        cases.append({'sample_rate_hz':rate,'duration_s':duration,'imported':True,'result_status':result['status'],'observation_diagnostics':result['observations'][0]['diagnostics']})
    out['storage_vs_processing']=cases
example=json.loads((snapshot/'examples/frontend/room-partial.json').read_text())
a,b,c=[copy.deepcopy(example) for _ in range(3)]
for obj,tag in zip([a,b,c],['a','b','c']):
    obj['surfaces']=obj['surfaces'][:1];obj['surfaces'][0]['surface_id']=tag;obj['result_id']=tag
ab=compare_results(a,b);bc=compare_results(b,c)
assert ab['correspondences'][0]['track_id']=='a'
assert bc['correspondences'][0]['track_id']=='b'
b['surfaces'][0]['track_id']=ab['correspondences'][0]['track_id']
propagated=compare_results(b,c)
out['track_chain']={'without_carry_forward':[ab['correspondences'][0]['track_id'],bc['correspondences'][0]['track_id']],'with_frontend_carry_forward':propagated['correspondences'][0]['track_id']}
request=json.loads((snapshot/'examples/frontend/controlled-request.json').read_text());request['coordinate_frame_id']='x'*161
validator('controlled-request').validate(request)
try:validate_session({'coordinate_frame_id':request['coordinate_frame_id']})
except ValueError as exc:out['controlled_schema_frame_boundary']={'schema_accepts_length':161,'session_rejection':str(exc)}
args.output.parent.mkdir(parents=True,exist_ok=True)
args.output.write_text(json.dumps(out,indent=2)+'\n')
print(json.dumps(out,indent=2))
