"""Portable calibration fit inputs are separate from supplied scene truth."""
import contextlib
import copy
import io
import json
from pathlib import Path
import signal
import unittest
from unittest.mock import patch
from jsonschema import ValidationError
from echosight.calibration import calibrate_reference
from echosight.cli import main
from echosight.pipeline import save_result
from tests import test_calibration
from tests.test_schemas import validator


class CalibrationContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        test_calibration.CalibrationTests.setUpClass()
        cls.session=test_calibration.CalibrationTests.session
        cls.reference=test_calibration.CalibrationTests.reference
        cls.root=test_calibration.CalibrationTests.root

    @classmethod
    def tearDownClass(cls):
        test_calibration.CalibrationTests.tearDownClass()

    def test_exact_inputs_roundtrip_without_paths_or_unknown_annotations(self):
        session=copy.deepcopy(self.session);reference=copy.deepcopy(self.reference)
        session['truth']={'secret_scene':'not_fitting_input'}
        session['probe']['private_note']='not_fitting_input'
        session['captures'][0]['annotations']={'wall':'not_fitting_input'}
        reference['private_path']='/not/a/fit/input'
        before=copy.deepcopy((session,reference))
        result=calibrate_reference(session,reference)
        inputs=result['calibration_input']
        serialized=json.dumps(inputs)
        self.assertNotIn('not_fitting_input',serialized)
        self.assertNotIn('private_path',serialized)
        self.assertNotIn('recording_path',serialized)
        self.assertNotIn(str(self.root),serialized)
        self.assertEqual(inputs['reference']['source_search_radius_m'],.15)
        self.assertEqual(inputs['reference']['effective_speed_bounds_m_s'],[300.,380.])
        replay=copy.deepcopy(inputs['acquisition'])
        paths={c['capture_id']:c['recording_path'] for c in session['captures']}
        for c in replay['captures']:c['recording_path']=paths[c['capture_id']]
        reproduced=calibrate_reference(replay,inputs['reference'])
        self.assertEqual(result['input_id'],reproduced['input_id'])
        self.assertEqual(result['calibration_id'],reproduced['calibration_id'])
        self.assertEqual(result['calibration'],reproduced['calibration'])
        self.assertEqual((session,reference),before)
        validator('calibration-result').validate(result)

    def test_reference_defaults_and_numeric_forms_canonicalize(self):
        default=calibrate_reference(self.session,self.reference)
        explicit=dict(self.reference,source_search_radius_m=.15,effective_speed_bounds_m_s=[300,380],normal=[1,0,0],offset_m=0)
        other=calibrate_reference(self.session,explicit)
        self.assertEqual(default['calibration_input'],other['calibration_input'])
        self.assertEqual(default['input_id'],other['input_id'])
        self.assertEqual(default['calibration_id'],other['calibration_id'])

    def test_changed_reference_pose_uncertainty_and_recording_change_identity(self):
        original=calibrate_reference(self.session,self.reference)
        for change in ('reference_uncertainty','source_pose','receiver_uncertainty','recording_bytes'):
            with self.subTest(change=change):
                session=copy.deepcopy(self.session);reference=copy.deepcopy(self.reference)
                if change=='reference_uncertainty':reference['offset_std_m']=.004
                if change=='source_pose':session['source_position_m'][0]+=.005
                if change=='receiver_uncertainty':session['captures'][0]['receiver_position_std_m']=.004
                if change=='recording_bytes':
                    path=self.root/'repackaged.wav'
                    path.write_bytes(Path(session['captures'][0]['recording_path']).read_bytes()+b'JUNK\x00\x00\x00\x00')
                    session['captures'][0]['recording_path']=str(path)
                changed=calibrate_reference(session,reference)
                self.assertNotEqual(original['input_id'],changed['input_id'])
                validator('calibration-result').validate(changed)

    def test_processed_and_preprocessing_rejections_have_honest_bindings(self):
        rejected=calibrate_reference(test_calibration.CalibrationTests.bad,self.reference)
        self.assertEqual(rejected['status'],'rejected')
        self.assertTrue(rejected['input_result_id'])
        self.assertTrue(all(r['hash_status']=='verified' for r in rejected['recording_inputs']))
        validator('calibration-result').validate(rejected)
        planar=copy.deepcopy(self.session)
        for c in planar['captures']:c['receiver_position_m'][2]=1.3
        with patch('echosight.pipeline.process_session',side_effect=AssertionError('early rejection decoded recordings')):
            early=calibrate_reference(planar,self.reference)
        self.assertEqual(early['status'],'rejected')
        self.assertIsNone(early['input_result_id'])
        self.assertTrue(early['input_id'])
        self.assertEqual(early['provenance']['recordings'],[])
        self.assertTrue(all(r['hash_status']=='not_processed' and r['sha256'] is None for r in early['recording_inputs']))
        self.assertEqual(early['training_capture_ids'],self.reference['training_capture_ids'])
        validator('calibration-result').validate(early)
        for output in (early,rejected):
            malformed=copy.deepcopy(output);malformed['calibration']={'source_position_m':[0,0,0]}
            with self.assertRaises(ValidationError):validator('calibration-result').validate(malformed)

    def test_cli_proposal_contract_and_interrupt_preserves_prior_output(self):
        from echosight import calibration
        session_path=self.root/'session.json';reference_path=self.root/'reference.json';output=self.root/'proposal.json'
        save_result(self.session,session_path);save_result(self.reference,reference_path)
        with contextlib.redirect_stdout(io.StringIO()):
            code=main(['calibrate-reference',str(session_path),str(reference_path),'--output',str(output)])
        self.assertEqual(code,0);validator('calibration-result').validate(json.loads(output.read_text()))
        before=output.read_bytes();fit=calibration.least_squares
        def interrupt(*args,**kwargs):
            fit(*args,**kwargs);signal.raise_signal(signal.SIGINT)
        with patch('echosight.calibration.least_squares',side_effect=interrupt),contextlib.redirect_stdout(io.StringIO()),contextlib.redirect_stderr(io.StringIO()):
            code=main(['calibrate-reference',str(session_path),str(reference_path),'--output',str(output)])
        self.assertEqual(code,130);self.assertEqual(output.read_bytes(),before)

if __name__=='__main__':unittest.main()
