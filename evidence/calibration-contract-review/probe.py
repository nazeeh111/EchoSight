"""Independent black-box contract boundary probes; candidate archive only."""
import copy, hashlib, json, os, signal, subprocess, sys, time
from pathlib import Path
import tempfile
ROOT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT/'source'))
tempfile.tempdir=str(ROOT)
from tests.test_calibration import CalibrationTests as Fixture
from tests.test_schemas import validator
from echosight.calibration import calibrate_reference
from echosight.storage import read_recording
from scipy.io.wavfile import write
import numpy as np
Fixture.setUpClass()
try:
    session=copy.deepcopy(Fixture.session);reference=copy.deepcopy(Fixture.reference)
    baseline=calibrate_reference(session,reference)
    cases={}
    # Independent failure mechanisms must retain verified bytes from other captures.
    mixed=copy.deepcopy(session)
    missing=Path(mixed['captures'][0].pop('recording_path'))
    silent=ROOT/'silent.wav';write(silent,48000,np.zeros(48000,dtype=np.int16))
    mixed['captures'][1]['recording_path']=str(silent)
    corrupt=ROOT/'corrupt.wav';corrupt.write_bytes(b'not a recording')
    mixed['captures'][2]['recording_path']=str(corrupt)
    got=calibrate_reference(mixed,reference);validator('calibration-result').validate(got)
    states=[r['hash_status'] for r in got['recording_inputs']]
    assert got['status']=='rejected' and states[:3]==['not_available','verified','not_available']
    assert all(v=='verified' for v in states[3:])
    assert got['recording_inputs'][1]['sha256']==hashlib.sha256(silent.read_bytes()).hexdigest()
    assert 'insufficient_signal' in str(got['diagnostics']) and 'recording_rejected' in str(got['diagnostics'])
    assert 'calibration' not in got and 'calibration_id' not in got
    cases['mixed_read_signal_rejection']={'status':got['status'],'hash_states':states,'schema_valid':True}
    # Full configuration defaults, numeric spelling and ignored annotations replay equally.
    altered=copy.deepcopy(session)
    for k in ('sound_speed_m_s','source_clock_scale','source_position_std_m'):
        altered[k]=baseline['calibration_input']['acquisition'][k]
    altered['probe']={k:v for k,v in altered['probe'].items() if k not in ('schema_version','kind','sample_count','pilot_start_samples','waveform_sha256','timing_unit')}
    # Verification fields are supplied assertions, so their removal intentionally changes identity.
    full=calibrate_reference(altered,reference)
    assert full['calibration']==baseline['calibration'] and full['input_id']!=baseline['input_id']
    numeric=copy.deepcopy(altered)
    numeric['probe']={k:float(v) for k,v in numeric['probe'].items()}
    numeric['unknown_annotation']={'not_consumed':'/private/marker'}
    numeric['captures'][0]['unknown_annotation']='ignored'
    same=calibrate_reference(numeric,reference)
    assert same['input_id']==full['input_id'] and same['calibration_id']==full['calibration_id']
    cases['numeric_and_assertion_identity']={'equal_numeric_identity':True,'removed_assertions_change_identity':True,'fit_unchanged':True}
    # Decoder rejection versus processor rejection must survive restoring only paths.
    replay=copy.deepcopy(got['calibration_input']['acquisition'])
    paths={c['capture_id']:c.get('recording_path') for c in mixed['captures']}
    for c in replay['captures']:
        if paths[c['capture_id']] is not None:c['recording_path']=paths[c['capture_id']]
    repeated=calibrate_reference(replay,got['calibration_input']['reference'])
    assert got['input_id']==repeated['input_id'] and got['diagnostics']==repeated['diagnostics']
    cases['mixed_rejection_replay']={'identity_equal':True,'diagnostics_equal':True}
    # A real CLI child receives SIGINT during execution; prior artifact remains intact.
    session_path=ROOT/'session.json';session_path.write_text(json.dumps(session))
    reference_path=ROOT/'reference.json';reference_path.write_text(json.dumps(reference))
    output=ROOT/'prior.json';prior=b'{"prior":"must survive"}\n';output.write_bytes(prior)
    code="from echosight.cli import main; import echosight.calibration; print('ready',flush=True); raise SystemExit(main())"
    proc=subprocess.Popen([sys.executable,'-c',code,'calibrate-reference',str(session_path),str(reference_path),'--output',str(output)],cwd=ROOT/'source',stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True,env=dict(os.environ,PYTHONDONTWRITEBYTECODE='1'))
    assert proc.stdout.readline().strip()=='ready'
    time.sleep(.05);proc.send_signal(signal.SIGINT)
    stdout,stderr=proc.communicate(timeout=30)
    assert proc.returncode==130,(proc.returncode,stdout,stderr)
    assert output.read_bytes()==prior
    cases['real_cli_sigint']={'exit_code':proc.returncode,'prior_output_unchanged':True,'stderr':stderr.strip()}
    for path in (ROOT/'source/evidence/calibration-contract').glob('*.json'):
        if path.stem in ('reference','report'):continue
        validator('calibration-result').validate(json.loads(path.read_text()))
    cases['checked_examples']={'proposal_and_four_rejections_schema_valid':True}
    (ROOT/'probe-results.json').write_text(json.dumps(cases,indent=2)+'\n')
    print(json.dumps(cases,indent=2))
finally:Fixture.tearDownClass()
