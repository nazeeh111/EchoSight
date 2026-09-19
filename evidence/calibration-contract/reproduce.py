"""Regenerate inspectable calibration artifacts from the existing raw-WAV fixture.

This is a contract replay of development simulation, not a new scientific cohort.
Run from the repository with requirements-test.txt installed in the local venv.
"""
import argparse
import copy
import hashlib
import json
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT))
from echosight.calibration import calibrate_reference
from echosight.pipeline import save_result
from tests import test_calibration
from tests.test_schemas import validator


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',required=True,type=Path)
    args=parser.parse_args()
    fixture=test_calibration.CalibrationTests
    fixture.setUpClass()
    try:
        planar=copy.deepcopy(fixture.session)
        for capture in planar['captures']:capture['receiver_position_m'][2]=1.3
        missing=copy.deepcopy(fixture.session);missing.pop('probe')
        malformed=copy.deepcopy(fixture.session);malformed['probe']={'duration_s':'bad'}
        cases={'proposal':fixture.session,'rejected-validation':fixture.bad,
               'rejected-planar':planar,'rejected-missing-probe':missing,
               'rejected-malformed-probe':malformed}
        check=validator('calibration-result');report={}
        validator('calibration-reference').validate(fixture.reference)
        save_result(fixture.reference,args.output/'reference.json')
        for name,session in cases.items():
            result=calibrate_reference(session,fixture.reference)
            check.validate(result)
            assert result['status']==('calibration_proposal' if name=='proposal' else 'rejected')
            assert str(fixture.root) not in json.dumps(result)
            replay=copy.deepcopy(result['calibration_input']['acquisition'])
            paths={c['capture_id']:c['recording_path'] for c in session['captures']}
            for capture in replay['captures']:capture['recording_path']=paths[capture['capture_id']]
            repeated=calibrate_reference(replay,result['calibration_input']['reference'])
            # The underlying mapper hashes the original probe spelling. The
            # calibration identity canonicalizes its materialized defaults.
            assert {k:v for k,v in result.items() if k!='input_result_id'}=={
                k:v for k,v in repeated.items() if k!='input_result_id'}
            path=save_result(result,args.output/(name+'.json'))
            report[name]={'status':result['status'],'schema_valid':True,'canonical_replay':True,
                          'upstream_result_id_reproduced':result['input_result_id']==repeated['input_result_id'],
                          'input_id':result['input_id'],
                          'artifact_sha256':hashlib.sha256(path.read_bytes()).hexdigest()}
        raw={path.name:hashlib.sha256(path.read_bytes()).hexdigest()
             for path in sorted(fixture.root.glob('*.wav'))}
        save_result({'evidence_class':'development simulation; no hardware validation',
                     'fixture':'tests.test_calibration.CalibrationTests (seed 81, 20 good + 20 held-delay-shift raw PCM WAVs)',
                     'raw_sha256':raw,'cases':report},args.output/'report.json')
        print(json.dumps(report,indent=2))
    finally:fixture.tearDownClass()


if __name__=='__main__':main()
