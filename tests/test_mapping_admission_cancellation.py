"""Recording admission and cancellation must not publish unfinished geometry."""
import contextlib
import copy
import hashlib
import io
import json
from pathlib import Path
import signal
import tempfile
import time
import unittest
from unittest.mock import patch

from echosight import inference
from echosight.pipeline import process_session
from echosight.simulation import simulate_session
from echosight.storage import load_session,read_recording,SessionStore
from tests.test_acquisition import capture_bytes
from tests.test_inference import fixture


class MappingAdmissionCancellationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp=tempfile.TemporaryDirectory();cls.root=Path(cls.temp.name)
        cls.session=load_session(simulate_session(cls.root/'raw',seed=39017,capture_count=12))
        cls.samples=[read_recording(c['recording_path'])[0] for c in cls.session['captures']]
    @classmethod
    def tearDownClass(cls):cls.temp.cleanup()

    def native_session(self,case):
        session=copy.deepcopy(self.session)
        for i,(capture,samples) in enumerate(zip(session['captures'],self.samples)):
            if case=='mixed' and i==0:continue
            def mutate(m):
                m['source_declaration'].update(configuration_id='source-one',probe_id='probe-one',route_id='speaker-one')
                if case=='unknown':m['source_declaration']={key:' UnKnOwN ' for key in m['source_declaration']}
                if case=='conflict' and i%2:m['source_declaration']['configuration_id']='source-two'
            raw,_,_=capture_bytes(samples,mutate);path=self.root/f'{case}-{i}.zip';path.write_bytes(raw)
            capture['recording_path']=str(path);capture.pop('sha256',None)
        return session

    def assert_cancelled_without_geometry(self,result):
        self.assertEqual(result['status'],'cancelled',result.get('diagnostics'))
        for key in ('surfaces','hypotheses','dimensions','guidance'):self.assertEqual(result.get(key,[]),[])
        for key in ('shared_image_source_covariance_m2','higher_order_explanations','score'):self.assertNotIn(key,result)
        self.assertFalse(result.get('search',{}).get('complete',False))

    def test_every_inference_wrapper_forwards_cancel_and_progress(self):
        session,observations,_=fixture()
        for function in (inference.infer_scene,inference.infer_baseline,inference.infer_first_echo):
            with self.subTest(method=function.__name__):
                state={'cancelled':False};progress=[]
                def notify(fraction,message=''):
                    progress.append(fraction);state['cancelled']=True
                result=function(session,observations,cancel=lambda:state['cancelled'],progress=notify)
                self.assert_cancelled_without_geometry(result);self.assertTrue(progress)
                self.assert_cancelled_without_geometry(function(session,observations,cancel=lambda:True))

    def test_late_mapper_and_baseline_cancel_discard_unverified_geometry(self):
        original=inference._second_order_explanations
        for method in ('mapper','baseline'):
            state={'cancelled':False}
            def during_ambiguity(*args,**kwargs):state['cancelled']=True;return original(*args,**kwargs)
            with self.subTest(method=method),patch('echosight.inference._second_order_explanations',side_effect=during_ambiguity):
                result=process_session(self.session,method=method,cancel=lambda:state['cancelled'])
            self.assertTrue(state['cancelled']);self.assert_cancelled_without_geometry(result)
            self.assertEqual(len(result['observations']),12)
            self.assertEqual(len(result['provenance']['recordings']),12)

    def test_cli_interrupt_saves_cancelled_evidence_without_geometry(self):
        from echosight.cli import main
        original=inference._second_order_explanations
        def interrupt(*args,**kwargs):signal.raise_signal(signal.SIGINT);return original(*args,**kwargs)
        for method in ('mapper','baseline'):
            output=self.root/f'cancelled-{method}.json'
            with patch('echosight.inference._second_order_explanations',side_effect=interrupt),contextlib.redirect_stdout(io.StringIO()):
                code=main(['process',str(self.root/'raw'/'session.json'),'--method',method,'--output',str(output)])
            self.assertEqual(code,130);result=json.loads(output.read_text())
            self.assert_cancelled_without_geometry(result);self.assertEqual(len(result['observations']),12)

    def test_native_source_conflict_prevents_all_mapper_fits_preserves_raw_and_replay(self):
        session=self.native_session('conflict');before=copy.deepcopy(session)
        digests=[hashlib.sha256(Path(c['recording_path']).read_bytes()).hexdigest() for c in session['captures']]
        for method in ('mapper','baseline'):
            with patch('echosight.inference._run',side_effect=AssertionError('contradictory source entered fitting')):
                result=process_session(session,method=method)
            self.assertEqual(result['status'],'no_result');self.assertEqual(result['surfaces'],[])
            from tests.test_schemas import validator
            validator('result').validate(result)
            self.assertIn('native_source_declarations_conflict',str(result['diagnostics']))
            self.assertEqual(result['source_declaration_consistency']['status'],'contradictory')
            self.assertEqual(len(result['observations']),12)
            self.assertTrue(all(o['status']=='ok' for o in result['observations']))
            self.assertEqual([o['recording_sha256'] for o in result['observations']],digests)
        self.assertEqual(session,before)
        self.assertEqual([hashlib.sha256(Path(c['recording_path']).read_bytes()).hexdigest() for c in session['captures']],digests)
        with SessionStore(self.root/'store') as store:
            created=store.create_session(dict(session,captures=[]))
            for capture in session['captures']:
                store.add_recording(created['session_id'],capture['recording_path'],{k:capture[k] for k in ('capture_id','receiver_position_m','receiver_position_std_m','provenance') if k in capture})
            # The HTTP job route calls this same store/processor boundary.
            with patch('echosight.inference._run',side_effect=AssertionError('stored job bypassed source consistency')):
                job=store.start_job(created['session_id'],process_session);deadline=time.monotonic()+15
                while job['status'] in ('queued','running') and time.monotonic()<deadline:
                    time.sleep(.01);job=store.get_job(job['job_id'])
            self.assertEqual(job['status'],'completed',job)
            stored=store.get_result(created['session_id'])
            self.assertEqual(stored['status'],'no_result')
            self.assertEqual(stored['source_declaration_consistency']['status'],'contradictory')
            archive=store.export_session(created['session_id'])
            with SessionStore(self.root/'replay') as replay:
                imported=replay.import_archive(archive)
                with patch('echosight.inference._run',side_effect=AssertionError('replay bypassed source consistency')):
                    result=process_session(imported)
                self.assertEqual(result['source_declaration_consistency']['status'],'contradictory')
                self.assertEqual([o['recording_sha256'] for o in result['observations']],digests)

    def test_missing_and_consistent_declarations_are_not_hardware_validation(self):
        for case,expected in [('matching','consistent_declarations'),('unknown','unknown'),('mixed','incomplete')]:
            result=process_session(self.native_session(case))
            self.assertEqual(len(result['surfaces']),6,(case,result['diagnostics']))
            self.assertEqual(result['source_declaration_consistency']['status'],expected)
            self.assertFalse(result['provenance']['physical_validation'])
            from tests.test_schemas import validator
            validator('result').validate(result)

    def test_rejected_capture_still_exposes_known_source_conflict(self):
        session=self.native_session('matching')
        def reject_and_conflict(manifest):
            manifest['source_declaration'].update(configuration_id='different-source',probe_id='probe-one',route_id='speaker-one')
            manifest['events'].append(dict(type='interruption',at_frame=10,detail='software fixture'))
        raw,_,_=capture_bytes(self.samples[0],reject_and_conflict)
        path=Path(session['captures'][0]['recording_path']);path.write_bytes(raw)
        digest=hashlib.sha256(raw).hexdigest()
        with patch('echosight.inference._run',side_effect=AssertionError('rejected evidence hid source contradiction')):
            result=process_session(session)
        self.assertEqual(result['status'],'no_result')
        self.assertEqual(result['source_declaration_consistency']['status'],'contradictory')
        first=result['observations'][0]
        self.assertEqual(first['status'],'rejected')
        self.assertIn('acquisition_not_continuous',str(first['diagnostics']))
        self.assertEqual(first['recording_sha256'],digest)
        self.assertEqual(first['acquisition_evidence']['source_declaration']['configuration_id'],'different-source')
        self.assertEqual(path.read_bytes(),raw)
        self.assertEqual(sum(o['status']=='ok' for o in result['observations']),11)
        from tests.test_schemas import validator
        validator('result').validate(result)

    def test_shared_helper_source_fields_and_controlled_reuse(self):
        from echosight.acquisition import source_declaration_consistency
        from echosight.controlled import _native_control_conflicts
        base={'source_declaration':{'configuration_id':'source','probe_id':'probe','route_id':'output'}}
        for field in base['source_declaration']:
            other=copy.deepcopy(base);other['source_declaration'][field]='changed'
            summary=source_declaration_consistency([base,other])
            self.assertEqual(summary['conflicting_fields'],[field]);self.assertEqual(summary['status'],'contradictory')
        self.assertEqual(source_declaration_consistency([None,None])['status'],'unknown')
        self.assertEqual(source_declaration_consistency([base,None])['status'],'incomplete')
        evidence=copy.deepcopy(base);evidence.update(device={},recorder={},route_initial={},route_final={},session={'category':'record','mode':'measurement','activated_sample_rate_hz':48000})
        observations=[{'a':{'acquisition_evidence':copy.deepcopy(evidence)}} for _ in range(4)]
        protocol={'epochs':[{'source_configuration_id':'source'} for _ in range(4)]}
        self.assertEqual(_native_control_conflicts(protocol,observations,{'a'}),[])
        observations[2]['a']['acquisition_evidence']['source_declaration']['probe_id']='other'
        self.assertIn('native source probe_id differs across captures/epochs',_native_control_conflicts(protocol,observations,{'a'}))


class MultisourceAdmissionTests(unittest.TestCase):
    def test_prepared_per_session_consistency_and_independent_source_configurations(self):
        from echosight.multisource import infer_scene_bundle
        from tests.test_multisource import fixture as multi_fixture
        data,bundle=multi_fixture()
        for a,item in enumerate(data):
            for observation in item['observations']:
                observation['acquisition_evidence']={'source_declaration':{'configuration_id':f'calibrated-source-{a}','probe_id':'shared-probe','route_id':f'route-{a}'}}
        before=copy.deepcopy(data);positive=infer_scene_bundle(data,bundle)
        self.assertEqual(len(positive['surfaces']),6,positive['diagnostics'])
        self.assertEqual(data,before)
        self.assertTrue(all(s['status']=='consistent_declarations' for s in positive['source_declaration_consistency_by_session'].values()))
        for rejected in (False,True):
            bad=copy.deepcopy(data);o=bad[1]['observations'][0]
            o['acquisition_evidence']['source_declaration']['configuration_id']='contradiction'
            if rejected:o['status']='rejected'
            for method in ('mapper','plane_grid'):
                with patch('echosight.inference._proposals',side_effect=AssertionError('prepared contradiction entered fitting')):
                    result=infer_scene_bundle(bad,bundle,method=method)
                self.assertEqual(result['status'],'calibration_needed')
                self.assertEqual(result['surfaces'],[])
                self.assertIn('native_source_declarations_conflict',str(result['diagnostics']))
                self.assertEqual(result['processed_sessions'],bad)
        bad=copy.deepcopy(data);bad[0]['observations'][0]['acquisition_evidence']={'source_declaration':[]}
        self.assertEqual(infer_scene_bundle(bad,bundle)['status'],'calibration_needed')
        bad=copy.deepcopy(data);bad[0]['observations']*=5
        self.assertIn('resource limit',str(infer_scene_bundle(bad,bundle)['diagnostics']))

    def test_joint_late_cancel_discards_all_derived_geometry_but_keeps_inputs(self):
        from echosight import multisource
        from tests.test_multisource import fixture as multi_fixture
        data,bundle=multi_fixture();original=multisource._parent_subset_alternatives
        for stage in ('parent_check','final_callback'):
            state={'cancelled':False}
            def parent(*args,**kwargs):
                if stage=='parent_check':state['cancelled']=True
                return original(*args,**kwargs)
            def progress(fraction,message=''):
                if stage=='final_callback' and fraction==1:state['cancelled']=True
            with patch('echosight.multisource._parent_subset_alternatives',side_effect=parent):
                result=multisource.infer_scene_bundle(data,bundle,cancel=lambda:state['cancelled'],progress=progress)
            self.assertTrue(state['cancelled']);self.assertEqual(result['status'],'cancelled')
            for key in ('surfaces','hypotheses','dimensions','guidance'):self.assertEqual(result[key],[])
            for key in ('shared_plane_parameter_covariance_m2','score','parent_model_comparison','path_model_comparison'):self.assertNotIn(key,result)
            self.assertEqual(result['processed_sessions'],data)

    def test_multisource_raw_native_conflict_and_prepared_replay_retain_bytes(self):
        import numpy as np
        from echosight.multisource import process_scene_bundle,infer_scene_bundle
        from tests.test_multisource import fixture as multi_fixture
        data,bundle=multi_fixture(receivers=4);raw=copy.deepcopy(bundle);raw['sessions']=[]
        with tempfile.TemporaryDirectory() as tmp:
            paths=[];digests=[]
            for a,item in enumerate(data):
                session=copy.deepcopy(item['session']);session.update(probe={},captures=[])
                for i,observation in enumerate(item['observations']):
                    def mutate(m):m['source_declaration'].update(configuration_id=f'source-{a}' if i else 'contradiction',probe_id='shared-probe',route_id=f'route-{a}')
                    contents,_,_=capture_bytes(np.array([.01*(a*4+i+1),0,-.01,0]),mutate)
                    path=Path(tmp)/f'{a}-{i}.zip';path.write_bytes(contents);paths.append(path);digests.append(hashlib.sha256(contents).hexdigest())
                    session['captures'].append(dict(capture_id=observation['capture_id'],receiver_position_m=observation['receiver_position_m'],receiver_position_std_m=.002,receiver_pose_group_id=observation['receiver_pose_group_id'],recording_path=str(path)))
                raw['sessions'].append(session)
            before=copy.deepcopy(raw)
            # Real native byte admission and hash binding; analytic detector
            # outputs isolate per-session metadata transport from acoustics.
            with patch('echosight.signals.process_recording',side_effect=[copy.deepcopy(o) for item in data for o in item['observations']]),patch('echosight.inference._proposals',side_effect=AssertionError('raw contradiction entered joint fitting')):
                result=process_scene_bundle(raw)
            self.assertEqual(result['status'],'calibration_needed');self.assertEqual(result['surfaces'],[])
            observations=[o for item in result['processed_sessions'] for o in item['observations']]
            self.assertEqual([o['recording_sha256'] for o in observations],digests)
            self.assertEqual([hashlib.sha256(path.read_bytes()).hexdigest() for path in paths],digests)
            self.assertEqual(raw,before)
            with patch('echosight.inference._proposals',side_effect=AssertionError('prepared replay bypassed conflict')):
                replay=infer_scene_bundle(result['processed_sessions'],raw)
            self.assertEqual(replay['surfaces'],[]);self.assertIn('native_source_declarations_conflict',str(replay['diagnostics']))


class ReferenceCalibrationAdmissionTests(unittest.TestCase):
    def test_raw_native_source_conflict_blocks_reference_fit_but_no_result_alone_does_not(self):
        from echosight.calibration import calibrate_reference
        from tests.test_calibration import CalibrationTests
        CalibrationTests.setUpClass()
        try:
            session=copy.deepcopy(CalibrationTests.session);reference=copy.deepcopy(CalibrationTests.reference)
            # Verify no blanket rejection of ordinary no_result geometry.
            observations=process_session(session);observations['status']='no_result';observations['surfaces']=[]
            with patch('echosight.pipeline.process_session',return_value=observations):
                accepted=calibrate_reference(session,reference)
            self.assertEqual(accepted['status'],'calibration_proposal')
            digests=[]
            for i,capture in enumerate(session['captures']):
                samples,rate=read_recording(capture['recording_path']);self.assertEqual(rate,48000)
                def mutate(m):m['source_declaration'].update(configuration_id='reference-source' if i!=19 else 'different-source',probe_id='same-probe',route_id='same-output')
                raw,_,_=capture_bytes(samples,mutate);path=CalibrationTests.root/f'native-{i}.zip';path.write_bytes(raw)
                capture['recording_path']=str(path);digests.append(hashlib.sha256(raw).hexdigest())
            original=copy.deepcopy(session)
            with patch('echosight.calibration.least_squares',side_effect=AssertionError('contradictory reference source reached optimizer')):
                rejected=calibrate_reference(session,reference)
            self.assertEqual(rejected['status'],'rejected');self.assertNotIn('calibration',rejected)
            self.assertEqual(rejected['diagnostics'][0]['code'],'native_source_declarations_conflict')
            self.assertEqual(rejected['source_declaration_consistency']['status'],'contradictory')
            self.assertEqual(rejected['training_capture_ids'],reference['training_capture_ids'])
            self.assertEqual(rejected['validation_capture_ids'],reference['validation_capture_ids'])
            self.assertEqual([r['sha256'] for r in rejected['provenance']['recordings']],digests)
            self.assertEqual([hashlib.sha256(Path(c['recording_path']).read_bytes()).hexdigest() for c in session['captures']],digests)
            self.assertEqual(session,original)
        finally:CalibrationTests.tearDownClass()

if __name__=='__main__':unittest.main()
