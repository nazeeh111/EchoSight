from pathlib import Path
import contextlib, copy, hashlib, io, json, shutil, signal, subprocess, sys
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT));P=Path(__file__).parent
from tests.test_calibration import CalibrationTests
from echosight import calibration, signals
from echosight.pipeline import save_result
from echosight.cli import main
CalibrationTests.setUpClass()
try:
 session=copy.deepcopy(CalibrationTests.session);reference=copy.deepcopy(CalibrationTests.reference)
 raw=P/'raw';raw.mkdir(exist_ok=True)
 for c in session['captures']:
  src=Path(c['recording_path']);dst=raw/src.name;shutil.copyfile(src,dst);c['recording_path']=str(dst)
 save_result(session,P/'session.json');save_result(reference,P/'reference.json')
 initial={c['capture_id']:hashlib.sha256(Path(c['recording_path']).read_bytes()).hexdigest() for c in session['captures']}
 report={'commit':subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(), 'source_sha256':{p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in ('echosight/calibration.py','echosight/cli.py','echosight/pipeline.py')},'interrupts':[]}
 proposal=calibration.calibrate_reference(session,reference);assert proposal['status']=='calibration_proposal';save_result(proposal,P/'proposal.json')
 for stage in ('recording','fit','presave'):
  for existing in (False,True):
   destination=P/f'{stage}-{existing}.json'
   sentinel=b'{"prior_completed_output":"preserve"}\n'
   if existing:destination.write_bytes(sentinel)
   elif destination.exists():destination.unlink()
   if stage=='recording':target='echosight.signals.process_recording';original=signals.process_recording
   elif stage=='fit':target='echosight.calibration.least_squares';original=calibration.least_squares
   else:target='echosight.cli.save_result';original=None
   state={'calls':0}
   def interrupted(*a,**kw):
    state['calls']+=1
    if original is not None:original(*a,**kw)
    signal.raise_signal(signal.SIGINT)
   with patch(target,side_effect=interrupted),contextlib.redirect_stdout(io.StringIO()),contextlib.redirect_stderr(io.StringIO()):
    code=main(['calibrate-reference',str(P/'session.json'),str(P/'reference.json'),'--output',str(destination)])
   assert code==130
   assert destination.read_bytes()==sentinel if existing else not destination.exists()
   report['interrupts'].append({'stage':stage,'existing_output':existing,'exit_code':code,'calls':state['calls'],'new_output_written':not existing and destination.exists(),'existing_output_preserved':existing and destination.read_bytes()==sentinel})
 final={c['capture_id']:hashlib.sha256(Path(c['recording_path']).read_bytes()).hexdigest() for c in session['captures']}
 assert initial==final
 report['raw_hashes_unchanged']=True
 report['proposal']={'status':proposal['status'],'recordings_hashed':len(proposal['provenance']['recordings']),'partitioned_captures':len(proposal['training_capture_ids'])+len(proposal['validation_capture_ids']),'selected_candidate_evidence':len(proposal['evidence']),'physical_validation':proposal['physical_validation'],'contains_reference_input':'reference' in proposal,'contains_acquisition_input':'acquisition' in proposal,'input_result_id':proposal['input_result_id'],'calibration_id':proposal['calibration_id'],'keys':sorted(proposal)}
 report['contracts']={'result_schema_present':(ROOT/'schemas/calibration-result.schema.json').exists(),'request_schema_present':(ROOT/'schemas/calibration-reference.schema.json').exists(),'calibration_examples':[str(p.relative_to(ROOT)) for p in (ROOT/'examples').rglob('*calibrat*')]}
 save_result(report,P/'report.json');print(json.dumps(report,indent=2))
finally:CalibrationTests.tearDownClass()
