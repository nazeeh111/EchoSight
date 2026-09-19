"""Pinned compact development observations, never runtime truth or work/ imports.

Extracted from immutable198d365 development1001/1003. Point controls are analytic;
finite-panel and hidden-corner observations came through PCM response extraction.
"""
import copy
import json
import unittest
import numpy as np
from echosight.path_alternatives import apply_path_alternatives,fit_point,prediction,derivatives
from echosight.multisource import _calibration,infer_scene_bundle
from echosight.inference import _Cancelled
from echosight.geometry import reflection_path


def fixture(name):
    case=copy.deepcopy(FIXTURES[name]);case['out']=dict(surfaces=case['surfaces'],hypotheses=[dict(hypothesis_id='existing',surfaces=[])],diagnostics=[],guidance=[],status='partial')
    return case


def apply(case,cancel=None):
    v,cov=_calibration(case['bundle'],len(case['processed_sessions']))
    apply_path_alternatives(case['out'],case['processed_sessions'],v,cov,cancel)
    return case['out']


class PathAlternativeTests(unittest.TestCase):
    def test_both_point_false_planes_challenged_without_changing_ids(self):
        for seed in [1001,1003]:
            case=fixture('point_scatterer-'+str(seed));before=copy.deepcopy(case['processed_sessions']);selected={(e['session_id'],e['capture_id'],e['candidate_id']) for e in case['surfaces'][0]['support']}
            out=apply(case);self.assertEqual(out['surfaces'],[]);self.assertEqual(out['status'],'ambiguous');self.assertEqual(out['hypotheses'][0]['hypothesis_id'],'existing')
            alt=next(h for h in out['hypotheses'] if h.get('kind')=='compact_scattering_location')
            self.assertEqual({tuple(k) for k in alt['selected_candidate_keys']},selected);self.assertEqual(len(alt['selected_candidate_keys']),len(selected));self.assertEqual(case['processed_sessions'],before)
            self.assertLess(alt['location_modes'][0]['score']['Q'],3);self.assertEqual(alt['location_status'],'unique_conditional_mode')
            json.dumps(out,allow_nan=False)

    def test_hidden_parent_physical_rays_and_five_coordinates(self):
        case=fixture('hidden_corner_four_sources-1003');out=apply(case)
        self.assertEqual(len(out['surfaces']),1);alt=next(h for h in out['hypotheses'] if h.get('kind')=='unobserved_two_reflection_family');self.assertEqual(alt['surfaces'],[])
        self.assertEqual(alt['operator']['parameter_count'],5);self.assertEqual(alt['operator']['local_rank'],5)
        lookup={(item['session']['session_id'],o['capture_id']):(item['session'],o) for item in case['processed_sessions'] for o in item['observations']}
        physical=alt['physical_example'];planes=[(np.array(p['normal']),p['offset_m']) for p in physical['planes']]
        for key,order,vertices,predicted in zip(alt['selected_candidate_keys'],physical['orders'],physical['path_vertices_m'],physical['predicted_delay_s']):
            session,o=lookup[tuple(key[:2])];s=np.array(session['source_position_m']);r=np.array(o['receiver_position_m']);path=reflection_path(s,r,[planes[i] for i in order]);self.assertIsNotNone(path)
            np.testing.assert_allclose(path['vertices_m'],vertices,atol=1e-9)
            self.assertAlmostEqual((path['length_m']-np.linalg.norm(s-r))/343,predicted,places=10)
        self.assertLess(physical['Q'],3)

    def test_seven_real_planes_retained(self):
        case=fixture('finite_panel_four_sources-1003');out=apply(case)
        self.assertEqual(len(out['surfaces']),7);self.assertEqual(len(out['hypotheses']),1)

    def test_mirror_modes_and_rank_deficient_uncertainty(self):
        rng=np.random.default_rng(33);s=rng.normal(size=(12,3));r=rng.normal(size=(12,3))+[2,0,0];s[:,2]=r[:,2]=0;p=np.array([3,2,1.])
        fit=fit_point(s,r,prediction(p,s,r,343),343,np.eye(12)*4e-10)
        self.assertEqual(fit['equal_quality_separated_minima'],2);self.assertEqual(fit['rank'],3)
        from echosight.path_alternatives import _point_modes
        rows=[dict(source_index=0,group=str(i),peak=dict(delay_std_s=2e-5),observation=dict(direct_std_s=0.,receiver_position_std_m=0.)) for i in range(len(s))]
        modes=_point_modes(fit,s,r,prediction(p,s,r,343),343,np.eye(12)*4e-10,1.,rows,np.zeros((4,4)))
        self.assertEqual(len(modes),2)
        s=np.tile([0.,0.,0.],(8,1));r=np.tile([1.,0.,0.],(8,1));fit=fit_point(s,r,prediction(p,s,r,343),343,np.eye(8)*4e-10)
        self.assertLess(fit['rank'],3);self.assertIsNone(fit['conditional_position_covariance_m2'])

    def test_search_boundary_does_not_claim_finite_unique_certainty(self):
        rng=np.random.default_rng(901);s=rng.normal(size=(12,3));r=rng.normal(size=(12,3))+[2,0,0]
        p=np.array([35.,2.,1.]);fit=fit_point(s,r,prediction(p,s,r,343),343,np.eye(12)*4e-10)
        self.assertTrue(fit['search_boundary_limited']);self.assertIsNone(fit['conditional_position_covariance_m2'])

    def test_derivatives_and_shared_covariance(self):
        from echosight.path_alternatives import _evidence
        case=fixture('point_scatterer-1001');v,cal=_calibration(case['bundle'],4);_,s,r,y,v,C,mu,_=_evidence(case['surfaces'][0],case['processed_sessions'],v,cal)
        _,_,_,_,_,low,_,_=_evidence(case['surfaces'][0],case['processed_sessions'],v,np.zeros_like(cal))
        self.assertGreater(np.max(abs(C-np.diag(np.diag(C)))),1e-12);self.assertGreater(np.linalg.norm(C-low),1e-10)
        p=np.array([3.,4.,2.]);J,Gs,Gr=derivatives(p,s,r,v)
        for k in range(3):
            h=np.eye(3)[k]*1e-5
            np.testing.assert_allclose((prediction(p+h,s,r,v)-prediction(p-h,s,r,v))/2e-5,J[:,k],atol=1e-10)
            np.testing.assert_allclose((prediction(p,s+h,r,v)-prediction(p,s-h,r,v))/2e-5,Gs[:,k],atol=1e-10)
            np.testing.assert_allclose((prediction(p,s,r+h,v)-prediction(p,s,r-h,v))/2e-5,Gr[:,k],atol=1e-10)

    def test_point_covariance_matches_independent_nuisance_sandwich(self):
        from echosight.path_alternatives import _evidence,_point_nuisance_covariance,_fixed_weight_covariance
        case=fixture('point_scatterer-1001');v,cal=_calibration(case['bundle'],4)
        rows,s,r,y,v,fixed,mu,_=_evidence(case['surfaces'][0],case['processed_sessions'],v,cal)
        # A PSD joint update creates explicit source/speed and cross-source terms.
        correlated=np.zeros(len(cal));correlated[0]=.03;correlated[7]=-.02;correlated[-1]=.9
        cal=cal+np.outer(correlated,correlated);p=np.array([-.4,5.1,1.15])
        groups=list(dict.fromkeys(row['group'] for row in rows));n=len(rows);size=len(cal)+3*len(groups)
        Sigma=np.zeros((size,size));Sigma[:len(cal),:len(cal)]=cal
        for g,group in enumerate(groups):
            std=next(row['observation']['receiver_position_std_m'] for row in rows if row['group']==group)
            Sigma[len(cal)+3*g:len(cal)+3*g+3,len(cal)+3*g:len(cal)+3*g+3]=np.eye(3)*std**2
        def independent_delays(delta,location=p):
            src=np.array([x+delta[3*row['source_index']:3*row['source_index']+3] for x,row in zip(s,rows)])
            rec=np.array([x+delta[len(cal)+3*groups.index(row['group']):len(cal)+3*groups.index(row['group'])+3] for x,row in zip(r,rows)])
            return (np.sqrt(np.sum((src-location)**2,axis=1))+np.sqrt(np.sum((rec-location)**2,axis=1))-np.sqrt(np.sum((src-rec)**2,axis=1)))/(v+delta[len(cal)-1])
        zero=np.zeros(size);G=np.empty((n,size));h=1e-5
        for k in range(size):
            d=np.eye(size)[k]*h;G[:,k]=(independent_delays(d)-independent_delays(-d))/(2*h)
        independent=[];mu=independent_delays(zero)
        for i,row in enumerate(rows):
            o=row['observation'];clock=o['clock'];independent.append(row['peak']['delay_std_s']**2+o['direct_std_s']**2+mu[i]**2*(clock['alpha_std']/clock['alpha'])**2)
        actual=G@Sigma@G.T+np.diag(independent)
        propagated=_point_nuisance_covariance(p,rows,s,r,v,cal)
        np.testing.assert_allclose(propagated,actual,rtol=2e-7,atol=2e-17)
        J=np.column_stack([(independent_delays(zero,p+np.eye(3)[k]*h)-independent_delays(zero,p-np.eye(3)[k]*h))/(2*h) for k in range(3)])
        W=np.linalg.inv(fixed);influence=np.linalg.solve(J.T@W@J,J.T@W);expected=influence@actual@influence.T
        obtained=_fixed_weight_covariance(derivatives(p,s,r,v)[0],fixed,propagated)
        np.testing.assert_allclose(obtained,expected,rtol=3e-7,atol=1e-11)
        dropped=cal.copy();dropped[:-1,-1]=0;dropped[-1,:-1]=0
        without_cross=_point_nuisance_covariance(p,rows,s,r,v,dropped)
        self.assertGreater(np.linalg.norm(propagated-without_cross),1e-10)
        wrong=np.linalg.inv(J.T@W@J)
        self.assertGreater(np.linalg.norm(expected-wrong),1e-5)

    def test_exported_point_covariance_is_mode_specific_sandwich(self):
        from echosight.path_alternatives import _evidence,_point_nuisance_covariance,_fixed_weight_covariance
        case=fixture('point_scatterer-1001');v,cal=_calibration(case['bundle'],4)
        rows,s,r,y,v,fixed,_,_=_evidence(case['surfaces'][0],case['processed_sessions'],v,cal)
        out=apply(case);alt=next(h for h in out['hypotheses'] if h.get('kind')=='compact_scattering_location')
        for mode in alt['location_modes']:
            p=np.array(mode['position_m']);actual=_point_nuisance_covariance(p,rows,s,r,v,cal)
            expected=_fixed_weight_covariance(derivatives(p,s,r,v)[0],fixed,actual)
            np.testing.assert_allclose(mode['conditional_covariance_m2'],expected,rtol=1e-10,atol=1e-12)
            self.assertIn('Mode-specific',mode['covariance_semantics'])

    def test_postfit_error_clears_geometry_and_marks_retained_hypotheses(self):
        from unittest.mock import patch
        case=fixture('point_scatterer-1001')
        def malformed_group(out,processed,*args,**kwargs):
            out['hypotheses'].append(dict(hypothesis_id='partial-check',surfaces=out['surfaces']))
            corrupt=copy.deepcopy(processed)
            for item in corrupt:
                for observation in item['observations']:observation.pop('receiver_pose_group_id',None)
            apply_path_alternatives(out,corrupt,*args,**kwargs)
        with patch('echosight.path_alternatives.apply_path_alternatives',side_effect=malformed_group):
            out=infer_scene_bundle(case['processed_sessions'],case['bundle'])
        self.assertEqual(out['status'],'calibration_needed');self.assertEqual(out['surfaces'],[])
        self.assertIn('selected receiver survey group is missing',out['diagnostics'])
        self.assertTrue(out['hypotheses'])
        self.assertTrue(all(h['verification_status']=='unverified_due_to_processing_error' for h in out['hypotheses']))

    def test_cancellation_is_atomic_and_resource_limit_precedes_fit(self):
        case=fixture('point_scatterer-1001');before=copy.deepcopy(case['out']);calls=[0]
        def cancel():
            calls[0]+=1
            return calls[0]>30
        with self.assertRaises(_Cancelled):apply(case,cancel)
        self.assertEqual(case['out'],before)
        case=fixture('point_scatterer-1001');case['surfaces'][0]['support']*=4
        with self.assertRaisesRegex(ValueError,'record budget'):apply(case)

    def test_duplicate_candidate_record_rejected(self):
        case=fixture('point_scatterer-1001');case['surfaces'][0]['support'].append(case['surfaces'][0]['support'][0])
        with self.assertRaisesRegex(ValueError,'one candidate per recording'):apply(case)

    def test_capture_group_fallback_and_missing_candidate_are_explicit(self):
        case=fixture('point_scatterer-1001')
        for item in case['processed_sessions']:
            item['session']['captures']=[dict(capture_id=o['capture_id'],receiver_pose_group_id=o.pop('receiver_pose_group_id')) for o in item['observations']]
        self.assertEqual(apply(case)['surfaces'],[])
        case=fixture('point_scatterer-1001');case['surfaces'][0]['support'][0]['candidate_id']='missing'
        with self.assertRaisesRegex(ValueError,'selected candidate is missing'):apply(case)

    def test_cancelled_joint_result_has_no_definitive_geometry(self):
        from unittest.mock import patch
        case=fixture('point_scatterer-1001')
        with patch('echosight.path_alternatives.apply_path_alternatives',side_effect=_Cancelled):
            out=infer_scene_bundle(case['processed_sessions'],case['bundle'])
        self.assertEqual(out['status'],'cancelled');self.assertEqual(out['surfaces'],[])

    def test_native_raw_entry_rejects_interruption_and_preserves_evidence(self):
        import hashlib,tempfile
        from pathlib import Path
        from unittest.mock import patch
        from scipy.io import wavfile
        from tests.test_acquisition import capture_bytes
        from echosight.multisource import process_scene_bundle
        from echosight.signals import generate_probe
        # Independent review reproduction: physically rendered direct + two
        # planar echoes, wrapped in packages reporting an actual interruption.
        sources=np.array([[1.2,1.1,.9],[1.8,1.1,.9],[1.2,1.7,.9],[1.3,1.3,1.5]])
        rng=np.random.default_rng(990);receivers=rng.uniform([.6,.6,.3],[3.5,3.2,2.7],(8,3))
        probe,metadata=generate_probe({'period_s':.35,'high_hz':14000.});fs=metadata['sample_rate_hz'];xt=np.arange(len(probe))/fs
        c=343.;ks=1.003;speed=c/ks
        bundle=dict(schema_version='1.0',scene_id='raw-admission',coordinate_frame_id='frame',scene_static=True,
            shared_calibration=dict(effective_speed_m_s=speed,effective_speed_std_m_s=.1,covariance_assumption='explicit_source_pose_covariance_independent_speed',source_pose_joint_covariance_m2=(np.eye(12)*.002**2).tolist()),sessions=[])
        hashes=[];paths=[]
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            for a,source in enumerate(sources):
                session=dict(schema_version='1.0',session_id=f's{a}',coordinate_frame_id='frame',source_position_m=source.tolist(),source_position_std_m=.002,sound_speed_m_s=c,source_clock_scale=ks,probe=metadata,captures=[])
                for i,receiver in enumerate(receivers):
                    kr=1.004+rng.uniform(-.0002,.0002);times=(np.arange(len(probe)+round(.2*fs))/fs-.055)/(kr/ks)
                    wall=source.copy();wall[0]=9-source[0];ceiling=source.copy();ceiling[2]=6.4-source[2];samples=np.zeros(len(times))
                    for position,amplitude in [(source,.48),(wall,.2),(ceiling,.17)]:
                        samples+=amplitude*np.interp(times-ks*np.linalg.norm(receiver-position)/c,xt,probe,left=0,right=0)
                    samples+=rng.normal(0,1e-5,len(samples))
                    raw,_,_=capture_bytes(samples,lambda m:m['events'].append(dict(type='interruption',at_frame=10,detail='review regression')))
                    path=root/f'{a}-{i}.zip';path.write_bytes(raw);paths.append(path);hashes.append(hashlib.sha256(raw).hexdigest())
                    session['captures'].append(dict(capture_id=str(i),receiver_position_m=receiver.tolist(),receiver_position_std_m=.002,receiver_pose_group_id=f'r{i}',recording_path=str(path),provenance='simulated',diagnostics=['supplied-check']))
                bundle['sessions'].append(session)
            with patch('echosight.signals.process_recording',side_effect=AssertionError('inadmissible package reached detector')):
                out=process_scene_bundle(bundle)
            observations=[o for item in out['processed_sessions'] for o in item['observations']]
            self.assertEqual(len(observations),32);self.assertEqual(out['surfaces'],[])
            for observation,digest in zip(observations,hashes):
                self.assertEqual(observation['status'],'rejected');self.assertEqual(observation['recording_sha256'],digest)
                self.assertEqual(observation['input_format'],'echosight_capture_zip');self.assertIn('supplied-check',observation['input_diagnostics'])
                self.assertFalse(observation['acquisition_evidence']['processing_eligible'])
                self.assertEqual(observation['diagnostics'][0]['code'],'acquisition_not_continuous')
            # Eligible native evidence reaches the detector, while the same
            # package with an incorrect manifest hash does not.
            eligible,_,_=capture_bytes(np.array([.0,.01,.0,-.01],dtype=np.float32));paths[0].write_bytes(eligible)
            detector_result=dict(capture_id='0',status='rejected',candidates=[],diagnostics=[dict(code='test_detector',message='admission only')])
            with patch('echosight.signals.process_recording',return_value=detector_result) as detector:
                admitted=process_scene_bundle(bundle)
            self.assertEqual(detector.call_count,1)
            first=admitted['processed_sessions'][0]['observations'][0]
            self.assertTrue(first['acquisition_evidence']['processing_eligible'])
            self.assertEqual(first['recording_sha256'],hashlib.sha256(eligible).hexdigest())
            bundle['sessions'][0]['captures'][0]['sha256']='0'*64
            with patch('echosight.signals.process_recording',side_effect=AssertionError('checksum mismatch reached detector')):
                mismatch=process_scene_bundle(bundle)
            first=mismatch['processed_sessions'][0]['observations'][0]
            self.assertIn('checksum differs',first['diagnostics'][0]['message'])
            self.assertEqual(first['recording_sha256'],hashlib.sha256(eligible).hexdigest())
            bundle['sessions'][0]['captures'][0].pop('sha256')
            # A nonfinite Float32 recording rejects only that capture and does
            # not abort preservation of the other 31 raw admission decisions.
            wavfile.write(paths[0],fs,np.array([np.nan,0.,0.],dtype=np.float32))
            with patch('echosight.signals.process_recording',side_effect=AssertionError('invalid samples reached detector')):
                out=process_scene_bundle(bundle)
            observations=[o for item in out['processed_sessions'] for o in item['observations']]
            self.assertEqual(len(observations),32);self.assertEqual(out['surfaces'],[])
            self.assertIn('nonfinite',observations[0]['diagnostics'][0]['message'])
            self.assertEqual(observations[0]['diagnostics'][0]['code'],'recording_rejected')

    def test_exact_decoded_copies_across_source_sessions_reject_every_container(self):
        import hashlib,io,struct,tempfile
        from pathlib import Path
        from scipy.io import wavfile
        from tests.test_acquisition import capture_bytes
        from echosight.multisource import process_scene_bundle
        from echosight.signals import generate_probe
        rng=np.random.default_rng(717);receivers=rng.uniform([.6,.6,.3],[3.5,3.2,2.7],(8,3))
        sources=np.array([[1.2,1.1,.9],[1.8,1.1,.9],[1.2,1.7,.9],[1.3,1.3,1.5]])
        probe,metadata=generate_probe({'period_s':.35,'high_hz':14000.});rate=metadata['sample_rate_hz'];times=np.arange(len(probe)+6000)/rate
        waves=[]
        for receiver in receivers:
            source=sources[0];image=source.copy();image[2]=6.4-source[2]
            samples=.5*np.interp(times-.05-np.linalg.norm(receiver-source)/343,np.arange(len(probe))/rate,probe,left=0,right=0)
            samples+=.2*np.interp(times-.05-np.linalg.norm(receiver-image)/343,np.arange(len(probe))/rate,probe,left=0,right=0)
            waves.append(np.rint(samples*32767).astype('<i2'))
        bundle=dict(schema_version='1.0',scene_id='cross-source-copy',coordinate_frame_id='frame',scene_static=True,sessions=[],
            shared_calibration=dict(effective_speed_m_s=343.,effective_speed_std_m_s=.1,covariance_assumption='explicit_source_pose_covariance_independent_speed',source_pose_joint_covariance_m2=(np.eye(12)*.002**2).tolist()))
        expected={}
        with tempfile.TemporaryDirectory() as tmp:
            for a,source in enumerate(sources):
                session=dict(schema_version='1.0',session_id=f's{a}',coordinate_frame_id='frame',source_position_m=source.tolist(),probe=metadata,captures=[])
                for i,(receiver,pcm) in enumerate(zip(receivers,waves)):
                    stream=io.BytesIO();wavfile.write(stream,rate,pcm if a in (0,2) else pcm.astype(np.float32)/32768);raw=stream.getvalue()
                    if a==2:
                        # A valid JUNK chunk changes raw bytes without samples.
                        raw=raw[:4]+struct.pack('<I',len(raw)+4)+raw[8:]+b'JUNK'+struct.pack('<I',4)+b'test'
                    elif a==3:raw=capture_bytes(pcm.astype(np.float32)/32768)[0]
                    path=Path(tmp)/f'{a}-{i}.wav';path.write_bytes(raw);expected[(f's{a}',str(i))]=hashlib.sha256(raw).hexdigest()
                    session['captures'].append(dict(capture_id=str(i),receiver_position_m=receiver.tolist(),receiver_position_std_m=.002,receiver_pose_group_id=f'r{i}',recording_path=str(path),provenance='simulated',waveform_sha256='untrusted-manifest-value'))
                bundle['sessions'].append(session)
            out=process_scene_bundle(bundle)
        observations=[o for item in out['processed_sessions'] for o in item['observations']]
        self.assertEqual(len(observations),32);self.assertEqual(out['surfaces'],[])
        self.assertEqual(len({o['waveform_sha256'] for o in observations}),8)
        self.assertEqual(len({o['recording_sha256'] for o in observations}),32)
        for o in observations:
            self.assertEqual(o['status'],'rejected');self.assertEqual(o['candidates'],[])
            self.assertIn('recording_waveform_reused',[d['code'] for d in o['diagnostics']])
            self.assertEqual(o['recording_sha256'],expected[(o['session_id'],o['capture_id'])])
            self.assertEqual({(p['session_id'],p['capture_id']) for p in o['duplicate_waveform_group']},{(f's{a}',o['capture_id']) for a in range(4)})
            self.assertNotEqual(o['waveform_sha256'],'untrusted-manifest-value')

    def test_joint_integration_retains_existing_source_diversity_guard(self):
        case=fixture('point_scatterer-1001');out=infer_scene_bundle(case['processed_sessions'],case['bundle'])
        self.assertEqual(out['status'],'ambiguous',out['diagnostics']);self.assertEqual(out['surfaces'],[])
        self.assertTrue(any(h.get('kind')=='compact_scattering_location' for h in out['hypotheses']))
        case=fixture('point_scatterer-1001')
        for item in case['processed_sessions']:item['session']['source_position_m'][2]=1.
        # An insufficient-source scene must not be rescued into definitive geometry.
        out=infer_scene_bundle(case['processed_sessions'],case['bundle']);self.assertEqual(out['surfaces'],[])


FIXTURES = json.loads(r'''
{
 "point_scatterer-1001": {
  "bundle": {
   "shared_calibration": {
    "effective_speed_m_s": 343.0,
    "effective_speed_std_m_s": 0.6,
    "covariance_assumption": "explicit_source_pose_covariance_independent_speed",
    "source_pose_joint_covariance_m2": [
     [
      2.4999999999999998e-05,
      0.0,
      0.0,
      9e-06,
      0.0,
      0.0,
      9e-06,
      0.0,
      0.0,
      9e-06,
      0.0,
      0.0
     ],
     [
      0.0,
      2.4999999999999998e-05,
      0.0,
      0.0,
      9e-06,
      0.0,
      0.0,
      9e-06,
      0.0,
      0.0,
      9e-06,
      0.0
     ],
     [
      0.0,
      0.0,
      2.4999999999999998e-05,
      0.0,
      0.0,
      9e-06,
      0.0,
      0.0,
      9e-06,
      0.0,
      0.0,
      9e-06
     ],
     [
      9e-06,
      0.0,
      0.0,
      2.4999999999999998e-05,
      0.0,
      0.0,
      9e-06,
      0.0,
      0.0,
      9e-06,
      0.0,
      0.0
     ],
     [
      0.0,
      9e-06,
      0.0,
      0.0,
      2.4999999999999998e-05,
      0.0,
      0.0,
      9e-06,
      0.0,
      0.0,
      9e-06,
      0.0
     ],
     [
      0.0,
      0.0,
      9e-06,
      0.0,
      0.0,
      2.4999999999999998e-05,
      0.0,
      0.0,
      9e-06,
      0.0,
      0.0,
      9e-06
     ],
     [
      9e-06,
      0.0,
      0.0,
      9e-06,
      0.0,
      0.0,
      2.4999999999999998e-05,
      0.0,
      0.0,
      9e-06,
      0.0,
      0.0
     ],
     [
      0.0,
      9e-06,
      0.0,
      0.0,
      9e-06,
      0.0,
      0.0,
      2.4999999999999998e-05,
      0.0,
      0.0,
      9e-06,
      0.0
     ],
     [
      0.0,
      0.0,
      9e-06,
      0.0,
      0.0,
      9e-06,
      0.0,
      0.0,
      2.4999999999999998e-05,
      0.0,
      0.0,
      9e-06
     ],
     [
      9e-06,
      0.0,
      0.0,
      9e-06,
      0.0,
      0.0,
      9e-06,
      0.0,
      0.0,
      2.4999999999999998e-05,
      0.0,
      0.0
     ],
     [
      0.0,
      9e-06,
      0.0,
      0.0,
      9e-06,
      0.0,
      0.0,
      9e-06,
      0.0,
      0.0,
      2.4999999999999998e-05,
      0.0
     ],
     [
      0.0,
      0.0,
      9e-06,
      0.0,
      0.0,
      9e-06,
      0.0,
      0.0,
      9e-06,
      0.0,
      0.0,
      2.4999999999999998e-05
     ]
    ]
   },
   "schema_version": "1.0",
   "scene_id": "compact-development",
   "coordinate_frame_id": "test-frame",
   "scene_static": true
  },
  "processed_sessions": [
   {
    "session": {
     "session_id": "relocation-room_four_sources-1001-source-00",
     "source_position_m": [
      -1.8228475909221284,
      3.3168107935670967,
      -0.08864888787342048
     ],
     "coordinate_frame_id": "test-frame"
    },
    "observations": [
     {
      "capture_id": "capture-03",
      "receiver_position_m": [
       -1.379176488501579,
       4.400134589125614,
       0.4392794688134826
      ],
      "receiver_position_std_m": 0.006,
      "receiver_pose_group_id": "receiver-pose-03",
      "candidates": [
       {
        "candidate_id": "capture-03:control",
        "delay_s": 0.007954929207414576,
        "delay_std_s": 4.16666666667e-05,
        "amplitude": 0.5
       }
      ],
      "clock": {
       "alpha": 0.9997599353216721,
       "alpha_std": 1.1248942649084144e-06
      },
      "direct_std_s": 4.1666666666666665e-05,
      "status": "ok"
     },
     {
      "capture_id": "capture-05",
      "receiver_position_m": [
       -2.0217284524452235,
       2.602629086071488,
       -0.09711260641289299
      ],
      "receiver_position_std_m": 0.006,
      "receiver_pose_group_id": "receiver-pose-05",
      "candidates": [
       {
        "candidate_id": "capture-05:control",
        "delay_s": 0.014878262716794793,
        "delay_std_s": 4.16666666667e-05,
        "amplitude": 0.5
       }
      ],
      "clock": {
       "alpha": 1.000017945530168,
       "alpha_std": 1.1248942649084144e-06
      },
      "direct_std_s": 4.1666666666666665e-05,
      "status": "ok"
     },
     {
      "capture_id": "capture-09",
      "receiver_position_m": [
       -2.179400422075555,
       3.6516513948207248,
       0.19537874340948308
      ],
      "receiver_position_std_m": 0.006,
      "receiver_pose_group_id": "receiver-pose-09",
      "candidates": [
       {
        "candidate_id": "capture-09:control",
        "delay_s": 0.013210458677614577,
        "delay_std_s": 4.16666666667e-05,
        "amplitude": 0.5
       }
      ],
      "clock": {
       "alpha": 0.9999876827389281,
       "alpha_std": 1.1248942649084144e-06
      },
      "direct_std_s": 4.1666666666666665e-05,
      "status": "ok"
     },
     {
      "capture_id": "capture-10",
      "receiver_position_m": [
       -2.5155968829077064,
       2.792601915067517,
       -0.4359050750970385
      ],
      "receiver_position_std_m": 0.006,
      "receiver_pose_group_id": "receiver-pose-10",
      "candidates": [
       {
        "candidate_id": "capture-10:control",
        "delay_s": 0.015168312941700039,
        "delay_std_s": 4.16666666667e-05,
        "amplitude": 0.5
       }
      ],
      "clock": {
       "alpha": 0.999868845732347,
       "alpha_std": 1.1248942649084144e-06
      },
      "direct_std_s": 4.1666666666666665e-05,
      "status": "ok"
     },
     {
      "capture_id": "capture-11",
      "receiver_position_m": [
       -2.201990289957457,
       2.7563195306074837,
       0.21900505590135522
      ],
      "receiver_position_std_m": 0.006,
      "receiver_pose_group_id": "receiver-pose-11",
      "candidates": [
       {
        "candidate_id": "capture-11:control",
        "delay_s": 0.0145224880035062,
        "delay_std_s": 4.16666666667e-05,
        "amplitude": 0.5
       }
      ],
      "clock": {
       "alpha": 1.000001892554826,
       "alpha_std": 1.1248942649084144e-06
      },
      "direct_std_s": 4.1666666666666665e-05,
      "status": "ok"
     }
    ]
   },
   {
    "session": {
     "session_id": "relocation-room_four_sources-1001-source-01",
     "source_position_m": [
      -1.5061707433384328,
      4.003656139422727,
      -0.08961409274937512
     ],
     "coordinate_frame_id": "test-frame"
    },
    "observations": [
     {
      "capture_id": "capture-03",
      "receiver_position_m": [
       -1.379176488501579,
       4.400134589125614,
       0.4392794688134826
      ],
      "receiver_position_std_m": 0.006,
      "receiver_pose_group_id": "receiver-pose-03",
      "candidates": [
       {
        "candidate_id": "capture-03:control",
        "delay_s": 0.007934975788437618,
        "delay_std_s": 4.16666666667e-05,
        "amplitude": 0.5
       }
      ],
      "clock": {
       "alpha": 1.000052908303762,
       "alpha_std": 1.1248942649084144e-06
      },
      "direct_std_s": 4.1666666666666665e-05,
      "status": "ok"
     },
     {
      "capture_id": "capture-04",
      "receiver_position_m": [
       -2.338913746661562,
       3.189361916104354,
       1.4381803998243514
      ],
      "receiver_position_std_m": 0.006,
      "receiver_pose_group_id": "receiver-pose-04",
      "candidates": [
       {
        "candidate_id": "capture-04:control",
        "delay_s": 0.008274569580028623,
        "delay_std_s": 4.16666666667e-05,
        "amplitude": 0.5
       }
      ],
      "clock": {
       "alpha": 1.0001507762558448,
       "alpha_std": 1.1248942649084144e-06
      },
      "direct_std_s": 4.1666666666666665e-05,
      "status": "ok"
     },
     {
      "capture_id": "capture-05",
      "receiver_position_m": [
       -2.0217284524452235,
       2.602629086071488,
       -0.09711260641289299
      ],
      "receiver_position_std_m": 0.006,
      "receiver_pose_group_id": "receiver-pose-05",
      "candidates": [
       {
        "candidate_id": "capture-05:control",
        "delay_s": 0.010920805276187705,
        "delay_std_s": 4.16666666667e-05,
        "amplitude": 0.5
       }
      ],
      "clock": {
       "alpha": 1.0001020643198413,
       "alpha_std": 1.1248942649084144e-06
      },
      "direct_std_s": 4.1666666666666665e-05,
      "status": "ok"
     },
     {
      "capture_id": "capture-08",
      "receiver_position_m": [
       -2.526858334203329,
       2.8696232106668287,
       1.5966782368142498
      ],
      "receiver_position_std_m": 0.006,
      "receiver_pose_group_id": "receiver-pose-08",
      "candidates": [
       {
        "candidate_id": "capture-08:control",
        "delay_s": 0.008320908229256054,
        "delay_std_s": 4.16666666667e-05,
        "amplitude": 0.5
       }
      ],
      "clock": {
       "alpha": 0.9997714326736532,
       "alpha_std": 1.1248942649084144e-06
      },
      "direct_std_s": 4.1666666666666665e-05,
      "status": "ok"
     },
     {
      "capture_id": "capture-09",
      "receiver_position_m": [
       -2.179400422075555,
       3.6516513948207248,
       0.19537874340948308
      ],
      "receiver_position_std_m": 0.006,
      "receiver_pose_group_id": "receiver-pose-09",
      "candidates": [
       {
        "candidate_id": "capture-09:control",
        "delay_s": 0.010728225245850712,
        "delay_std_s": 4.16666666667e-05,
        "amplitude": 0.5
       }
      ],
      "clock": {
       "alpha": 0.9997681483177787,
       "alpha_std": 1.1248942649084144e-06
      },
      "direct_std_s": 4.1666666666666665e-05,
      "status": "ok"
     },
     {
      "capture_id": "capture-10",
      "receiver_position_m": [
       -2.5155968829077064,
       2.792601915067517,
       -0.4359050750970385
      ],
      "receiver_position_std_m": 0.006,
      "receiver_pose_group_id": "receiver-pose-10",
      "candidates": [
       {
        "candidate_id": "capture-10:control",
        "delay_s": 0.01136291022584651,
        "delay_std_s": 4.16666666667e-05,
        "amplitude": 0.5
       }
      ],
      "clock": {
       "alpha": 0.9997886061628743,
       "alpha_std": 1.1248942649084144e-06
      },
      "direct_std_s": 4.1666666666666665e-05,
      "status": "ok"
     },
     {
      "capture_id": "capture-11",
      "receiver_position_m": [
       -2.201990289957457,
       2.7563195306074837,
       0.21900505590135522
      ],
      "receiver_position_std_m": 0.006,
      "receiver_pose_group_id": "receiver-pose-11",
      "candidates": [
       {
        "candidate_id": "capture-11:control",
        "delay_s": 0.010647820136710602,
        "delay_std_s": 4.16666666667e-05,
        "amplitude": 0.5
       }
      ],
      "clock": {
       "alpha": 0.999962839304475,
       "alpha_std": 1.1248942649084144e-06
      },
      "direct_std_s": 4.1666666666666665e-05,
      "status": "ok"
     }
    ]
   },
   {
    "session": {
     "session_id": "relocation-room_four_sources-1001-source-02",
     "source_position_m": [
      -2.4990389263888098,
      3.6319598728042264,
      -0.09067194434580597
     ],
     "coordinate_frame_id": "test-frame"
    },
    "observations": [
     {
      "capture_id": "capture-01",
      "receiver_position_m": [
       -1.0610743541374785,
       3.850873461606965,
       -0.36847745375646646
      ],
      "receiver_position_std_m": 0.006,
      "receiver_pose_group_id": "receiver-pose-01",
      "candidates": [
       {
        "candidate_id": "capture-01:control",
        "delay_s": 0.010052899662883478,
        "delay_std_s": 4.16666666667e-05,
        "amplitude": 0.5
       }
      ],
      "clock": {
       "alpha": 0.9999471094148416,
       "alpha_std": 1.1248942649084144e-06
      },
      "direct_std_s": 4.1666666666666665e-05,
      "status": "ok"
     },
     {
      "capture_id": "capture-03",
      "receiver_position_m": [
       -1.379176488501579,
       4.400134589125614,
       0.4392794688134826
      ],
      "receiver_position_std_m": 0.006,
      "receiver_pose_group_id": "receiver-pose-03",
      "candidates": [
       {
        "candidate_id": "capture-03:control",
        "delay_s": 0.008093621146332658,
        "delay_std_s": 4.16666666667e-05,
        "amplitude": 0.5
       }
      ],
      "clock": {
       "alpha": 0.9999522981211125,
       "alpha_std": 1.1248942649084144e-06
      },
      "direct_std_s": 4.1666666666666665e-05,
      "status": "ok"
     },
     {
      "capture_id": "capture-05",
      "receiver_position_m": [
       -2.0217284524452235,
       2.602629086071488,
       -0.09711260641289299
      ],
      "receiver_position_std_m": 0.006,
      "receiver_pose_group_id": "receiver-pose-05",
      "candidates": [
       {
        "candidate_id": "capture-05:control",
        "delay_s": 0.01446878850615839,
        "delay_std_s": 4.16666666667e-05,
        "amplitude": 0.5
       }
      ],
      "clock": {
       "alpha": 1.0000802345574866,
       "alpha_std": 1.1248942649084144e-06
      },
      "direct_std_s": 4.1666666666666665e-05,
      "status": "ok"
     },
     {
      "capture_id": "capture-09",
      "receiver_position_m": [
       -2.179400422075555,
       3.6516513948207248,
       0.19537874340948308
      ],
      "receiver_position_std_m": 0.006,
      "receiver_pose_group_id": "receiver-pose-09",
      "candidates": [
       {
        "candidate_id": "capture-09:control",
        "delay_s": 0.014288967388268433,
        "delay_std_s": 4.16666666667e-05,
        "amplitude": 0.5
       }
      ],
      "clock": {
       "alpha": 0.9998920328948885,
       "alpha_std": 1.1248942649084144e-06
      },
      "direct_std_s": 4.1666666666666665e-05,
      "status": "ok"
     },
     {
      "capture_id": "capture-10",
      "receiver_position_m": [
       -2.5155968829077064,
       2.792601915067517,
       -0.4359050750970385
      ],
      "receiver_position_std_m": 0.006,
      "receiver_pose_group_id": "receiver-pose-10",
      "candidates": [
       {
        "candidate_id": "capture-10:control",
        "delay_s": 0.015929368280739764,
        "delay_std_s": 4.16666666667e-05,
        "amplitude": 0.5
       }
      ],
      "clock": {
       "alpha": 1.0000798292809527,
       "alpha_std": 1.1248942649084144e-06
      },
      "direct_std_s": 4.1666666666666665e-05,
      "status": "ok"
     },
     {
      "capture_id": "capture-11",
      "receiver_position_m": [
       -2.201990289957457,
       2.7563195306074837,
       0.21900505590135522
      ],
      "receiver_position_std_m": 0.006,
      "receiver_pose_group_id": "receiver-pose-11",
      "candidates": [
       {
        "candidate_id": "capture-11:control",
        "delay_s": 0.014514923778385778,
        "delay_std_s": 4.16666666667e-05,
        "amplitude": 0.5
       }
      ],
      "clock": {
       "alpha": 0.999937354567914,
       "alpha_std": 1.1248942649084144e-06
      },
      "direct_std_s": 4.1666666666666665e-05,
      "status": "ok"
     }
    ]
   },
   {
    "session": {
     "session_id": "relocation-room_four_sources-1001-source-03",
     "source_position_m": [
      -1.9384575962145283,
      3.5423938089421143,
      0.5057133496330527
     ],
     "coordinate_frame_id": "test-frame"
    },
    "observations": [
     {
      "capture_id": "capture-00",
      "receiver_position_m": [
       -0.7374090629934841,
       4.362207242282512,
       -0.2519931606760347
      ],
      "receiver_position_std_m": 0.006,
      "receiver_pose_group_id": "receiver-pose-00",
      "candidates": [
       {
        "candidate_id": "capture-00:control",
        "delay_s": 0.006608567669221215,
        "delay_std_s": 4.16666666667e-05,
        "amplitude": 0.5
       }
      ],
      "clock": {
       "alpha": 0.9998973824882246,
       "alpha_std": 1.1248942649084144e-06
      },
      "direct_std_s": 4.1666666666666665e-05,
      "status": "ok"
     },
     {
      "capture_id": "capture-01",
      "receiver_position_m": [
       -1.0610743541374785,
       3.850873461606965,
       -0.36847745375646646
      ],
      "receiver_position_std_m": 0.006,
      "receiver_pose_group_id": "receiver-pose-01",
      "candidates": [
       {
        "candidate_id": "capture-01:control",
        "delay_s": 0.009051335820781827,
        "delay_std_s": 4.16666666667e-05,
        "amplitude": 0.5
       }
      ],
      "clock": {
       "alpha": 1.0000645945824298,
       "alpha_std": 1.1248942649084144e-06
      },
      "direct_std_s": 4.1666666666666665e-05,
      "status": "ok"
     },
     {
      "capture_id": "capture-03",
      "receiver_position_m": [
       -1.379176488501579,
       4.400134589125614,
       0.4392794688134826
      ],
      "receiver_position_std_m": 0.006,
      "receiver_pose_group_id": "receiver-pose-03",
      "candidates": [
       {
        "candidate_id": "capture-03:control",
        "delay_s": 0.007803596889982343,
        "delay_std_s": 4.16666666667e-05,
        "amplitude": 0.5
       }
      ],
      "clock": {
       "alpha": 0.9999218022394121,
       "alpha_std": 1.1248942649084144e-06
      },
      "direct_std_s": 4.1666666666666665e-05,
      "status": "ok"
     },
     {
      "capture_id": "capture-05",
      "receiver_position_m": [
       -2.0217284524452235,
       2.602629086071488,
       -0.09711260641289299
      ],
      "receiver_position_std_m": 0.006,
      "receiver_pose_group_id": "receiver-pose-05",
      "candidates": [
       {
        "candidate_id": "capture-05:control",
        "delay_s": 0.012896853714194127,
        "delay_std_s": 4.16666666667e-05,
        "amplitude": 0.5
       }
      ],
      "clock": {
       "alpha": 1.0002135080337442,
       "alpha_std": 1.1248942649084144e-06
      },
      "direct_std_s": 4.1666666666666665e-05,
      "status": "ok"
     },
     {
      "capture_id": "capture-09",
      "receiver_position_m": [
       -2.179400422075555,
       3.6516513948207248,
       0.19537874340948308
      ],
      "receiver_position_std_m": 0.006,
      "receiver_pose_group_id": "receiver-pose-09",
      "candidates": [
       {
        "candidate_id": "capture-09:control",
        "delay_s": 0.012774971902018635,
        "delay_std_s": 4.16666666667e-05,
        "amplitude": 0.5
       }
      ],
      "clock": {
       "alpha": 0.9998124194833947,
       "alpha_std": 1.1248942649084144e-06
      },
      "direct_std_s": 4.1666666666666665e-05,
      "status": "ok"
     },
     {
      "capture_id": "capture-10",
      "receiver_position_m": [
       -2.5155968829077064,
       2.792601915067517,
       -0.4359050750970385
      ],
      "receiver_position_std_m": 0.006,
      "receiver_pose_group_id": "receiver-pose-10",
      "candidates": [
       {
        "candidate_id": "capture-10:control",
        "delay_s": 0.0130743955456893,
        "delay_std_s": 4.16666666667e-05,
        "amplitude": 0.5
       }
      ],
      "clock": {
       "alpha": 1.0000136805595983,
       "alpha_std": 1.1248942649084144e-06
      },
      "direct_std_s": 4.1666666666666665e-05,
      "status": "ok"
     },
     {
      "capture_id": "capture-11",
      "receiver_position_m": [
       -2.201990289957457,
       2.7563195306074837,
       0.21900505590135522
      ],
      "receiver_position_std_m": 0.006,
      "receiver_pose_group_id": "receiver-pose-11",
      "candidates": [
       {
        "candidate_id": "capture-11:control",
        "delay_s": 0.013203960435747706,
        "delay_std_s": 4.16666666667e-05,
        "amplitude": 0.5
       }
      ],
      "clock": {
       "alpha": 1.0001259166596597,
       "alpha_std": 1.1248942649084144e-06
      },
      "direct_std_s": 4.1666666666666665e-05,
      "status": "ok"
     }
    ]
   }
  ],
  "surfaces": [
   {
    "surface_id": "reflector-8b239b45caea1d53",
    "normal": [
     0.6064579868659522,
     0.6695829350864752,
     0.42879762500214214
    ],
    "offset_m": 3.6953844721995197,
    "support": [
     {
      "session_id": "relocation-room_four_sources-1001-source-00",
      "capture_id": "capture-03",
      "candidate_id": "capture-03:control"
     },
     {
      "session_id": "relocation-room_four_sources-1001-source-00",
      "capture_id": "capture-05",
      "candidate_id": "capture-05:control"
     },
     {
      "session_id": "relocation-room_four_sources-1001-source-00",
      "capture_id": "capture-09",
      "candidate_id": "capture-09:control"
     },
     {
      "session_id": "relocation-room_four_sources-1001-source-00",
      "capture_id": "capture-10",
      "candidate_id": "capture-10:control"
     },
     {
      "session_id": "relocation-room_four_sources-1001-source-00",
      "capture_id": "capture-11",
      "candidate_id": "capture-11:control"
     },
     {
      "session_id": "relocation-room_four_sources-1001-source-01",
      "capture_id": "capture-03",
      "candidate_id": "capture-03:control"
     },
     {
      "session_id": "relocation-room_four_sources-1001-source-01",
      "capture_id": "capture-04",
      "candidate_id": "capture-04:control"
     },
     {
      "session_id": "relocation-room_four_sources-1001-source-01",
      "capture_id": "capture-05",
      "candidate_id": "capture-05:control"
     },
     {
      "session_id": "relocation-room_four_sources-1001-source-01",
      "capture_id": "capture-08",
      "candidate_id": "capture-08:control"
     },
     {
      "session_id": "relocation-room_four_sources-1001-source-01",
      "capture_id": "capture-09",
      "candidate_id": "capture-09:control"
     },
     {
      "session_id": "relocation-room_four_sources-1001-source-01",
      "capture_id": "capture-10",
      "candidate_id": "capture-10:control"
     },
     {
      "session_id": "relocation-room_four_sources-1001-source-01",
      "capture_id": "capture-11",
      "candidate_id": "capture-11:control"
     },
     {
      "session_id": "relocation-room_four_sources-1001-source-02",
      "capture_id": "capture-01",
      "candidate_id": "capture-01:control"
     },
     {
      "session_id": "relocation-room_four_sources-1001-source-02",
      "capture_id": "capture-03",
      "candidate_id": "capture-03:control"
     },
     {
      "session_id": "relocation-room_four_sources-1001-source-02",
      "capture_id": "capture-05",
      "candidate_id": "capture-05:control"
     },
     {
      "session_id": "relocation-room_four_sources-1001-source-02",
      "capture_id": "capture-09",
      "candidate_id": "capture-09:control"
     },
     {
      "session_id": "relocation-room_four_sources-1001-source-02",
      "capture_id": "capture-10",
      "candidate_id": "capture-10:control"
     },
     {
      "session_id": "relocation-room_four_sources-1001-source-02",
      "capture_id": "capture-11",
      "candidate_id": "capture-11:control"
     },
     {
      "session_id": "relocation-room_four_sources-1001-source-03",
      "capture_id": "capture-00",
      "candidate_id": "capture-00:control"
     },
     {
      "session_id": "relocation-room_four_sources-1001-source-03",
      "capture_id": "capture-01",
      "candidate_id": "capture-01:control"
     },
     {
      "session_id": "relocation-room_four_sources-1001-source-03",
      "capture_id": "capture-03",
      "candidate_id": "capture-03:control"
     },
     {
      "session_id": "relocation-room_four_sources-1001-source-03",
      "capture_id": "capture-05",
      "candidate_id": "capture-05:control"
     },
     {
      "session_id": "relocation-room_four_sources-1001-source-03",
      "capture_id": "capture-09",
      "candidate_id": "capture-09:control"
     },
     {
      "session_id": "relocation-room_four_sources-1001-source-03",
      "capture_id": "capture-10",
      "candidate_id": "capture-10:control"
     },
     {
      "session_id": "relocation-room_four_sources-1001-source-03",
      "capture_id": "capture-11",
      "candidate_id": "capture-11:control"
     }
    ]
   }
  ]
 },
 "point_scatterer-1003": {
  "bundle": {
   "shared_calibration": {
    "effective_speed_m_s": 343.0,
    "effective_speed_std_m_s": 0.6,
    "covariance_assumption": "explicit_source_pose_covariance_independent_speed",
    "source_pose_joint_covariance_m2": [
     [
      2.4999999999999998e-05,
      0.0,
      0.0,
      9e-06,
      0.0,
      0.0,
      9e-06,
      0.0,
      0.0,
      9e-06,
      0.0,
      0.0
     ],
     [
      0.0,
      2.4999999999999998e-05,
      0.0,
      0.0,
      9e-06,
      0.0,
      0.0,
      9e-06,
      0.0,
      0.0,
      9e-06,
      0.0
     ],
     [
      0.0,
      0.0,
      2.4999999999999998e-05,
      0.0,
      0.0,
      9e-06,
      0.0,
      0.0,
      9e-06,
      0.0,
      0.0,
      9e-06
     ],
     [
      9e-06,
      0.0,
      0.0,
      2.4999999999999998e-05,
      0.0,
      0.0,
      9e-06,
      0.0,
      0.0,
      9e-06,
      0.0,
      0.0
     ],
     [
      0.0,
      9e-06,
      0.0,
      0.0,
      2.4999999999999998e-05,
      0.0,
      0.0,
      9e-06,
      0.0,
      0.0,
      9e-06,
      0.0
     ],
     [
      0.0,
      0.0,
      9e-06,
      0.0,
      0.0,
      2.4999999999999998e-05,
      0.0,
      0.0,
      9e-06,
      0.0,
      0.0,
      9e-06
     ],
     [
      9e-06,
      0.0,
      0.0,
      9e-06,
      0.0,
      0.0,
      2.4999999999999998e-05,
      0.0,
      0.0,
      9e-06,
      0.0,
      0.0
     ],
     [
      0.0,
      9e-06,
      0.0,
      0.0,
      9e-06,
      0.0,
      0.0,
      2.4999999999999998e-05,
      0.0,
      0.0,
      9e-06,
      0.0
     ],
     [
      0.0,
      0.0,
      9e-06,
      0.0,
      0.0,
      9e-06,
      0.0,
      0.0,
      2.4999999999999998e-05,
      0.0,
      0.0,
      9e-06
     ],
     [
      9e-06,
      0.0,
      0.0,
      9e-06,
      0.0,
      0.0,
      9e-06,
      0.0,
      0.0,
      2.4999999999999998e-05,
      0.0,
      0.0
     ],
     [
      0.0,
      9e-06,
      0.0,
      0.0,
      9e-06,
      0.0,
      0.0,
      9e-06,
      0.0,
      0.0,
      2.4999999999999998e-05,
      0.0
     ],
     [
      0.0,
      0.0,
      9e-06,
      0.0,
      0.0,
      9e-06,
      0.0,
      0.0,
      9e-06,
      0.0,
      0.0,
      2.4999999999999998e-05
     ]
    ]
   },
   "schema_version": "1.0",
   "scene_id": "compact-development",
   "coordinate_frame_id": "test-frame",
   "scene_static": true
  },
  "processed_sessions": [
   {
    "session": {
     "session_id": "relocation-room_four_sources-1003-source-00",
     "source_position_m": [
      -0.5838621455383515,
      1.3100239529940036,
      0.3387816039546151
     ],
     "coordinate_frame_id": "test-frame"
    },
    "observations": [
     {
      "capture_id": "capture-00",
      "receiver_position_m": [
       -1.021216344640526,
       3.2583296014536223,
       1.4728190422780376
      ],
      "receiver_position_std_m": 0.006,
      "receiver_pose_group_id": "receiver-pose-00",
      "candidates": [
       {
        "candidate_id": "capture-00:control",
        "delay_s": 0.008167809958380358,
        "delay_std_s": 4.16666666667e-05,
        "amplitude": 0.5
       }
      ],
      "clock": {
       "alpha": 0.9998802094224984,
       "alpha_std": 1.1248942649084144e-06
      },
      "direct_std_s": 4.1666666666666665e-05,
      "status": "ok"
     },
     {
      "capture_id": "capture-03",
      "receiver_position_m": [
       -1.1737507032858958,
       3.6170450710342545,
       0.6397477566420586
      ],
      "receiver_position_std_m": 0.006,
      "receiver_pose_group_id": "receiver-pose-03",
      "candidates": [
       {
        "candidate_id": "capture-03:control",
        "delay_s": 0.008926165609012889,
        "delay_std_s": 4.16666666667e-05,
        "amplitude": 0.5
       }
      ],
      "clock": {
       "alpha": 0.9997917311487416,
       "alpha_std": 1.1248942649084144e-06
      },
      "direct_std_s": 4.1666666666666665e-05,
      "status": "ok"
     },
     {
      "capture_id": "capture-07",
      "receiver_position_m": [
       -1.3297304443562432,
       2.8218684105853358,
       0.9384998473377993
      ],
      "receiver_position_std_m": 0.006,
      "receiver_pose_group_id": "receiver-pose-07",
      "candidates": [
       {
        "candidate_id": "capture-07:control",
        "delay_s": 0.011381741881530088,
        "delay_std_s": 4.16666666667e-05,
        "amplitude": 0.5
       }
      ],
      "clock": {
       "alpha": 0.999804953774074,
       "alpha_std": 1.1248942649084144e-06
      },
      "direct_std_s": 4.1666666666666665e-05,
      "status": "ok"
     },
     {
      "capture_id": "capture-08",
      "receiver_position_m": [
       -2.4295750269935374,
       2.696309754572328,
       0.06711956893777604
      ],
      "receiver_position_std_m": 0.006,
      "receiver_pose_group_id": "receiver-pose-08",
      "candidates": [
       {
        "candidate_id": "capture-08:control",
        "delay_s": 0.013644006467772377,
        "delay_std_s": 4.16666666667e-05,
        "amplitude": 0.5
       }
      ],
      "clock": {
       "alpha": 1.0002216088935214,
       "alpha_std": 1.1248942649084144e-06
      },
      "direct_std_s": 4.1666666666666665e-05,
      "status": "ok"
     },
     {
      "capture_id": "capture-10",
      "receiver_position_m": [
       -1.6225591466580747,
       3.5386181421966616,
       0.0405879612259283
      ],
      "receiver_position_std_m": 0.006,
      "receiver_pose_group_id": "receiver-pose-10",
      "candidates": [
       {
        "candidate_id": "capture-10:control",
        "delay_s": 0.010765022273264873,
        "delay_std_s": 4.16666666667e-05,
        "amplitude": 0.5
       }
      ],
      "clock": {
       "alpha": 0.9999687322227558,
       "alpha_std": 1.1248942649084144e-06
      },
      "direct_std_s": 4.1666666666666665e-05,
      "status": "ok"
     }
    ]
   },
   {
    "session": {
     "session_id": "relocation-room_four_sources-1003-source-01",
     "source_position_m": [
      -0.010690466427334948,
      1.8058326795345345,
      0.3387049325890533
     ],
     "coordinate_frame_id": "test-frame"
    },
    "observations": [
     {
      "capture_id": "capture-00",
      "receiver_position_m": [
       -1.021216344640526,
       3.2583296014536223,
       1.4728190422780376
      ],
      "receiver_position_std_m": 0.006,
      "receiver_pose_group_id": "receiver-pose-00",
      "candidates": [
       {
        "candidate_id": "capture-00:control",
        "delay_s": 0.007043755536746001,
        "delay_std_s": 4.16666666667e-05,
        "amplitude": 0.5
       }
      ],
      "clock": {
       "alpha": 1.0002088966363043,
       "alpha_std": 1.1248942649084144e-06
      },
      "direct_std_s": 4.1666666666666665e-05,
      "status": "ok"
     },
     {
      "capture_id": "capture-03",
      "receiver_position_m": [
       -1.1737507032858958,
       3.6170450710342545,
       0.6397477566420586
      ],
      "receiver_position_std_m": 0.006,
      "receiver_pose_group_id": "receiver-pose-03",
      "candidates": [
       {
        "candidate_id": "capture-03:control",
        "delay_s": 0.007908482009734994,
        "delay_std_s": 4.16666666667e-05,
        "amplitude": 0.5
       }
      ],
      "clock": {
       "alpha": 0.9998459914859706,
       "alpha_std": 1.1248942649084144e-06
      },
      "direct_std_s": 4.1666666666666665e-05,
      "status": "ok"
     },
     {
      "capture_id": "capture-07",
      "receiver_position_m": [
       -1.3297304443562432,
       2.8218684105853358,
       0.9384998473377993
      ],
      "receiver_position_std_m": 0.006,
      "receiver_pose_group_id": "receiver-pose-07",
      "candidates": [
       {
        "candidate_id": "capture-07:control",
        "delay_s": 0.00977317315877187,
        "delay_std_s": 4.16666666667e-05,
        "amplitude": 0.5
       }
      ],
      "clock": {
       "alpha": 0.9998758310883146,
       "alpha_std": 1.1248942649084144e-06
      },
      "direct_std_s": 4.1666666666666665e-05,
      "status": "ok"
     },
     {
      "capture_id": "capture-08",
      "receiver_position_m": [
       -2.4295750269935374,
       2.696309754572328,
       0.06711956893777604
      ],
      "receiver_position_std_m": 0.006,
      "receiver_pose_group_id": "receiver-pose-08",
      "candidates": [
       {
        "candidate_id": "capture-08:control",
        "delay_s": 0.011174512894250444,
        "delay_std_s": 4.16666666667e-05,
        "amplitude": 0.5
       }
      ],
      "clock": {
       "alpha": 1.0002273699556168,
       "alpha_std": 1.1248942649084144e-06
      },
      "direct_std_s": 4.1666666666666665e-05,
      "status": "ok"
     },
     {
      "capture_id": "capture-10",
      "receiver_position_m": [
       -1.6225591466580747,
       3.5386181421966616,
       0.0405879612259283
      ],
      "receiver_position_std_m": 0.006,
      "receiver_pose_group_id": "receiver-pose-10",
      "candidates": [
       {
        "candidate_id": "capture-10:control",
        "delay_s": 0.009311310103264796,
        "delay_std_s": 4.16666666667e-05,
        "amplitude": 0.5
       }
      ],
      "clock": {
       "alpha": 0.9998900412126932,
       "alpha_std": 1.1248942649084144e-06
      },
      "direct_std_s": 4.1666666666666665e-05,
      "status": "ok"
     }
    ]
   },
   {
    "session": {
     "session_id": "relocation-room_four_sources-1003-source-02",
     "source_position_m": [
      -1.063937097976136,
      1.8816893934796273,
      0.3439300468451523
     ],
     "coordinate_frame_id": "test-frame"
    },
    "observations": [
     {
      "capture_id": "capture-00",
      "receiver_position_m": [
       -1.021216344640526,
       3.2583296014536223,
       1.4728190422780376
      ],
      "receiver_position_std_m": 0.006,
      "receiver_pose_group_id": "receiver-pose-00",
      "candidates": [
       {
        "candidate_id": "capture-00:control",
        "delay_s": 0.009142629263502311,
        "delay_std_s": 4.16666666667e-05,
        "amplitude": 0.5
       }
      ],
      "clock": {
       "alpha": 0.9998498320970454,
       "alpha_std": 1.1248942649084144e-06
      },
      "direct_std_s": 4.1666666666666665e-05,
      "status": "ok"
     },
     {
      "capture_id": "capture-03",
      "receiver_position_m": [
       -1.1737507032858958,
       3.6170450710342545,
       0.6397477566420586
      ],
      "receiver_position_std_m": 0.006,
      "receiver_pose_group_id": "receiver-pose-03",
      "candidates": [
       {
        "candidate_id": "capture-03:control",
        "delay_s": 0.010203275919842707,
        "delay_std_s": 4.16666666667e-05,
        "amplitude": 0.5
       }
      ],
      "clock": {
       "alpha": 0.9998221536388737,
       "alpha_std": 1.1248942649084144e-06
      },
      "direct_std_s": 4.1666666666666665e-05,
      "status": "ok"
     },
     {
      "capture_id": "capture-04",
      "receiver_position_m": [
       -1.6578127465714712,
       1.7224861066104302,
       0.9859871915932342
      ],
      "receiver_position_std_m": 0.006,
      "receiver_pose_group_id": "receiver-pose-04",
      "candidates": [
       {
        "candidate_id": "capture-04:control",
        "delay_s": 0.01597229096050568,
        "delay_std_s": 4.16666666667e-05,
        "amplitude": 0.5
       }
      ],
      "clock": {
       "alpha": 1.0000639976293886,
       "alpha_std": 1.1248942649084144e-06
      },
      "direct_std_s": 4.1666666666666665e-05,
      "status": "ok"
     },
     {
      "capture_id": "capture-07",
      "receiver_position_m": [
       -1.3297304443562432,
       2.8218684105853358,
       0.9384998473377993
      ],
      "receiver_position_std_m": 0.006,
      "receiver_pose_group_id": "receiver-pose-07",
      "candidates": [
       {
        "candidate_id": "capture-07:control",
        "delay_s": 0.012684775859362249,
        "delay_std_s": 4.16666666667e-05,
        "amplitude": 0.5
       }
      ],
      "clock": {
       "alpha": 0.999880186807938,
       "alpha_std": 1.1248942649084144e-06
      },
      "direct_std_s": 4.1666666666666665e-05,
      "status": "ok"
     },
     {
      "capture_id": "capture-08",
      "receiver_position_m": [
       -2.4295750269935374,
       2.696309754572328,
       0.06711956893777604
      ],
      "receiver_position_std_m": 0.006,
      "receiver_pose_group_id": "receiver-pose-08",
      "candidates": [
       {
        "candidate_id": "capture-08:control",
        "delay_s": 0.015165744275904836,
        "delay_std_s": 4.16666666667e-05,
        "amplitude": 0.5
       }
      ],
      "clock": {
       "alpha": 0.9998934628503491,
       "alpha_std": 1.1248942649084144e-06
      },
      "direct_std_s": 4.1666666666666665e-05,
      "status": "ok"
     },
     {
      "capture_id": "capture-09",
      "receiver_position_m": [
       -1.1321620082574537,
       2.103783246650004,
       0.6031821071277661
      ],
      "receiver_position_std_m": 0.006,
      "receiver_pose_group_id": "receiver-pose-09",
      "candidates": [
       {
        "candidate_id": "capture-09:control",
        "delay_s": 0.01613589702565202,
        "delay_std_s": 4.16666666667e-05,
        "amplitude": 0.5
       }
      ],
      "clock": {
       "alpha": 0.9999009668159238,
       "alpha_std": 1.1248942649084144e-06
      },
      "direct_std_s": 4.1666666666666665e-05,
      "status": "ok"
     }
    ]
   },
   {
    "session": {
     "session_id": "relocation-room_four_sources-1003-source-03",
     "source_position_m": [
      -0.5998043873611618,
      1.5599228361353603,
      0.9369995665007834
     ],
     "coordinate_frame_id": "test-frame"
    },
    "observations": [
     {
      "capture_id": "capture-00",
      "receiver_position_m": [
       -1.021216344640526,
       3.2583296014536223,
       1.4728190422780376
      ],
      "receiver_position_std_m": 0.006,
      "receiver_pose_group_id": "receiver-pose-00",
      "candidates": [
       {
        "candidate_id": "capture-00:control",
        "delay_s": 0.008303627592787789,
        "delay_std_s": 4.16666666667e-05,
        "amplitude": 0.5
       }
      ],
      "clock": {
       "alpha": 0.9999704545270237,
       "alpha_std": 1.1248942649084144e-06
      },
      "direct_std_s": 4.1666666666666665e-05,
      "status": "ok"
     },
     {
      "capture_id": "capture-03",
      "receiver_position_m": [
       -1.1737507032858958,
       3.6170450710342545,
       0.6397477566420586
      ],
      "receiver_position_std_m": 0.006,
      "receiver_pose_group_id": "receiver-pose-03",
      "candidates": [
       {
        "candidate_id": "capture-03:control",
        "delay_s": 0.008351724197082702,
        "delay_std_s": 4.16666666667e-05,
        "amplitude": 0.5
       }
      ],
      "clock": {
       "alpha": 0.9997562136183781,
       "alpha_std": 1.1248942649084144e-06
      },
      "direct_std_s": 4.1666666666666665e-05,
      "status": "ok"
     },
     {
      "capture_id": "capture-07",
      "receiver_position_m": [
       -1.3297304443562432,
       2.8218684105853358,
       0.9384998473377993
      ],
      "receiver_position_std_m": 0.006,
      "receiver_pose_group_id": "receiver-pose-07",
      "candidates": [
       {
        "candidate_id": "capture-07:control",
        "delay_s": 0.011130650132896953,
        "delay_std_s": 4.16666666667e-05,
        "amplitude": 0.5
       }
      ],
      "clock": {
       "alpha": 1.000008959533991,
       "alpha_std": 1.1248942649084144e-06
      },
      "direct_std_s": 4.1666666666666665e-05,
      "status": "ok"
     },
     {
      "capture_id": "capture-08",
      "receiver_position_m": [
       -2.4295750269935374,
       2.696309754572328,
       0.06711956893777604
      ],
      "receiver_position_std_m": 0.006,
      "receiver_pose_group_id": "receiver-pose-08",
      "candidates": [
       {
        "candidate_id": "capture-08:control",
        "delay_s": 0.012446426404350685,
        "delay_std_s": 4.16666666667e-05,
        "amplitude": 0.5
       }
      ],
      "clock": {
       "alpha": 1.0000342142310656,
       "alpha_std": 1.1248942649084144e-06
      },
      "direct_std_s": 4.1666666666666665e-05,
      "status": "ok"
     },
     {
      "capture_id": "capture-10",
      "receiver_position_m": [
       -1.6225591466580747,
       3.5386181421966616,
       0.0405879612259283
      ],
      "receiver_position_std_m": 0.006,
      "receiver_pose_group_id": "receiver-pose-10",
      "candidates": [
       {
        "candidate_id": "capture-10:control",
        "delay_s": 0.009766129843302858,
        "delay_std_s": 4.16666666667e-05,
        "amplitude": 0.5
       }
      ],
      "clock": {
       "alpha": 0.9998687413549835,
       "alpha_std": 1.1248942649084144e-06
      },
      "direct_std_s": 4.1666666666666665e-05,
      "status": "ok"
     }
    ]
   }
  ],
  "surfaces": [
   {
    "surface_id": "reflector-c720985da4726cd5",
    "normal": [
     0.6759450625621998,
     0.5732311862830494,
     0.4631460671001231
    ],
    "offset_m": 3.563189521941981,
    "support": [
     {
      "session_id": "relocation-room_four_sources-1003-source-00",
      "capture_id": "capture-00",
      "candidate_id": "capture-00:control"
     },
     {
      "session_id": "relocation-room_four_sources-1003-source-00",
      "capture_id": "capture-03",
      "candidate_id": "capture-03:control"
     },
     {
      "session_id": "relocation-room_four_sources-1003-source-00",
      "capture_id": "capture-07",
      "candidate_id": "capture-07:control"
     },
     {
      "session_id": "relocation-room_four_sources-1003-source-00",
      "capture_id": "capture-08",
      "candidate_id": "capture-08:control"
     },
     {
      "session_id": "relocation-room_four_sources-1003-source-00",
      "capture_id": "capture-10",
      "candidate_id": "capture-10:control"
     },
     {
      "session_id": "relocation-room_four_sources-1003-source-01",
      "capture_id": "capture-00",
      "candidate_id": "capture-00:control"
     },
     {
      "session_id": "relocation-room_four_sources-1003-source-01",
      "capture_id": "capture-03",
      "candidate_id": "capture-03:control"
     },
     {
      "session_id": "relocation-room_four_sources-1003-source-01",
      "capture_id": "capture-07",
      "candidate_id": "capture-07:control"
     },
     {
      "session_id": "relocation-room_four_sources-1003-source-01",
      "capture_id": "capture-08",
      "candidate_id": "capture-08:control"
     },
     {
      "session_id": "relocation-room_four_sources-1003-source-01",
      "capture_id": "capture-10",
      "candidate_id": "capture-10:control"
     },
     {
      "session_id": "relocation-room_four_sources-1003-source-02",
      "capture_id": "capture-00",
      "candidate_id": "capture-00:control"
     },
     {
      "session_id": "relocation-room_four_sources-1003-source-02",
      "capture_id": "capture-03",
      "candidate_id": "capture-03:control"
     },
     {
      "session_id": "relocation-room_four_sources-1003-source-02",
      "capture_id": "capture-04",
      "candidate_id": "capture-04:control"
     },
     {
      "session_id": "relocation-room_four_sources-1003-source-02",
      "capture_id": "capture-07",
      "candidate_id": "capture-07:control"
     },
     {
      "session_id": "relocation-room_four_sources-1003-source-02",
      "capture_id": "capture-08",
      "candidate_id": "capture-08:control"
     },
     {
      "session_id": "relocation-room_four_sources-1003-source-02",
      "capture_id": "capture-09",
      "candidate_id": "capture-09:control"
     },
     {
      "session_id": "relocation-room_four_sources-1003-source-03",
      "capture_id": "capture-00",
      "candidate_id": "capture-00:control"
     },
     {
      "session_id": "relocation-room_four_sources-1003-source-03",
      "capture_id": "capture-03",
      "candidate_id": "capture-03:control"
     },
     {
      "session_id": "relocation-room_four_sources-1003-source-03",
      "capture_id": "capture-07",
      "candidate_id": "capture-07:control"
     },
     {
      "session_id": "relocation-room_four_sources-1003-source-03",
      "capture_id": "capture-08",
      "candidate_id": "capture-08:control"
     },
     {
      "session_id": "relocation-room_four_sources-1003-source-03",
      "capture_id": "capture-10",
      "candidate_id": "capture-10:control"
     }
    ]
   }
  ]
 },
 "hidden_corner_four_sources-1003": {
  "bundle": {
   "shared_calibration": {
    "effective_speed_m_s": 343.0,
    "effective_speed_std_m_s": 0.6,
    "covariance_assumption": "explicit_source_pose_covariance_independent_speed",
    "source_pose_joint_covariance_m2": [
     [
      2.4999999999999998e-05,
      0.0,
      0.0,
      9e-06,
      0.0,
      0.0,
      9e-06,
      0.0,
      0.0,
      9e-06,
      0.0,
      0.0
     ],
     [
      0.0,
      2.4999999999999998e-05,
      0.0,
      0.0,
      9e-06,
      0.0,
      0.0,
      9e-06,
      0.0,
      0.0,
      9e-06,
      0.0
     ],
     [
      0.0,
      0.0,
      2.4999999999999998e-05,
      0.0,
      0.0,
      9e-06,
      0.0,
      0.0,
      9e-06,
      0.0,
      0.0,
      9e-06
     ],
     [
      9e-06,
      0.0,
      0.0,
      2.4999999999999998e-05,
      0.0,
      0.0,
      9e-06,
      0.0,
      0.0,
      9e-06,
      0.0,
      0.0
     ],
     [
      0.0,
      9e-06,
      0.0,
      0.0,
      2.4999999999999998e-05,
      0.0,
      0.0,
      9e-06,
      0.0,
      0.0,
      9e-06,
      0.0
     ],
     [
      0.0,
      0.0,
      9e-06,
      0.0,
      0.0,
      2.4999999999999998e-05,
      0.0,
      0.0,
      9e-06,
      0.0,
      0.0,
      9e-06
     ],
     [
      9e-06,
      0.0,
      0.0,
      9e-06,
      0.0,
      0.0,
      2.4999999999999998e-05,
      0.0,
      0.0,
      9e-06,
      0.0,
      0.0
     ],
     [
      0.0,
      9e-06,
      0.0,
      0.0,
      9e-06,
      0.0,
      0.0,
      2.4999999999999998e-05,
      0.0,
      0.0,
      9e-06,
      0.0
     ],
     [
      0.0,
      0.0,
      9e-06,
      0.0,
      0.0,
      9e-06,
      0.0,
      0.0,
      2.4999999999999998e-05,
      0.0,
      0.0,
      9e-06
     ],
     [
      9e-06,
      0.0,
      0.0,
      9e-06,
      0.0,
      0.0,
      9e-06,
      0.0,
      0.0,
      2.4999999999999998e-05,
      0.0,
      0.0
     ],
     [
      0.0,
      9e-06,
      0.0,
      0.0,
      9e-06,
      0.0,
      0.0,
      9e-06,
      0.0,
      0.0,
      2.4999999999999998e-05,
      0.0
     ],
     [
      0.0,
      0.0,
      9e-06,
      0.0,
      0.0,
      9e-06,
      0.0,
      0.0,
      9e-06,
      0.0,
      0.0,
      2.4999999999999998e-05
     ]
    ]
   },
   "schema_version": "1.0",
   "scene_id": "compact-development",
   "coordinate_frame_id": "test-frame",
   "scene_static": true
  },
  "processed_sessions": [
   {
    "session": {
     "session_id": "relocation-hidden_corner_four_sources-1003-source-00",
     "source_position_m": [
      -0.5838621455383515,
      1.3100239529940036,
      0.3387816039546151
     ],
     "coordinate_frame_id": "test-frame"
    },
    "observations": [
     {
      "capture_id": "capture-00",
      "receiver_position_m": [
       -1.021216344640526,
       3.2583296014536223,
       1.4728190422780376
      ],
      "receiver_position_std_m": 0.006,
      "receiver_pose_group_id": "receiver-pose-00",
      "candidates": [
       {
        "candidate_id": "capture-00:echo:00",
        "delay_s": 0.004353729443182197,
        "delay_std_s": 4.1666666666666665e-05,
        "amplitude": 0.425585831065481
       },
       {
        "candidate_id": "capture-00:echo:01",
        "delay_s": 0.011440659925950428,
        "delay_std_s": 4.1666666666666665e-05,
        "amplitude": 0.16998435355225183
       }
      ],
      "clock": {
       "alpha": 0.9998802094228082,
       "alpha_std": 1.1248942649084144e-06
      },
      "direct_std_s": 4.1666666666666665e-05,
      "status": "ok"
     },
     {
      "capture_id": "capture-01",
      "receiver_position_m": [
       -1.3395350103286499,
       2.28426746056934,
       2.0939675115427914
      ],
      "receiver_position_std_m": 0.006,
      "receiver_pose_group_id": "receiver-pose-01",
      "candidates": [
       {
        "candidate_id": "capture-01:echo:00",
        "delay_s": 0.002141509752290095,
        "delay_std_s": 4.1666666666666665e-05,
        "amplitude": 0.5121665318954317
       },
       {
        "candidate_id": "capture-01:echo:01",
        "delay_s": 0.00963684184033255,
        "delay_std_s": 4.1666666666666665e-05,
        "amplitude": 0.1738443617870572
       }
      ],
      "clock": {
       "alpha": 0.9999337006569768,
       "alpha_std": 1.1248942649084144e-06
      },
      "direct_std_s": 4.1666666666666665e-05,
      "status": "ok"
     },
     {
      "capture_id": "capture-02",
      "receiver_position_m": [
       0.2553713673204093,
       1.943866596104725,
       0.012289491846311801
      ],
      "receiver_position_std_m": 0.006,
      "receiver_pose_group_id": "receiver-pose-02",
      "candidates": [
       {
        "candidate_id": "capture-02:echo:00",
        "delay_s": 0.010733538362704399,
        "delay_std_s": 4.1666666666666665e-05,
        "amplitude": 0.15699049739555296
       }
      ],
      "clock": {
       "alpha": 1.0000371690125849,
       "alpha_std": 1.1248942649084144e-06
      },
      "direct_std_s": 4.1666666666666665e-05,
      "status": "ok"
     },
     {
      "capture_id": "capture-03",
      "receiver_position_m": [
       -1.1737507032858958,
       3.6170450710342545,
       0.6397477566420586
      ],
      "receiver_position_std_m": 0.006,
      "receiver_pose_group_id": "receiver-pose-03",
      "candidates": [
       {
        "candidate_id": "capture-03:echo:00",
        "delay_s": 0.006701342347695795,
        "delay_std_s": 4.1666666666666665e-05,
        "amplitude": 0.37856778956024034
       },
       {
        "candidate_id": "capture-03:echo:01",
        "delay_s": 0.011914189168183086,
        "delay_std_s": 4.1666666666666665e-05,
        "amplitude": 0.19183123743037192
       }
      ],
      "clock": {
       "alpha": 0.9997917311506279,
       "alpha_std": 1.1248942649084144e-06
      },
      "direct_std_s": 4.1666666666666665e-05,
      "status": "ok"
     },
     {
      "capture_id": "capture-04",
      "receiver_position_m": [
       -1.6578127465714712,
       1.7224861066104302,
       0.9859871915932342
      ],
      "receiver_position_std_m": 0.006,
      "receiver_pose_group_id": "receiver-pose-04",
      "candidates": [
       {
        "candidate_id": "capture-04:echo:00",
        "delay_s": 0.007449733940121678,
        "delay_std_s": 4.1666666666666665e-05,
        "amplitude": 0.229467600628169
       }
      ],
      "clock": {
       "alpha": 1.0002216810310869,
       "alpha_std": 1.1248942649084144e-06
      },
      "direct_std_s": 4.1666666666666665e-05,
      "status": "ok"
     },
     {
      "capture_id": "capture-05",
      "receiver_position_m": [
       0.7566217813086723,
       1.9038885564621655,
       2.08855480367412
      ],
      "receiver_position_std_m": 0.006,
      "receiver_pose_group_id": "receiver-pose-05",
      "candidates": [
       {
        "candidate_id": "capture-05:echo:00",
        "delay_s": 0.002049757699666801,
        "delay_std_s": 4.1666666666666665e-05,
        "amplitude": 0.502878044053612
       }
      ],
      "clock": {
       "alpha": 0.99978662320283,
       "alpha_std": 1.1248942649084144e-06
      },
      "direct_std_s": 4.1666666666666665e-05,
      "status": "ok"
     },
     {
      "capture_id": "capture-06",
      "receiver_position_m": [
       0.5639505479530454,
       1.6183378718995025,
       1.7709115258515786
      ],
      "receiver_position_std_m": 0.006,
      "receiver_pose_group_id": "receiver-pose-06",
      "candidates": [
       {
        "candidate_id": "capture-06:echo:00",
        "delay_s": 0.0038215768019698574,
        "delay_std_s": 4.1666666666666665e-05,
        "amplitude": 0.38198084829081924
       }
      ],
      "clock": {
       "alpha": 1.0000625553446956,
       "alpha_std": 1.1248942649084144e-06
      },
      "direct_std_s": 4.1666666666666665e-05,
      "status": "ok"
     },
     {
      "capture_id": "capture-07",
      "receiver_position_m": [
       -1.3297304443562432,
       2.8218684105853358,
       0.9384998473377993
      ],
      "receiver_position_std_m": 0.006,
      "receiver_pose_group_id": "receiver-pose-07",
      "candidates": [
       {
        "candidate_id": "capture-07:echo:00",
        "delay_s": 0.006788274814039056,
        "delay_std_s": 4.1666666666666665e-05,
        "amplitude": 0.31901720863772115
       },
       {
        "candidate_id": "capture-07:echo:01",
        "delay_s": 0.011494023824551718,
        "delay_std_s": 4.1666666666666665e-05,
        "amplitude": 0.1584535850909211
       }
      ],
      "clock": {
       "alpha": 0.9998049537405996,
       "alpha_std": 1.1248942649084144e-06
      },
      "direct_std_s": 4.1666666666666665e-05,
      "status": "ok"
     },
     {
      "capture_id": "capture-08",
      "receiver_position_m": [
       -2.4295750269935374,
       2.696309754572328,
       0.06711956893777604
      ],
      "receiver_position_std_m": 0.006,
      "receiver_pose_group_id": "receiver-pose-08",
      "candidates": [
       {
        "candidate_id": "capture-08:echo:00",
        "delay_s": 0.008287459456412544,
        "delay_std_s": 4.1666666666666665e-05,
        "amplitude": 0.2904289544103961
       }
      ],
      "clock": {
       "alpha": 1.000221609105795,
       "alpha_std": 1.1248942649084144e-06
      },
      "direct_std_s": 4.1666666666666665e-05,
      "status": "ok"
     },
     {
      "capture_id": "capture-09",
      "receiver_position_m": [
       -1.1321620082574537,
       2.103783246650004,
       0.6031821071277661
      ],
      "receiver_position_std_m": 0.006,
      "receiver_pose_group_id": "receiver-pose-09",
      "candidates": [
       {
        "candidate_id": "capture-09:echo:00",
        "delay_s": 0.009320935952721788,
        "delay_std_s": 4.1666666666666665e-05,
        "amplitude": 0.17288859547721047
       },
       {
        "candidate_id": "capture-09:echo:01",
        "delay_s": 0.011584383406590492,
        "delay_std_s": 4.1666666666666665e-05,
        "amplitude": 0.09820120703652581
       }
      ],
      "clock": {
       "alpha": 1.0002487105115219,
       "alpha_std": 1.1248942649084144e-06
      },
      "direct_std_s": 4.1666666666666665e-05,
      "status": "ok"
     },
     {
      "capture_id": "capture-10",
      "receiver_position_m": [
       -1.6225591466580747,
       3.5386181421966616,
       0.0405879612259283
      ],
      "receiver_position_std_m": 0.006,
      "receiver_pose_group_id": "receiver-pose-10",
      "candidates": [
       {
        "candidate_id": "capture-10:echo:00",
        "delay_s": 0.008128933749855485,
        "delay_std_s": 4.1666666666666665e-05,
        "amplitude": 0.31923800826754883
       },
       {
        "candidate_id": "capture-10:echo:01",
        "delay_s": 0.011557331372634134,
        "delay_std_s": 4.1666666666666665e-05,
        "amplitude": 0.1849823121681283
       }
      ],
      "clock": {
       "alpha": 0.9999687324265726,
       "alpha_std": 1.1248942649084144e-06
      },
      "direct_std_s": 4.1666666666666665e-05,
      "status": "ok"
     },
     {
      "capture_id": "capture-11",
      "receiver_position_m": [
       0.09087829951602602,
       1.6720710238166085,
       1.4282962807626172
      ],
      "receiver_position_std_m": 0.006,
      "receiver_pose_group_id": "receiver-pose-11",
      "candidates": [
       {
        "candidate_id": "capture-11:echo:00",
        "delay_s": 0.005886513970223042,
        "delay_std_s": 4.1666666666666665e-05,
        "amplitude": 0.28233500934092876
       }
      ],
      "clock": {
       "alpha": 0.9997748279122086,
       "alpha_std": 1.1248942649084144e-06
      },
      "direct_std_s": 4.1666666666666665e-05,
      "status": "ok"
     }
    ]
   },
   {
    "session": {
     "session_id": "relocation-hidden_corner_four_sources-1003-source-01",
     "source_position_m": [
      -0.010690466427334948,
      1.8058326795345345,
      0.3387049325890533
     ],
     "coordinate_frame_id": "test-frame"
    },
    "observations": [
     {
      "capture_id": "capture-00",
      "receiver_position_m": [
       -1.021216344640526,
       3.2583296014536223,
       1.4728190422780376
      ],
      "receiver_position_std_m": 0.006,
      "receiver_pose_group_id": "receiver-pose-00",
      "candidates": [
       {
        "candidate_id": "capture-00:echo:00",
        "delay_s": 0.004581678336788486,
        "delay_std_s": 4.1666666666666665e-05,
        "amplitude": 0.37747913728520893
       },
       {
        "candidate_id": "capture-00:echo:01",
        "delay_s": 0.013451822669376827,
        "delay_std_s": 4.1666666666666665e-05,
        "amplitude": 0.12691938736700797
       }
      ],
      "clock": {
       "alpha": 1.0002088966653602,
       "alpha_std": 1.1248942649084144e-06
      },
      "direct_std_s": 4.1666666666666665e-05,
      "status": "ok"
     },
     {
      "capture_id": "capture-01",
      "receiver_position_m": [
       -1.3395350103286499,
       2.28426746056934,
       2.0939675115427914
      ],
      "receiver_position_std_m": 0.006,
      "receiver_pose_group_id": "receiver-pose-01",
      "candidates": [
       {
        "candidate_id": "capture-01:echo:00",
        "delay_s": 0.002064010341949893,
        "delay_std_s": 4.1666666666666665e-05,
        "amplitude": 0.5205196968938262
       },
       {
        "candidate_id": "capture-01:echo:01",
        "delay_s": 0.01065536363382437,
        "delay_std_s": 4.1666666666666665e-05,
        "amplitude": 0.18524274437055616
       }
      ],
      "clock": {
       "alpha": 0.999753638233019,
       "alpha_std": 1.1248942649084144e-06
      },
      "direct_std_s": 4.1666666666666665e-05,
      "status": "ok"
     },
     {
      "capture_id": "capture-03",
      "receiver_position_m": [
       -1.1737507032858958,
       3.6170450710342545,
       0.6397477566420586
      ],
      "receiver_position_std_m": 0.006,
      "receiver_pose_group_id": "receiver-pose-03",
      "candidates": [
       {
        "candidate_id": "capture-03:echo:00",
        "delay_s": 0.00703274889990103,
        "delay_std_s": 4.1666666666666665e-05,
        "amplitude": 0.3258975706192582
       },
       {
        "candidate_id": "capture-03:echo:01",
        "delay_s": 0.014006551641245132,
        "delay_std_s": 4.1666666666666665e-05,
        "amplitude": 0.136810980846019
       }
      ],
      "clock": {
       "alpha": 0.9998459915740558,
       "alpha_std": 1.1248942649084144e-06
      },
      "direct_std_s": 4.1666666666666665e-05,
      "status": "ok"
     },
     {
      "capture_id": "capture-04",
      "receiver_position_m": [
       -1.6578127465714712,
       1.7224861066104302,
       0.9859871915932342
      ],
      "receiver_position_std_m": 0.006,
      "receiver_pose_group_id": "receiver-pose-04",
      "candidates": [
       {
        "candidate_id": "capture-04:echo:00",
        "delay_s": 0.006656248467595437,
        "delay_std_s": 4.1666666666666665e-05,
        "amplitude": 0.27275144833995835
       }
      ],
      "clock": {
       "alpha": 0.9998815346055494,
       "alpha_std": 1.1248942649084144e-06
      },
      "direct_std_s": 4.1666666666666665e-05,
      "status": "ok"
     },
     {
      "capture_id": "capture-05",
      "receiver_position_m": [
       0.7566217813086723,
       1.9038885564621655,
       2.08855480367412
      ],
      "receiver_position_std_m": 0.006,
      "receiver_pose_group_id": "receiver-pose-05",
      "candidates": [
       {
        "candidate_id": "capture-05:echo:00",
        "delay_s": 0.002326021577031673,
        "delay_std_s": 4.1666666666666665e-05,
        "amplitude": 0.4541400114318008
       }
      ],
      "clock": {
       "alpha": 1.00020317628896,
       "alpha_std": 1.1248942649084144e-06
      },
      "direct_std_s": 4.1666666666666665e-05,
      "status": "ok"
     },
     {
      "capture_id": "capture-06",
      "receiver_position_m": [
       0.5639505479530454,
       1.6183378718995025,
       1.7709115258515786
      ],
      "receiver_position_std_m": 0.006,
      "receiver_pose_group_id": "receiver-pose-06",
      "candidates": [
       {
        "candidate_id": "capture-06:echo:00",
        "delay_s": 0.004222929977188892,
        "delay_std_s": 4.1666666666666665e-05,
        "amplitude": 0.3732244906155452
       }
      ],
      "clock": {
       "alpha": 0.999773543312687,
       "alpha_std": 1.1248942649084144e-06
      },
      "direct_std_s": 4.1666666666666665e-05,
      "status": "ok"
     },
     {
      "capture_id": "capture-07",
      "receiver_position_m": [
       -1.3297304443562432,
       2.8218684105853358,
       0.9384998473377993
      ],
      "receiver_position_std_m": 0.006,
      "receiver_pose_group_id": "receiver-pose-07",
      "candidates": [
       {
        "candidate_id": "capture-07:echo:00",
        "delay_s": 0.006829556376044889,
        "delay_std_s": 4.1666666666666665e-05,
        "amplitude": 0.30636823946720654
       },
       {
        "candidate_id": "capture-07:echo:01",
        "delay_s": 0.012962197397596202,
        "delay_std_s": 4.1666666666666665e-05,
        "amplitude": 0.12992334498272076
       }
      ],
      "clock": {
       "alpha": 0.9998758311854347,
       "alpha_std": 1.1248942649084144e-06
      },
      "direct_std_s": 4.1666666666666665e-05,
      "status": "ok"
     },
     {
      "capture_id": "capture-08",
      "receiver_position_m": [
       -2.4295750269935374,
       2.696309754572328,
       0.06711956893777604
      ],
      "receiver_position_std_m": 0.006,
      "receiver_pose_group_id": "receiver-pose-08",
      "candidates": [
       {
        "candidate_id": "capture-08:echo:00",
        "delay_s": 0.007878661803047885,
        "delay_std_s": 4.1666666666666665e-05,
        "amplitude": 0.33520006778388545
       }
      ],
      "clock": {
       "alpha": 1.0002273699097606,
       "alpha_std": 1.1248942649084144e-06
      },
      "direct_std_s": 4.1666666666666665e-05,
      "status": "ok"
     },
     {
      "capture_id": "capture-09",
      "receiver_position_m": [
       -1.1321620082574537,
       2.103783246650004,
       0.6031821071277661
      ],
      "receiver_position_std_m": 0.006,
      "receiver_pose_group_id": "receiver-pose-09",
      "candidates": [
       {
        "candidate_id": "capture-09:echo:00",
        "delay_s": 0.008917217707279882,
        "delay_std_s": 4.1666666666666665e-05,
        "amplitude": 0.19271776503953666
       },
       {
        "candidate_id": "capture-09:echo:01",
        "delay_s": 0.012496542991413612,
        "delay_std_s": 4.1666666666666665e-05,
        "amplitude": 0.10979412019413946
       }
      ],
      "clock": {
       "alpha": 0.9997580481107046,
       "alpha_std": 1.1248942649084144e-06
      },
      "direct_std_s": 4.1666666666666665e-05,
      "status": "ok"
     },
     {
      "capture_id": "capture-10",
      "receiver_position_m": [
       -1.6225591466580747,
       3.5386181421966616,
       0.0405879612259283
      ],
      "receiver_position_std_m": 0.006,
      "receiver_pose_group_id": "receiver-pose-10",
      "candidates": [
       {
        "candidate_id": "capture-10:echo:00",
        "delay_s": 0.00827283723160489,
        "delay_std_s": 4.1666666666666665e-05,
        "amplitude": 0.31831503389188964
       }
      ],
      "clock": {
       "alpha": 0.9998900407764176,
       "alpha_std": 1.1248942649084144e-06
      },
      "direct_std_s": 4.1666666666666665e-05,
      "status": "ok"
     },
     {
      "capture_id": "capture-11",
      "receiver_position_m": [
       0.09087829951602602,
       1.6720710238166085,
       1.4282962807626172
      ],
      "receiver_position_std_m": 0.006,
      "receiver_pose_group_id": "receiver-pose-11",
      "candidates": [
       {
        "candidate_id": "capture-11:echo:00",
        "delay_s": 0.006306942576328353,
        "delay_std_s": 4.1666666666666665e-05,
        "amplitude": 0.22030439550438718
       }
      ],
      "clock": {
       "alpha": 1.0000871667936357,
       "alpha_std": 1.1248942649084144e-06
      },
      "direct_std_s": 4.1666666666666665e-05,
      "status": "ok"
     }
    ]
   },
   {
    "session": {
     "session_id": "relocation-hidden_corner_four_sources-1003-source-02",
     "source_position_m": [
      -1.063937097976136,
      1.8816893934796273,
      0.3439300468451523
     ],
     "coordinate_frame_id": "test-frame"
    },
    "observations": [
     {
      "capture_id": "capture-00",
      "receiver_position_m": [
       -1.021216344640526,
       3.2583296014536223,
       1.4728190422780376
      ],
      "receiver_position_std_m": 0.006,
      "receiver_pose_group_id": "receiver-pose-00",
      "candidates": [
       {
        "candidate_id": "capture-00:echo:00",
        "delay_s": 0.0050096448421923815,
        "delay_std_s": 4.1666666666666665e-05,
        "amplitude": 0.33110923838723744
       },
       {
        "candidate_id": "capture-00:echo:01",
        "delay_s": 0.014617678350004704,
        "delay_std_s": 4.1666666666666665e-05,
        "amplitude": 0.13374041612437412
       }
      ],
      "clock": {
       "alpha": 0.9998498320481047,
       "alpha_std": 1.1248942649084144e-06
      },
      "direct_std_s": 4.1666666666666665e-05,
      "status": "ok"
     },
     {
      "capture_id": "capture-01",
      "receiver_position_m": [
       -1.3395350103286499,
       2.28426746056934,
       2.0939675115427914
      ],
      "receiver_position_std_m": 0.006,
      "receiver_pose_group_id": "receiver-pose-01",
      "candidates": [
       {
        "candidate_id": "capture-01:echo:00",
        "delay_s": 0.0024057812137392655,
        "delay_std_s": 4.1666666666666665e-05,
        "amplitude": 0.4914650178706016
       },
       {
        "candidate_id": "capture-01:echo:01",
        "delay_s": 0.012293846925575148,
        "delay_std_s": 4.1666666666666665e-05,
        "amplitude": 0.15161865261829954
       }
      ],
      "clock": {
       "alpha": 1.000246890255781,
       "alpha_std": 1.1248942649084144e-06
      },
      "direct_std_s": 4.1666666666666665e-05,
      "status": "ok"
     },
     {
      "capture_id": "capture-02",
      "receiver_position_m": [
       0.2553713673204093,
       1.943866596104725,
       0.012289491846311801
      ],
      "receiver_position_std_m": 0.006,
      "receiver_pose_group_id": "receiver-pose-02",
      "candidates": [
       {
        "candidate_id": "capture-02:echo:00",
        "delay_s": 0.010150569117570481,
        "delay_std_s": 4.1666666666666665e-05,
        "amplitude": 0.20418233337610944
       },
       {
        "candidate_id": "capture-02:echo:01",
        "delay_s": 0.011834300745274863,
        "delay_std_s": 4.1666666666666665e-05,
        "amplitude": 0.12689269288422872
       }
      ],
      "clock": {
       "alpha": 1.0001964943983639,
       "alpha_std": 1.1248942649084144e-06
      },
      "direct_std_s": 4.1666666666666665e-05,
      "status": "ok"
     },
     {
      "capture_id": "capture-03",
      "receiver_position_m": [
       -1.1737507032858958,
       3.6170450710342545,
       0.6397477566420586
      ],
      "receiver_position_std_m": 0.006,
      "receiver_pose_group_id": "receiver-pose-03",
      "candidates": [
       {
        "candidate_id": "capture-03:echo:00",
        "delay_s": 0.007703341516575503,
        "delay_std_s": 4.1666666666666665e-05,
        "amplitude": 0.2773089860570746
       },
       {
        "candidate_id": "capture-03:echo:01",
        "delay_s": 0.015503009027986295,
        "delay_std_s": 4.1666666666666665e-05,
        "amplitude": 0.11417231777940746
       }
      ],
      "clock": {
       "alpha": 0.9998221536648491,
       "alpha_std": 1.1248942649084144e-06
      },
      "direct_std_s": 4.1666666666666665e-05,
      "status": "ok"
     },
     {
      "capture_id": "capture-04",
      "receiver_position_m": [
       -1.6578127465714712,
       1.7224861066104302,
       0.9859871915932342
      ],
      "receiver_position_std_m": 0.006,
      "receiver_pose_group_id": "receiver-pose-04",
      "candidates": [
       {
        "candidate_id": "capture-04:echo:00",
        "delay_s": 0.008351842843663387,
        "delay_std_s": 4.1666666666666665e-05,
        "amplitude": 0.1642576063426077
       },
       {
        "candidate_id": "capture-04:echo:01",
        "delay_s": 0.012941691874475799,
        "delay_std_s": 4.1666666666666665e-05,
        "amplitude": 0.08125171217022925
       }
      ],
      "clock": {
       "alpha": 1.000063997659575,
       "alpha_std": 1.1248942649084144e-06
      },
      "direct_std_s": 4.1666666666666665e-05,
      "status": "ok"
     },
     {
      "capture_id": "capture-05",
      "receiver_position_m": [
       0.7566217813086723,
       1.9038885564621655,
       2.08855480367412
      ],
      "receiver_position_std_m": 0.006,
      "receiver_pose_group_id": "receiver-pose-05",
      "candidates": [
       {
        "candidate_id": "capture-05:echo:00",
        "delay_s": 0.0018861711674308696,
        "delay_std_s": 4.1666666666666665e-05,
        "amplitude": 0.5103766834574265
       },
       {
        "candidate_id": "capture-05:echo:01",
        "delay_s": 0.009323445294994513,
        "delay_std_s": 4.1666666666666665e-05,
        "amplitude": 0.19843059045996034
       }
      ],
      "clock": {
       "alpha": 1.000082519197097,
       "alpha_std": 1.1248942649084144e-06
      },
      "direct_std_s": 4.1666666666666665e-05,
      "status": "ok"
     },
     {
      "capture_id": "capture-06",
      "receiver_position_m": [
       0.5639505479530454,
       1.6183378718995025,
       1.7709115258515786
      ],
      "receiver_position_std_m": 0.006,
      "receiver_pose_group_id": "receiver-pose-06",
      "candidates": [
       {
        "candidate_id": "capture-06:echo:00",
        "delay_s": 0.0034510121741953455,
        "delay_std_s": 4.1666666666666665e-05,
        "amplitude": 0.4209858604567902
       },
       {
        "candidate_id": "capture-06:echo:01",
        "delay_s": 0.009202647539815579,
        "delay_std_s": 4.1666666666666665e-05,
        "amplitude": 0.1782197768698827
       }
      ],
      "clock": {
       "alpha": 1.0002165353443102,
       "alpha_std": 1.1248942649084144e-06
      },
      "direct_std_s": 4.1666666666666665e-05,
      "status": "ok"
     },
     {
      "capture_id": "capture-07",
      "receiver_position_m": [
       -1.3297304443562432,
       2.8218684105853358,
       0.9384998473377993
      ],
      "receiver_position_std_m": 0.006,
      "receiver_pose_group_id": "receiver-pose-07",
      "candidates": [
       {
        "candidate_id": "capture-07:echo:00",
        "delay_s": 0.007972590682424204,
        "delay_std_s": 4.1666666666666665e-05,
        "amplitude": 0.20179236570552603
       },
       {
        "candidate_id": "capture-07:echo:01",
        "delay_s": 0.015142672349440849,
        "delay_std_s": 4.1666666666666665e-05,
        "amplitude": 0.09002906210368575
       }
      ],
      "clock": {
       "alpha": 0.9998801868447112,
       "alpha_std": 1.1248942649084144e-06
      },
      "direct_std_s": 4.1666666666666665e-05,
      "status": "ok"
     },
     {
      "capture_id": "capture-08",
      "receiver_position_m": [
       -2.4295750269935374,
       2.696309754572328,
       0.06711956893777604
      ],
      "receiver_position_std_m": 0.006,
      "receiver_pose_group_id": "receiver-pose-08",
      "candidates": [
       {
        "candidate_id": "capture-08:echo:00",
        "delay_s": 0.009561353011533914,
        "delay_std_s": 4.1666666666666665e-05,
        "amplitude": 0.2313030085239076
       },
       {
        "candidate_id": "capture-08:echo:01",
        "delay_s": 0.014079573395664291,
        "delay_std_s": 4.1666666666666665e-05,
        "amplitude": 0.12326395802084794
       }
      ],
      "clock": {
       "alpha": 0.9998934628416548,
       "alpha_std": 1.1248942649084144e-06
      },
      "direct_std_s": 4.1666666666666665e-05,
      "status": "ok"
     },
     {
      "capture_id": "capture-10",
      "receiver_position_m": [
       -1.6225591466580747,
       3.5386181421966616,
       0.0405879612259283
      ],
      "receiver_position_std_m": 0.006,
      "receiver_pose_group_id": "receiver-pose-10",
      "candidates": [
       {
        "candidate_id": "capture-10:echo:00",
        "delay_s": 0.009323930394537393,
        "delay_std_s": 4.1666666666666665e-05,
        "amplitude": 0.2336271947644959
       },
       {
        "candidate_id": "capture-10:echo:01",
        "delay_s": 0.015426025758590357,
        "delay_std_s": 4.1666666666666665e-05,
        "amplitude": 0.11628496214032069
       }
      ],
      "clock": {
       "alpha": 1.000242638120538,
       "alpha_std": 1.1248942649084144e-06
      },
      "direct_std_s": 4.1666666666666665e-05,
      "status": "ok"
     },
     {
      "capture_id": "capture-11",
      "receiver_position_m": [
       0.09087829951602602,
       1.6720710238166085,
       1.4282962807626172
      ],
      "receiver_position_std_m": 0.006,
      "receiver_pose_group_id": "receiver-pose-11",
      "candidates": [
       {
        "candidate_id": "capture-11:echo:00",
        "delay_s": 0.00541788199415439,
        "delay_std_s": 4.1666666666666665e-05,
        "amplitude": 0.32394734374284473
       },
       {
        "candidate_id": "capture-11:echo:01",
        "delay_s": 0.010562252059066718,
        "delay_std_s": 4.1666666666666665e-05,
        "amplitude": 0.15077960080868386
       }
      ],
      "clock": {
       "alpha": 1.0001058530522162,
       "alpha_std": 1.1248942649084144e-06
      },
      "direct_std_s": 4.1666666666666665e-05,
      "status": "ok"
     }
    ]
   },
   {
    "session": {
     "session_id": "relocation-hidden_corner_four_sources-1003-source-03",
     "source_position_m": [
      -0.5998043873611618,
      1.5599228361353603,
      0.9369995665007834
     ],
     "coordinate_frame_id": "test-frame"
    },
    "observations": [
     {
      "capture_id": "capture-00",
      "receiver_position_m": [
       -1.021216344640526,
       3.2583296014536223,
       1.4728190422780376
      ],
      "receiver_position_std_m": 0.006,
      "receiver_pose_group_id": "receiver-pose-00",
      "candidates": [
       {
        "candidate_id": "capture-00:echo:00",
        "delay_s": 0.003855675013525182,
        "delay_std_s": 4.1666666666666665e-05,
        "amplitude": 0.40089862919642
       },
       {
        "candidate_id": "capture-00:echo:01",
        "delay_s": 0.013291045782001657,
        "delay_std_s": 4.1666666666666665e-05,
        "amplitude": 0.13788848885712102
       }
      ],
      "clock": {
       "alpha": 0.999970454494769,
       "alpha_std": 1.1248942649084144e-06
      },
      "direct_std_s": 4.1666666666666665e-05,
      "status": "ok"
     },
     {
      "capture_id": "capture-01",
      "receiver_position_m": [
       -1.3395350103286499,
       2.28426746056934,
       2.0939675115427914
      ],
      "receiver_position_std_m": 0.006,
      "receiver_pose_group_id": "receiver-pose-01",
      "candidates": [
       {
        "candidate_id": "capture-01:echo:00",
        "delay_s": 0.0020480716793148234,
        "delay_std_s": 4.1666666666666665e-05,
        "amplitude": 0.48566062465949905
       },
       {
        "candidate_id": "capture-01:echo:01",
        "delay_s": 0.011605884617127018,
        "delay_std_s": 4.1666666666666665e-05,
        "amplitude": 0.14470286642089988
       }
      ],
      "clock": {
       "alpha": 1.0001552449946387,
       "alpha_std": 1.1248942649084144e-06
      },
      "direct_std_s": 4.1666666666666665e-05,
      "status": "ok"
     },
     {
      "capture_id": "capture-02",
      "receiver_position_m": [
       0.2553713673204093,
       1.943866596104725,
       0.012289491846311801
      ],
      "receiver_position_std_m": 0.006,
      "receiver_pose_group_id": "receiver-pose-02",
      "candidates": [
       {
        "candidate_id": "capture-02:echo:00",
        "delay_s": 0.008331411497131638,
        "delay_std_s": 4.1666666666666665e-05,
        "amplitude": 0.21984596617129964
       }
      ],
      "clock": {
       "alpha": 1.0000421961520811,
       "alpha_std": 1.1248942649084144e-06
      },
      "direct_std_s": 4.1666666666666665e-05,
      "status": "ok"
     },
     {
      "capture_id": "capture-03",
      "receiver_position_m": [
       -1.1737507032858958,
       3.6170450710342545,
       0.6397477566420586
      ],
      "receiver_position_std_m": 0.006,
      "receiver_pose_group_id": "receiver-pose-03",
      "candidates": [
       {
        "candidate_id": "capture-03:echo:00",
        "delay_s": 0.0055429377430512294,
        "delay_std_s": 4.1666666666666665e-05,
        "amplitude": 0.36192536313897505
       },
       {
        "candidate_id": "capture-03:echo:01",
        "delay_s": 0.013350048320487294,
        "delay_std_s": 4.1666666666666665e-05,
        "amplitude": 0.1632461183616834
       }
      ],
      "clock": {
       "alpha": 0.999756213649422,
       "alpha_std": 1.1248942649084144e-06
      },
      "direct_std_s": 4.1666666666666665e-05,
      "status": "ok"
     },
     {
      "capture_id": "capture-04",
      "receiver_position_m": [
       -1.6578127465714712,
       1.7224861066104302,
       0.9859871915932342
      ],
      "receiver_position_std_m": 0.006,
      "receiver_pose_group_id": "receiver-pose-04",
      "candidates": [
       {
        "candidate_id": "capture-04:echo:00",
        "delay_s": 0.006440428932707375,
        "delay_std_s": 4.1666666666666665e-05,
        "amplitude": 0.21748382679891196
       }
      ],
      "clock": {
       "alpha": 0.9998037944136463,
       "alpha_std": 1.1248942649084144e-06
      },
      "direct_std_s": 4.1666666666666665e-05,
      "status": "ok"
     },
     {
      "capture_id": "capture-05",
      "receiver_position_m": [
       0.7566217813086723,
       1.9038885564621655,
       2.08855480367412
      ],
      "receiver_position_std_m": 0.006,
      "receiver_pose_group_id": "receiver-pose-05",
      "candidates": [
       {
        "candidate_id": "capture-05:echo:00",
        "delay_s": 0.0018375126917358434,
        "delay_std_s": 4.1666666666666665e-05,
        "amplitude": 0.531293035244046
       }
      ],
      "clock": {
       "alpha": 1.0002009202178577,
       "alpha_std": 1.1248942649084144e-06
      },
      "direct_std_s": 4.1666666666666665e-05,
      "status": "ok"
     },
     {
      "capture_id": "capture-06",
      "receiver_position_m": [
       0.5639505479530454,
       1.6183378718995025,
       1.7709115258515786
      ],
      "receiver_position_std_m": 0.006,
      "receiver_pose_group_id": "receiver-pose-06",
      "candidates": [
       {
        "candidate_id": "capture-06:echo:00",
        "delay_s": 0.0034420583769926125,
        "delay_std_s": 4.1666666666666665e-05,
        "amplitude": 0.40066191142007723
       }
      ],
      "clock": {
       "alpha": 1.0002404687991067,
       "alpha_std": 1.1248942649084144e-06
      },
      "direct_std_s": 4.1666666666666665e-05,
      "status": "ok"
     },
     {
      "capture_id": "capture-07",
      "receiver_position_m": [
       -1.3297304443562432,
       2.8218684105853358,
       0.9384998473377993
      ],
      "receiver_position_std_m": 0.006,
      "receiver_pose_group_id": "receiver-pose-07",
      "candidates": [
       {
        "candidate_id": "capture-07:echo:00",
        "delay_s": 0.005881316047123165,
        "delay_std_s": 4.1666666666666665e-05,
        "amplitude": 0.2755867771175001
       },
       {
        "candidate_id": "capture-07:echo:01",
        "delay_s": 0.013092450790906157,
        "delay_std_s": 4.1666666666666665e-05,
        "amplitude": 0.10661597717172427
       }
      ],
      "clock": {
       "alpha": 1.0000089595041204,
       "alpha_std": 1.1248942649084144e-06
      },
      "direct_std_s": 4.1666666666666665e-05,
      "status": "ok"
     },
     {
      "capture_id": "capture-08",
      "receiver_position_m": [
       -2.4295750269935374,
       2.696309754572328,
       0.06711956893777604
      ],
      "receiver_position_std_m": 0.006,
      "receiver_pose_group_id": "receiver-pose-08",
      "candidates": [
       {
        "candidate_id": "capture-08:echo:00",
        "delay_s": 0.006527018375868406,
        "delay_std_s": 4.1666666666666665e-05,
        "amplitude": 0.3426062928896743
       }
      ],
      "clock": {
       "alpha": 1.0000342142349024,
       "alpha_std": 1.1248942649084144e-06
      },
      "direct_std_s": 4.1666666666666665e-05,
      "status": "ok"
     },
     {
      "capture_id": "capture-09",
      "receiver_position_m": [
       -1.1321620082574537,
       2.103783246650004,
       0.6031821071277661
      ],
      "receiver_position_std_m": 0.006,
      "receiver_pose_group_id": "receiver-pose-09",
      "candidates": [
       {
        "candidate_id": "capture-09:echo:00",
        "delay_s": 0.007974170769670675,
        "delay_std_s": 4.1666666666666665e-05,
        "amplitude": 0.15694679872720463
       },
       {
        "candidate_id": "capture-09:echo:01",
        "delay_s": 0.01281128148365436,
        "delay_std_s": 4.1666666666666665e-05,
        "amplitude": 0.07679820303998572
       }
      ],
      "clock": {
       "alpha": 0.9999609713309789,
       "alpha_std": 1.1248942649084144e-06
      },
      "direct_std_s": 4.1666666666666665e-05,
      "status": "ok"
     },
     {
      "capture_id": "capture-10",
      "receiver_position_m": [
       -1.6225591466580747,
       3.5386181421966616,
       0.0405879612259283
      ],
      "receiver_position_std_m": 0.006,
      "receiver_pose_group_id": "receiver-pose-10",
      "candidates": [
       {
        "candidate_id": "capture-10:echo:00",
        "delay_s": 0.006481637560050788,
        "delay_std_s": 4.1666666666666665e-05,
        "amplitude": 0.34819532205643783
       },
       {
        "candidate_id": "capture-10:echo:01",
        "delay_s": 0.012653394437657218,
        "delay_std_s": 4.1666666666666665e-05,
        "amplitude": 0.15446982405013435
       }
      ],
      "clock": {
       "alpha": 0.99986874137621,
       "alpha_std": 1.1248942649084144e-06
      },
      "direct_std_s": 4.1666666666666665e-05,
      "status": "ok"
     },
     {
      "capture_id": "capture-11",
      "receiver_position_m": [
       0.09087829951602602,
       1.6720710238166085,
       1.4282962807626172
      ],
      "receiver_position_std_m": 0.006,
      "receiver_pose_group_id": "receiver-pose-11",
      "candidates": [
       {
        "candidate_id": "capture-11:echo:00",
        "delay_s": 0.005523386780234979,
        "delay_std_s": 4.1666666666666665e-05,
        "amplitude": 0.21547459846026107
       }
      ],
      "clock": {
       "alpha": 1.000052071662556,
       "alpha_std": 1.1248942649084144e-06
      },
      "direct_std_s": 4.1666666666666665e-05,
      "status": "ok"
     }
    ]
   }
  ],
  "surfaces": [
   {
    "surface_id": "reflector-49169db0ed6d7311",
    "normal": [
     -0.0008352015194524088,
     -0.00199240281965377,
     0.9999976663819902
    ],
    "offset_m": 2.511973442685313,
    "support": [
     {
      "session_id": "relocation-hidden_corner_four_sources-1003-source-00",
      "capture_id": "capture-00",
      "candidate_id": "capture-00:echo:00"
     },
     {
      "session_id": "relocation-hidden_corner_four_sources-1003-source-00",
      "capture_id": "capture-01",
      "candidate_id": "capture-01:echo:00"
     },
     {
      "session_id": "relocation-hidden_corner_four_sources-1003-source-00",
      "capture_id": "capture-02",
      "candidate_id": "capture-02:echo:00"
     },
     {
      "session_id": "relocation-hidden_corner_four_sources-1003-source-00",
      "capture_id": "capture-03",
      "candidate_id": "capture-03:echo:00"
     },
     {
      "session_id": "relocation-hidden_corner_four_sources-1003-source-00",
      "capture_id": "capture-04",
      "candidate_id": "capture-04:echo:00"
     },
     {
      "session_id": "relocation-hidden_corner_four_sources-1003-source-00",
      "capture_id": "capture-05",
      "candidate_id": "capture-05:echo:00"
     },
     {
      "session_id": "relocation-hidden_corner_four_sources-1003-source-00",
      "capture_id": "capture-06",
      "candidate_id": "capture-06:echo:00"
     },
     {
      "session_id": "relocation-hidden_corner_four_sources-1003-source-00",
      "capture_id": "capture-07",
      "candidate_id": "capture-07:echo:00"
     },
     {
      "session_id": "relocation-hidden_corner_four_sources-1003-source-00",
      "capture_id": "capture-08",
      "candidate_id": "capture-08:echo:00"
     },
     {
      "session_id": "relocation-hidden_corner_four_sources-1003-source-00",
      "capture_id": "capture-09",
      "candidate_id": "capture-09:echo:00"
     },
     {
      "session_id": "relocation-hidden_corner_four_sources-1003-source-00",
      "capture_id": "capture-10",
      "candidate_id": "capture-10:echo:00"
     },
     {
      "session_id": "relocation-hidden_corner_four_sources-1003-source-00",
      "capture_id": "capture-11",
      "candidate_id": "capture-11:echo:00"
     },
     {
      "session_id": "relocation-hidden_corner_four_sources-1003-source-01",
      "capture_id": "capture-00",
      "candidate_id": "capture-00:echo:00"
     },
     {
      "session_id": "relocation-hidden_corner_four_sources-1003-source-01",
      "capture_id": "capture-01",
      "candidate_id": "capture-01:echo:00"
     },
     {
      "session_id": "relocation-hidden_corner_four_sources-1003-source-01",
      "capture_id": "capture-03",
      "candidate_id": "capture-03:echo:00"
     },
     {
      "session_id": "relocation-hidden_corner_four_sources-1003-source-01",
      "capture_id": "capture-04",
      "candidate_id": "capture-04:echo:00"
     },
     {
      "session_id": "relocation-hidden_corner_four_sources-1003-source-01",
      "capture_id": "capture-05",
      "candidate_id": "capture-05:echo:00"
     },
     {
      "session_id": "relocation-hidden_corner_four_sources-1003-source-01",
      "capture_id": "capture-06",
      "candidate_id": "capture-06:echo:00"
     },
     {
      "session_id": "relocation-hidden_corner_four_sources-1003-source-01",
      "capture_id": "capture-07",
      "candidate_id": "capture-07:echo:00"
     },
     {
      "session_id": "relocation-hidden_corner_four_sources-1003-source-01",
      "capture_id": "capture-08",
      "candidate_id": "capture-08:echo:00"
     },
     {
      "session_id": "relocation-hidden_corner_four_sources-1003-source-01",
      "capture_id": "capture-09",
      "candidate_id": "capture-09:echo:00"
     },
     {
      "session_id": "relocation-hidden_corner_four_sources-1003-source-01",
      "capture_id": "capture-10",
      "candidate_id": "capture-10:echo:00"
     },
     {
      "session_id": "relocation-hidden_corner_four_sources-1003-source-01",
      "capture_id": "capture-11",
      "candidate_id": "capture-11:echo:00"
     },
     {
      "session_id": "relocation-hidden_corner_four_sources-1003-source-02",
      "capture_id": "capture-00",
      "candidate_id": "capture-00:echo:00"
     },
     {
      "session_id": "relocation-hidden_corner_four_sources-1003-source-02",
      "capture_id": "capture-01",
      "candidate_id": "capture-01:echo:00"
     },
     {
      "session_id": "relocation-hidden_corner_four_sources-1003-source-02",
      "capture_id": "capture-02",
      "candidate_id": "capture-02:echo:00"
     },
     {
      "session_id": "relocation-hidden_corner_four_sources-1003-source-02",
      "capture_id": "capture-03",
      "candidate_id": "capture-03:echo:00"
     },
     {
      "session_id": "relocation-hidden_corner_four_sources-1003-source-02",
      "capture_id": "capture-04",
      "candidate_id": "capture-04:echo:00"
     },
     {
      "session_id": "relocation-hidden_corner_four_sources-1003-source-02",
      "capture_id": "capture-05",
      "candidate_id": "capture-05:echo:00"
     },
     {
      "session_id": "relocation-hidden_corner_four_sources-1003-source-02",
      "capture_id": "capture-06",
      "candidate_id": "capture-06:echo:00"
     },
     {
      "session_id": "relocation-hidden_corner_four_sources-1003-source-02",
      "capture_id": "capture-07",
      "candidate_id": "capture-07:echo:00"
     },
     {
      "session_id": "relocation-hidden_corner_four_sources-1003-source-02",
      "capture_id": "capture-08",
      "candidate_id": "capture-08:echo:00"
     },
     {
      "session_id": "relocation-hidden_corner_four_sources-1003-source-02",
      "capture_id": "capture-10",
      "candidate_id": "capture-10:echo:00"
     },
     {
      "session_id": "relocation-hidden_corner_four_sources-1003-source-02",
      "capture_id": "capture-11",
      "candidate_id": "capture-11:echo:00"
     },
     {
      "session_id": "relocation-hidden_corner_four_sources-1003-source-03",
      "capture_id": "capture-00",
      "candidate_id": "capture-00:echo:00"
     },
     {
      "session_id": "relocation-hidden_corner_four_sources-1003-source-03",
      "capture_id": "capture-01",
      "candidate_id": "capture-01:echo:00"
     },
     {
      "session_id": "relocation-hidden_corner_four_sources-1003-source-03",
      "capture_id": "capture-02",
      "candidate_id": "capture-02:echo:00"
     },
     {
      "session_id": "relocation-hidden_corner_four_sources-1003-source-03",
      "capture_id": "capture-03",
      "candidate_id": "capture-03:echo:00"
     },
     {
      "session_id": "relocation-hidden_corner_four_sources-1003-source-03",
      "capture_id": "capture-04",
      "candidate_id": "capture-04:echo:00"
     },
     {
      "session_id": "relocation-hidden_corner_four_sources-1003-source-03",
      "capture_id": "capture-05",
      "candidate_id": "capture-05:echo:00"
     },
     {
      "session_id": "relocation-hidden_corner_four_sources-1003-source-03",
      "capture_id": "capture-06",
      "candidate_id": "capture-06:echo:00"
     },
     {
      "session_id": "relocation-hidden_corner_four_sources-1003-source-03",
      "capture_id": "capture-07",
      "candidate_id": "capture-07:echo:00"
     },
     {
      "session_id": "relocation-hidden_corner_four_sources-1003-source-03",
      "capture_id": "capture-08",
      "candidate_id": "capture-08:echo:00"
     },
     {
      "session_id": "relocation-hidden_corner_four_sources-1003-source-03",
      "capture_id": "capture-09",
      "candidate_id": "capture-09:echo:00"
     },
     {
      "session_id": "relocation-hidden_corner_four_sources-1003-source-03",
      "capture_id": "capture-10",
      "candidate_id": "capture-10:echo:00"
     },
     {
      "session_id": "relocation-hidden_corner_four_sources-1003-source-03",
      "capture_id": "capture-11",
      "candidate_id": "capture-11:echo:00"
     }
    ]
   },
   {
    "surface_id": "reflector-03025438ea379070",
    "normal": [
     -0.11129705580686883,
     0.9937669744845519,
     -0.006337648818220824
    ],
    "offset_m": -0.683119689518738,
    "support": [
     {
      "session_id": "relocation-hidden_corner_four_sources-1003-source-00",
      "capture_id": "capture-00",
      "candidate_id": "capture-00:echo:01"
     },
     {
      "session_id": "relocation-hidden_corner_four_sources-1003-source-00",
      "capture_id": "capture-01",
      "candidate_id": "capture-01:echo:01"
     },
     {
      "session_id": "relocation-hidden_corner_four_sources-1003-source-00",
      "capture_id": "capture-03",
      "candidate_id": "capture-03:echo:01"
     },
     {
      "session_id": "relocation-hidden_corner_four_sources-1003-source-00",
      "capture_id": "capture-07",
      "candidate_id": "capture-07:echo:01"
     },
     {
      "session_id": "relocation-hidden_corner_four_sources-1003-source-00",
      "capture_id": "capture-09",
      "candidate_id": "capture-09:echo:01"
     },
     {
      "session_id": "relocation-hidden_corner_four_sources-1003-source-00",
      "capture_id": "capture-10",
      "candidate_id": "capture-10:echo:01"
     },
     {
      "session_id": "relocation-hidden_corner_four_sources-1003-source-01",
      "capture_id": "capture-00",
      "candidate_id": "capture-00:echo:01"
     },
     {
      "session_id": "relocation-hidden_corner_four_sources-1003-source-01",
      "capture_id": "capture-01",
      "candidate_id": "capture-01:echo:01"
     },
     {
      "session_id": "relocation-hidden_corner_four_sources-1003-source-01",
      "capture_id": "capture-03",
      "candidate_id": "capture-03:echo:01"
     },
     {
      "session_id": "relocation-hidden_corner_four_sources-1003-source-01",
      "capture_id": "capture-07",
      "candidate_id": "capture-07:echo:01"
     },
     {
      "session_id": "relocation-hidden_corner_four_sources-1003-source-01",
      "capture_id": "capture-09",
      "candidate_id": "capture-09:echo:01"
     },
     {
      "session_id": "relocation-hidden_corner_four_sources-1003-source-02",
      "capture_id": "capture-00",
      "candidate_id": "capture-00:echo:01"
     },
     {
      "session_id": "relocation-hidden_corner_four_sources-1003-source-02",
      "capture_id": "capture-01",
      "candidate_id": "capture-01:echo:01"
     },
     {
      "session_id": "relocation-hidden_corner_four_sources-1003-source-02",
      "capture_id": "capture-02",
      "candidate_id": "capture-02:echo:01"
     },
     {
      "session_id": "relocation-hidden_corner_four_sources-1003-source-02",
      "capture_id": "capture-03",
      "candidate_id": "capture-03:echo:01"
     },
     {
      "session_id": "relocation-hidden_corner_four_sources-1003-source-02",
      "capture_id": "capture-04",
      "candidate_id": "capture-04:echo:01"
     },
     {
      "session_id": "relocation-hidden_corner_four_sources-1003-source-02",
      "capture_id": "capture-05",
      "candidate_id": "capture-05:echo:01"
     },
     {
      "session_id": "relocation-hidden_corner_four_sources-1003-source-02",
      "capture_id": "capture-06",
      "candidate_id": "capture-06:echo:01"
     },
     {
      "session_id": "relocation-hidden_corner_four_sources-1003-source-02",
      "capture_id": "capture-07",
      "candidate_id": "capture-07:echo:01"
     },
     {
      "session_id": "relocation-hidden_corner_four_sources-1003-source-02",
      "capture_id": "capture-08",
      "candidate_id": "capture-08:echo:01"
     },
     {
      "session_id": "relocation-hidden_corner_four_sources-1003-source-02",
      "capture_id": "capture-10",
      "candidate_id": "capture-10:echo:01"
     },
     {
      "session_id": "relocation-hidden_corner_four_sources-1003-source-02",
      "capture_id": "capture-11",
      "candidate_id": "capture-11:echo:01"
     },
     {
      "session_id": "relocation-hidden_corner_four_sources-1003-source-03",
      "capture_id": "capture-00",
      "candidate_id": "capture-00:echo:01"
     },
     {
      "session_id": "relocation-hidden_corner_four_sources-1003-source-03",
      "capture_id": "capture-01",
      "candidate_id": "capture-01:echo:01"
     },
     {
      "session_id": "relocation-hidden_corner_four_sources-1003-source-03",
      "capture_id": "capture-03",
      "candidate_id": "capture-03:echo:01"
     },
     {
      "session_id": "relocation-hidden_corner_four_sources-1003-source-03",
      "capture_id": "capture-07",
      "candidate_id": "capture-07:echo:01"
     },
     {
      "session_id": "relocation-hidden_corner_four_sources-1003-source-03",
      "capture_id": "capture-09",
      "candidate_id": "capture-09:echo:01"
     },
     {
      "session_id": "relocation-hidden_corner_four_sources-1003-source-03",
      "capture_id": "capture-10",
      "candidate_id": "capture-10:echo:01"
     }
    ]
   }
  ]
 },
 "finite_panel_four_sources-1003": {
  "bundle": {
   "shared_calibration": {
    "effective_speed_m_s": 343.0,
    "effective_speed_std_m_s": 0.6,
    "covariance_assumption": "explicit_source_pose_covariance_independent_speed",
    "source_pose_joint_covariance_m2": [
     [
      2.4999999999999998e-05,
      0.0,
      0.0,
      9e-06,
      0.0,
      0.0,
      9e-06,
      0.0,
      0.0,
      9e-06,
      0.0,
      0.0
     ],
     [
      0.0,
      2.4999999999999998e-05,
      0.0,
      0.0,
      9e-06,
      0.0,
      0.0,
      9e-06,
      0.0,
      0.0,
      9e-06,
      0.0
     ],
     [
      0.0,
      0.0,
      2.4999999999999998e-05,
      0.0,
      0.0,
      9e-06,
      0.0,
      0.0,
      9e-06,
      0.0,
      0.0,
      9e-06
     ],
     [
      9e-06,
      0.0,
      0.0,
      2.4999999999999998e-05,
      0.0,
      0.0,
      9e-06,
      0.0,
      0.0,
      9e-06,
      0.0,
      0.0
     ],
     [
      0.0,
      9e-06,
      0.0,
      0.0,
      2.4999999999999998e-05,
      0.0,
      0.0,
      9e-06,
      0.0,
      0.0,
      9e-06,
      0.0
     ],
     [
      0.0,
      0.0,
      9e-06,
      0.0,
      0.0,
      2.4999999999999998e-05,
      0.0,
      0.0,
      9e-06,
      0.0,
      0.0,
      9e-06
     ],
     [
      9e-06,
      0.0,
      0.0,
      9e-06,
      0.0,
      0.0,
      2.4999999999999998e-05,
      0.0,
      0.0,
      9e-06,
      0.0,
      0.0
     ],
     [
      0.0,
      9e-06,
      0.0,
      0.0,
      9e-06,
      0.0,
      0.0,
      2.4999999999999998e-05,
      0.0,
      0.0,
      9e-06,
      0.0
     ],
     [
      0.0,
      0.0,
      9e-06,
      0.0,
      0.0,
      9e-06,
      0.0,
      0.0,
      2.4999999999999998e-05,
      0.0,
      0.0,
      9e-06
     ],
     [
      9e-06,
      0.0,
      0.0,
      9e-06,
      0.0,
      0.0,
      9e-06,
      0.0,
      0.0,
      2.4999999999999998e-05,
      0.0,
      0.0
     ],
     [
      0.0,
      9e-06,
      0.0,
      0.0,
      9e-06,
      0.0,
      0.0,
      9e-06,
      0.0,
      0.0,
      2.4999999999999998e-05,
      0.0
     ],
     [
      0.0,
      0.0,
      9e-06,
      0.0,
      0.0,
      9e-06,
      0.0,
      0.0,
      9e-06,
      0.0,
      0.0,
      2.4999999999999998e-05
     ]
    ]
   },
   "schema_version": "1.0",
   "scene_id": "compact-development",
   "coordinate_frame_id": "test-frame",
   "scene_static": true
  },
  "processed_sessions": [
   {
    "session": {
     "session_id": "relocation-finite_panel_four_sources-1003-source-00",
     "source_position_m": [
      -0.5838621455383515,
      1.3100239529940036,
      0.3387816039546151
     ],
     "coordinate_frame_id": "test-frame"
    },
    "observations": [
     {
      "capture_id": "capture-00",
      "receiver_position_m": [
       -1.021216344640526,
       3.2583296014536223,
       1.4728190422780376
      ],
      "receiver_position_std_m": 0.006,
      "receiver_pose_group_id": "receiver-pose-00",
      "candidates": [
       {
        "candidate_id": "capture-00:echo:00",
        "delay_s": 0.004355025028827456,
        "delay_std_s": 4.1666666666666665e-05,
        "amplitude": 0.39101642472871007
       },
       {
        "candidate_id": "capture-00:echo:01",
        "delay_s": 0.006331964375606596,
        "delay_std_s": 4.1666666666666665e-05,
        "amplitude": 0.3631177615969521
       },
       {
        "candidate_id": "capture-00:echo:02",
        "delay_s": 0.007598378265383675,
        "delay_std_s": 4.1666666666666665e-05,
        "amplitude": 0.3350645217191058
       },
       {
        "candidate_id": "capture-00:echo:03",
        "delay_s": 0.00915949148027599,
        "delay_std_s": 4.1666666666666665e-05,
        "amplitude": 0.25753941918821355
       },
       {
        "candidate_id": "capture-00:echo:04",
        "delay_s": 0.014097590825011212,
        "delay_std_s": 4.1666666666666665e-05,
        "amplitude": 0.22139191575759845
       }
      ],
      "clock": {
       "alpha": 0.999880209435173,
       "alpha_std": 1.1248942649084144e-06
      },
      "direct_std_s": 4.1666666666666665e-05,
      "status": "ok"
     },
     {
      "capture_id": "capture-01",
      "receiver_position_m": [
       -1.3395350103286499,
       2.28426746056934,
       2.0939675115427914
      ],
      "receiver_position_std_m": 0.006,
      "receiver_pose_group_id": "receiver-pose-01",
      "candidates": [
       {
        "candidate_id": "capture-01:echo:00",
        "delay_s": 0.002141508255175567,
        "delay_std_s": 4.1666666666666665e-05,
        "amplitude": 0.5121624912828309
       },
       {
        "candidate_id": "capture-01:echo:01",
        "delay_s": 0.004678309487343102,
        "delay_std_s": 4.1666666666666665e-05,
        "amplitude": 0.36104803268192653
       },
       {
        "candidate_id": "capture-01:echo:02",
        "delay_s": 0.005396363750612759,
        "delay_std_s": 4.1666666666666665e-05,
        "amplitude": 0.3685196500629005
       },
       {
        "candidate_id": "capture-01:echo:03",
        "delay_s": 0.00686966327610687,
        "delay_std_s": 4.1666666666666665e-05,
        "amplitude": 0.3207280448203458
       },
       {
        "candidate_id": "capture-01:echo:04",
        "delay_s": 0.009932901050468235,
        "delay_std_s": 4.1666666666666665e-05,
        "amplitude": 0.2606388208935375
       },
       {
        "candidate_id": "capture-01:echo:05",
        "delay_s": 0.011983468021269924,
        "delay_std_s": 4.1666666666666665e-05,
        "amplitude": 0.19765209249964125
       },
       {
        "candidate_id": "capture-01:echo:06",
        "delay_s": 0.016980019530019295,
        "delay_std_s": 4.1666666666666665e-05,
        "amplitude": 0.18129302231521438
       }
      ],
      "clock": {
       "alpha": 0.9999337007284163,
       "alpha_std": 1.1248942649084144e-06
      },
      "direct_std_s": 4.1666666666666665e-05,
      "status": "ok"
     },
     {
      "capture_id": "capture-02",
      "receiver_position_m": [
       0.2553713673204093,
       1.943866596104725,
       0.012289491846311801
      ],
      "receiver_position_std_m": 0.006,
      "receiver_pose_group_id": "receiver-pose-02",
      "candidates": [
       {
        "candidate_id": "capture-02:echo:00",
        "delay_s": 0.0026756454280040904,
        "delay_std_s": 4.1666666666666665e-05,
        "amplitude": 0.34131996962049393
       },
       {
        "candidate_id": "capture-02:echo:01",
        "delay_s": 0.005675396466310533,
        "delay_std_s": 4.1666666666666665e-05,
        "amplitude": 0.22726060619490987
       },
       {
        "candidate_id": "capture-02:echo:02",
        "delay_s": 0.008660550339904916,
        "delay_std_s": 4.1666666666666665e-05,
        "amplitude": 0.1768515928394674
       },
       {
        "candidate_id": "capture-02:echo:03",
        "delay_s": 0.010733857416266498,
        "delay_std_s": 4.1666666666666665e-05,
        "amplitude": 0.16200755871144695
       },
       {
        "candidate_id": "capture-02:echo:04",
        "delay_s": 0.011109280346459678,
        "delay_std_s": 4.1666666666666665e-05,
        "amplitude": 0.07417428091053638
       },
       {
        "candidate_id": "capture-02:echo:05",
        "delay_s": 0.016223025502856224,
        "delay_std_s": 4.1666666666666665e-05,
        "amplitude": 0.09654915915974792
       }
      ],
      "clock": {
       "alpha": 1.0000371689666443,
       "alpha_std": 1.1248942649084144e-06
      },
      "direct_std_s": 4.1666666666666665e-05,
      "status": "ok"
     },
     {
      "capture_id": "capture-03",
      "receiver_position_m": [
       -1.1737507032858958,
       3.6170450710342545,
       0.6397477566420586
      ],
      "receiver_position_std_m": 0.006,
      "receiver_pose_group_id": "receiver-pose-03",
      "candidates": [
       {
        "candidate_id": "capture-03:echo:00",
        "delay_s": 0.002751301606602143,
        "delay_std_s": 4.1666666666666665e-05,
        "amplitude": 0.49343552530139057
       },
       {
        "candidate_id": "capture-03:echo:01",
        "delay_s": 0.006125387793611455,
        "delay_std_s": 4.1666666666666665e-05,
        "amplitude": 0.38966704182582945
       },
       {
        "candidate_id": "capture-03:echo:02",
        "delay_s": 0.006700281942432829,
        "delay_std_s": 4.1666666666666665e-05,
        "amplitude": 0.39195950368248766
       },
       {
        "candidate_id": "capture-03:echo:03",
        "delay_s": 0.008060965384783967,
        "delay_std_s": 4.1666666666666665e-05,
        "amplitude": 0.3355050500190598
       },
       {
        "candidate_id": "capture-03:echo:04",
        "delay_s": 0.008574299020243764,
        "delay_std_s": 4.1666666666666665e-05,
        "amplitude": 0.28584164231443604
       },
       {
        "candidate_id": "capture-03:echo:05",
        "delay_s": 0.013481048626942778,
        "delay_std_s": 4.1666666666666665e-05,
        "amplitude": 0.2369538874283424
       }
      ],
      "clock": {
       "alpha": 0.9997917311880886,
       "alpha_std": 1.1248942649084144e-06
      },
      "direct_std_s": 4.1666666666666665e-05,
      "status": "ok"
     },
     {
      "capture_id": "capture-04",
      "receiver_position_m": [
       -1.6578127465714712,
       1.7224861066104302,
       0.9859871915932342
      ],
      "receiver_position_std_m": 0.006,
      "receiver_pose_group_id": "receiver-pose-04",
      "candidates": [
       {
        "candidate_id": "capture-04:echo:00",
        "delay_s": 0.004141834814667843,
        "delay_std_s": 4.1666666666666665e-05,
        "amplitude": 0.3106150003523854
       },
       {
        "candidate_id": "capture-04:echo:01",
        "delay_s": 0.00468381743840472,
        "delay_std_s": 4.1666666666666665e-05,
        "amplitude": 0.29449079459568767
       },
       {
        "candidate_id": "capture-04:echo:02",
        "delay_s": 0.0074503005763464705,
        "delay_std_s": 4.1666666666666665e-05,
        "amplitude": 0.22179627796975857
       },
       {
        "candidate_id": "capture-04:echo:03",
        "delay_s": 0.007861801324522842,
        "delay_std_s": 4.1666666666666665e-05,
        "amplitude": 0.23165830771894447
       },
       {
        "candidate_id": "capture-04:echo:04",
        "delay_s": 0.012290377136268333,
        "delay_std_s": 4.1666666666666665e-05,
        "amplitude": 0.1602657422583384
       },
       {
        "candidate_id": "capture-04:echo:05",
        "delay_s": 0.015365146070727406,
        "delay_std_s": 4.1666666666666665e-05,
        "amplitude": 0.11751013482592673
       },
       {
        "candidate_id": "capture-04:echo:06",
        "delay_s": 0.020539331946128815,
        "delay_std_s": 4.1666666666666665e-05,
        "amplitude": 0.10306037159969657
       }
      ],
      "clock": {
       "alpha": 1.0002216810472442,
       "alpha_std": 1.1248942649084144e-06
      },
      "direct_std_s": 4.1666666666666665e-05,
      "status": "ok"
     },
     {
      "capture_id": "capture-05",
      "receiver_position_m": [
       0.7566217813086723,
       1.9038885564621655,
       2.08855480367412
      ],
      "receiver_position_std_m": 0.006,
      "receiver_pose_group_id": "receiver-pose-05",
      "candidates": [
       {
        "candidate_id": "capture-05:echo:00",
        "delay_s": 0.0020497929336657818,
        "delay_std_s": 4.1666666666666665e-05,
        "amplitude": 0.5021997714239852
       },
       {
        "candidate_id": "capture-05:echo:01",
        "delay_s": 0.0030953582944015607,
        "delay_std_s": 4.1666666666666665e-05,
        "amplitude": 0.47574428816632597
       },
       {
        "candidate_id": "capture-05:echo:02",
        "delay_s": 0.0052170116664012394,
        "delay_std_s": 4.1666666666666665e-05,
        "amplitude": 0.3681169266896886
       },
       {
        "candidate_id": "capture-05:echo:03",
        "delay_s": 0.007215719470108967,
        "delay_std_s": 4.1666666666666665e-05,
        "amplitude": 0.2949400075887756
       },
       {
        "candidate_id": "capture-05:echo:04",
        "delay_s": 0.007644266851624157,
        "delay_std_s": 4.1666666666666665e-05,
        "amplitude": 0.27452402157765265
       },
       {
        "candidate_id": "capture-05:echo:05",
        "delay_s": 0.012617011296569862,
        "delay_std_s": 4.1666666666666665e-05,
        "amplitude": 0.2501022019988107
       },
       {
        "candidate_id": "capture-05:echo:06",
        "delay_s": 0.014569941133245884,
        "delay_std_s": 4.1666666666666665e-05,
        "amplitude": 0.20646622985946037
       }
      ],
      "clock": {
       "alpha": 0.9997866231774115,
       "alpha_std": 1.1248942649084144e-06
      },
      "direct_std_s": 4.1666666666666665e-05,
      "status": "ok"
     },
     {
      "capture_id": "capture-06",
      "receiver_position_m": [
       0.5639505479530454,
       1.6183378718995025,
       1.7709115258515786
      ],
      "receiver_position_std_m": 0.006,
      "receiver_pose_group_id": "receiver-pose-06",
      "candidates": [
       {
        "candidate_id": "capture-06:echo:00",
        "delay_s": 0.0033007117884436615,
        "delay_std_s": 4.1666666666666665e-05,
        "amplitude": 0.40217635127580176
       },
       {
        "candidate_id": "capture-06:echo:01",
        "delay_s": 0.0038219124916322508,
        "delay_std_s": 4.1666666666666665e-05,
        "amplitude": 0.37627368261172606
       },
       {
        "candidate_id": "capture-06:echo:02",
        "delay_s": 0.0052819705281198495,
        "delay_std_s": 4.1666666666666665e-05,
        "amplitude": 0.31438142702661526
       },
       {
        "candidate_id": "capture-06:echo:03",
        "delay_s": 0.007275210159343921,
        "delay_std_s": 4.1666666666666665e-05,
        "amplitude": 0.2979272570294791
       },
       {
        "candidate_id": "capture-06:echo:04",
        "delay_s": 0.009479169663323895,
        "delay_std_s": 4.1666666666666665e-05,
        "amplitude": 0.22437359172235574
       },
       {
        "candidate_id": "capture-06:echo:05",
        "delay_s": 0.014546853521863872,
        "delay_std_s": 4.1666666666666665e-05,
        "amplitude": 0.18742981692761304
       },
       {
        "candidate_id": "capture-06:echo:06",
        "delay_s": 0.015671702392651598,
        "delay_std_s": 4.1666666666666665e-05,
        "amplitude": 0.17758810617496382
       }
      ],
      "clock": {
       "alpha": 1.0000625553352562,
       "alpha_std": 1.1248942649084144e-06
      },
      "direct_std_s": 4.1666666666666665e-05,
      "status": "ok"
     },
     {
      "capture_id": "capture-07",
      "receiver_position_m": [
       -1.3297304443562432,
       2.8218684105853358,
       0.9384998473377993
      ],
      "receiver_position_std_m": 0.006,
      "receiver_pose_group_id": "receiver-pose-07",
      "candidates": [
       {
        "candidate_id": "capture-07:echo:00",
        "delay_s": 0.0039150437755426214,
        "delay_std_s": 4.1666666666666665e-05,
        "amplitude": 0.4074775665004636
       },
       {
        "candidate_id": "capture-07:echo:01",
        "delay_s": 0.006023867746399591,
        "delay_std_s": 4.1666666666666665e-05,
        "amplitude": 0.3076467806210134
       },
       {
        "candidate_id": "capture-07:echo:02",
        "delay_s": 0.006788422698034279,
        "delay_std_s": 4.1666666666666665e-05,
        "amplitude": 0.3148636834944833
       },
       {
        "candidate_id": "capture-07:echo:03",
        "delay_s": 0.008204810667196185,
        "delay_std_s": 4.1666666666666665e-05,
        "amplitude": 0.28715055768841624
       },
       {
        "candidate_id": "capture-07:echo:04",
        "delay_s": 0.009108574986604891,
        "delay_std_s": 4.1666666666666665e-05,
        "amplitude": 0.23887433984065637
       },
       {
        "candidate_id": "capture-07:echo:05",
        "delay_s": 0.011607544063178645,
        "delay_std_s": 4.1666666666666665e-05,
        "amplitude": 0.18138161400086686
       },
       {
        "candidate_id": "capture-07:echo:06",
        "delay_s": 0.0166648276769109,
        "delay_std_s": 4.1666666666666665e-05,
        "amplitude": 0.16680660858120863
       }
      ],
      "clock": {
       "alpha": 0.9998049537130203,
       "alpha_std": 1.1248942649084144e-06
      },
      "direct_std_s": 4.1666666666666665e-05,
      "status": "ok"
     },
     {
      "capture_id": "capture-08",
      "receiver_position_m": [
       -2.4295750269935374,
       2.696309754572328,
       0.06711956893777604
      ],
      "receiver_position_std_m": 0.006,
      "receiver_pose_group_id": "receiver-pose-08",
      "candidates": [
       {
        "candidate_id": "capture-08:echo:00",
        "delay_s": 0.001702653996670529,
        "delay_std_s": 4.1666666666666665e-05,
        "amplitude": 0.5113164471490176
       },
       {
        "candidate_id": "capture-08:echo:01",
        "delay_s": 0.0031120237655465157,
        "delay_std_s": 4.1666666666666665e-05,
        "amplitude": 0.5027838310638788
       },
       {
        "candidate_id": "capture-08:echo:02",
        "delay_s": 0.005680256837533058,
        "delay_std_s": 4.1666666666666665e-05,
        "amplitude": 0.3603852268948364
       },
       {
        "candidate_id": "capture-08:echo:03",
        "delay_s": 0.008381022100294244,
        "delay_std_s": 4.1666666666666665e-05,
        "amplitude": 0.29844347095480034
       },
       {
        "candidate_id": "capture-08:echo:04",
        "delay_s": 0.01309684873172994,
        "delay_std_s": 4.1666666666666665e-05,
        "amplitude": 0.20139136984574715
       },
       {
        "candidate_id": "capture-08:echo:05",
        "delay_s": 0.018102708427539655,
        "delay_std_s": 4.1666666666666665e-05,
        "amplitude": 0.18415948277333719
       }
      ],
      "clock": {
       "alpha": 1.0002216088948055,
       "alpha_std": 1.1248942649084144e-06
      },
      "direct_std_s": 4.1666666666666665e-05,
      "status": "ok"
     },
     {
      "capture_id": "capture-09",
      "receiver_position_m": [
       -1.1321620082574537,
       2.103783246650004,
       0.6031821071277661
      ],
      "receiver_position_std_m": 0.006,
      "receiver_pose_group_id": "receiver-pose-09",
      "candidates": [
       {
        "candidate_id": "capture-09:echo:00",
        "delay_s": 0.004379592083078615,
        "delay_std_s": 4.1666666666666665e-05,
        "amplitude": 0.2895749612751568
       },
       {
        "candidate_id": "capture-09:echo:01",
        "delay_s": 0.006607030185971699,
        "delay_std_s": 4.1666666666666665e-05,
        "amplitude": 0.22262501206916332
       },
       {
        "candidate_id": "capture-09:echo:02",
        "delay_s": 0.008403246479989824,
        "delay_std_s": 4.1666666666666665e-05,
        "amplitude": 0.190341368693359
       },
       {
        "candidate_id": "capture-09:echo:03",
        "delay_s": 0.009320968705367715,
        "delay_std_s": 4.1666666666666665e-05,
        "amplitude": 0.17344467200798783
       },
       {
        "candidate_id": "capture-09:echo:04",
        "delay_s": 0.013226891214417317,
        "delay_std_s": 4.1666666666666665e-05,
        "amplitude": 0.11758306420752108
       },
       {
        "candidate_id": "capture-09:echo:05",
        "delay_s": 0.014341410905477588,
        "delay_std_s": 4.1666666666666665e-05,
        "amplitude": 0.10461811233178142
       },
       {
        "candidate_id": "capture-09:echo:06",
        "delay_s": 0.019527261138572085,
        "delay_std_s": 4.1666666666666665e-05,
        "amplitude": 0.09167647003262085
       }
      ],
      "clock": {
       "alpha": 1.0002487104862876,
       "alpha_std": 1.1248942649084144e-06
      },
      "direct_std_s": 4.1666666666666665e-05,
      "status": "ok"
     },
     {
      "capture_id": "capture-10",
      "receiver_position_m": [
       -1.6225591466580747,
       3.5386181421966616,
       0.0405879612259283
      ],
      "receiver_position_std_m": 0.006,
      "receiver_pose_group_id": "receiver-pose-10",
      "candidates": [
       {
        "candidate_id": "capture-10:echo:00",
        "delay_s": 0.0015550129846640317,
        "delay_std_s": 4.1666666666666665e-05,
        "amplitude": 0.5408690276551744
       },
       {
        "candidate_id": "capture-10:echo:01",
        "delay_s": 0.005012555331206562,
        "delay_std_s": 4.1666666666666665e-05,
        "amplitude": 0.3940796549444075
       },
       {
        "candidate_id": "capture-10:echo:02",
        "delay_s": 0.005565896350965537,
        "delay_std_s": 4.1666666666666665e-05,
        "amplitude": 0.397114598173734
       },
       {
        "candidate_id": "capture-10:echo:03",
        "delay_s": 0.008312718967023278,
        "delay_std_s": 4.1666666666666665e-05,
        "amplitude": 0.34799604245845
       },
       {
        "candidate_id": "capture-10:echo:04",
        "delay_s": 0.009631754398554031,
        "delay_std_s": 4.1666666666666665e-05,
        "amplitude": 0.24467680324346847
       },
       {
        "candidate_id": "capture-10:echo:05",
        "delay_s": 0.014517653720766991,
        "delay_std_s": 4.1666666666666665e-05,
        "amplitude": 0.23378262561800967
       }
      ],
      "clock": {
       "alpha": 0.9999687322815678,
       "alpha_std": 1.1248942649084144e-06
      },
      "direct_std_s": 4.1666666666666665e-05,
      "status": "ok"
     },
     {
      "capture_id": "capture-11",
      "receiver_position_m": [
       0.09087829951602602,
       1.6720710238166085,
       1.4282962807626172
      ],
      "receiver_position_std_m": 0.006,
      "receiver_pose_group_id": "receiver-pose-11",
      "candidates": [
       {
        "candidate_id": "capture-11:echo:00",
        "delay_s": 0.004973814470660219,
        "delay_std_s": 4.1666666666666665e-05,
        "amplitude": 0.32887116391297067
       },
       {
        "candidate_id": "capture-11:echo:01",
        "delay_s": 0.005522512420448777,
        "delay_std_s": 4.1666666666666665e-05,
        "amplitude": 0.27691310785456386
       },
       {
        "candidate_id": "capture-11:echo:02",
        "delay_s": 0.00588616204508387,
        "delay_std_s": 4.1666666666666665e-05,
        "amplitude": 0.2691507273095402
       },
       {
        "candidate_id": "capture-11:echo:03",
        "delay_s": 0.007525531600230294,
        "delay_std_s": 4.1666666666666665e-05,
        "amplitude": 0.218037998443847
       },
       {
        "candidate_id": "capture-11:echo:04",
        "delay_s": 0.011593028816911238,
        "delay_std_s": 4.1666666666666665e-05,
        "amplitude": 0.15064764553160767
       },
       {
        "candidate_id": "capture-11:echo:05",
        "delay_s": 0.015924928776144823,
        "delay_std_s": 4.1666666666666665e-05,
        "amplitude": 0.1295931511554071
       },
       {
        "candidate_id": "capture-11:echo:06",
        "delay_s": 0.01674920335734823,
        "delay_std_s": 4.1666666666666665e-05,
        "amplitude": 0.13208945052925675
       }
      ],
      "clock": {
       "alpha": 0.9997748278152477,
       "alpha_std": 1.1248942649084144e-06
      },
      "direct_std_s": 4.1666666666666665e-05,
      "status": "ok"
     }
    ]
   },
   {
    "session": {
     "session_id": "relocation-finite_panel_four_sources-1003-source-01",
     "source_position_m": [
      -0.010690466427334948,
      1.8058326795345345,
      0.3387049325890533
     ],
     "coordinate_frame_id": "test-frame"
    },
    "observations": [
     {
      "capture_id": "capture-00",
      "receiver_position_m": [
       -1.021216344640526,
       3.2583296014536223,
       1.4728190422780376
      ],
      "receiver_position_std_m": 0.006,
      "receiver_pose_group_id": "receiver-pose-00",
      "candidates": [
       {
        "candidate_id": "capture-00:echo:00",
        "delay_s": 0.0044848311175955365,
        "delay_std_s": 4.1666666666666665e-05,
        "amplitude": 0.3610505944397352
       },
       {
        "candidate_id": "capture-00:echo:01",
        "delay_s": 0.007900450181522158,
        "delay_std_s": 4.1666666666666665e-05,
        "amplitude": 0.3231583073159056
       },
       {
        "candidate_id": "capture-00:echo:02",
        "delay_s": 0.008850282354764257,
        "delay_std_s": 4.1666666666666665e-05,
        "amplitude": 0.2480172566228818
       },
       {
        "candidate_id": "capture-00:echo:03",
        "delay_s": 0.012571159452540608,
        "delay_std_s": 4.1666666666666665e-05,
        "amplitude": 0.21066843415262415
       }
      ],
      "clock": {
       "alpha": 1.00020889665841,
       "alpha_std": 1.1248942649084144e-06
      },
      "direct_std_s": 4.1666666666666665e-05,
      "status": "ok"
     },
     {
      "capture_id": "capture-01",
      "receiver_position_m": [
       -1.3395350103286499,
       2.28426746056934,
       2.0939675115427914
      ],
      "receiver_position_std_m": 0.006,
      "receiver_pose_group_id": "receiver-pose-01",
      "candidates": [
       {
        "candidate_id": "capture-01:echo:00",
        "delay_s": 0.0020640094850196563,
        "delay_std_s": 4.1666666666666665e-05,
        "amplitude": 0.5205004737337652
       },
       {
        "candidate_id": "capture-01:echo:01",
        "delay_s": 0.005256395036028179,
        "delay_std_s": 4.1666666666666665e-05,
        "amplitude": 0.3654361569151934
       },
       {
        "candidate_id": "capture-01:echo:02",
        "delay_s": 0.006222957007043893,
        "delay_std_s": 4.1666666666666665e-05,
        "amplitude": 0.38372827405780024
       },
       {
        "candidate_id": "capture-01:echo:03",
        "delay_s": 0.006708991513651344,
        "delay_std_s": 4.1666666666666665e-05,
        "amplitude": 0.3441350160769073
       },
       {
        "candidate_id": "capture-01:echo:04",
        "delay_s": 0.009744503002467726,
        "delay_std_s": 4.1666666666666665e-05,
        "amplitude": 0.27192405566174954
       },
       {
        "candidate_id": "capture-01:echo:05",
        "delay_s": 0.01457477743198443,
        "delay_std_s": 4.1666666666666665e-05,
        "amplitude": 0.22527568313518442
       }
      ],
      "clock": {
       "alpha": 0.999753638225712,
       "alpha_std": 1.1248942649084144e-06
      },
      "direct_std_s": 4.1666666666666665e-05,
      "status": "ok"
     },
     {
      "capture_id": "capture-02",
      "receiver_position_m": [
       0.2553713673204093,
       1.943866596104725,
       0.012289491846311801
      ],
      "receiver_position_std_m": 0.006,
      "receiver_pose_group_id": "receiver-pose-02",
      "candidates": [
       {
        "candidate_id": "capture-02:echo:00",
        "delay_s": 0.003800630074228323,
        "delay_std_s": 4.1666666666666665e-05,
        "amplitude": 0.1620452180272945
       },
       {
        "candidate_id": "capture-02:echo:01",
        "delay_s": 0.007085950827797897,
        "delay_std_s": 4.1666666666666665e-05,
        "amplitude": 0.10740948043335287
       }
      ],
      "clock": {
       "alpha": 1.000040284752684,
       "alpha_std": 1.1248942649084144e-06
      },
      "direct_std_s": 4.1666666666666665e-05,
      "status": "ok"
     },
     {
      "capture_id": "capture-03",
      "receiver_position_m": [
       -1.1737507032858958,
       3.6170450710342545,
       0.6397477566420586
      ],
      "receiver_position_std_m": 0.006,
      "receiver_pose_group_id": "receiver-pose-03",
      "candidates": [
       {
        "candidate_id": "capture-03:echo:00",
        "delay_s": 0.0029478348976513294,
        "delay_std_s": 4.1666666666666665e-05,
        "amplitude": 0.4493113966551832
       },
       {
        "candidate_id": "capture-03:echo:01",
        "delay_s": 0.006441966494673589,
        "delay_std_s": 4.1666666666666665e-05,
        "amplitude": 0.3285993007048383
       },
       {
        "candidate_id": "capture-03:echo:02",
        "delay_s": 0.007031299838252733,
        "delay_std_s": 4.1666666666666665e-05,
        "amplitude": 0.3314855863280632
       },
       {
        "candidate_id": "capture-03:echo:03",
        "delay_s": 0.008421759481055715,
        "delay_std_s": 4.1666666666666665e-05,
        "amplitude": 0.2843668692833612
       },
       {
        "candidate_id": "capture-03:echo:04",
        "delay_s": 0.009035545750986858,
        "delay_std_s": 4.1666666666666665e-05,
        "amplitude": 0.3009146056993504
       },
       {
        "candidate_id": "capture-03:echo:05",
        "delay_s": 0.012064953652558622,
        "delay_std_s": 4.1666666666666665e-05,
        "amplitude": 0.2353532754691732
       }
      ],
      "clock": {
       "alpha": 0.9998459915091528,
       "alpha_std": 1.1248942649084144e-06
      },
      "direct_std_s": 4.1666666666666665e-05,
      "status": "ok"
     },
     {
      "capture_id": "capture-04",
      "receiver_position_m": [
       -1.6578127465714712,
       1.7224861066104302,
       0.9859871915932342
      ],
      "receiver_position_std_m": 0.006,
      "receiver_pose_group_id": "receiver-pose-04",
      "candidates": [
       {
        "candidate_id": "capture-04:echo:00",
        "delay_s": 0.004042033722695851,
        "delay_std_s": 4.1666666666666665e-05,
        "amplitude": 0.38603108619791715
       },
       {
        "candidate_id": "capture-04:echo:01",
        "delay_s": 0.004850243084024776,
        "delay_std_s": 4.1666666666666665e-05,
        "amplitude": 0.3531326659244075
       },
       {
        "candidate_id": "capture-04:echo:02",
        "delay_s": 0.006656000176595045,
        "delay_std_s": 4.1666666666666665e-05,
        "amplitude": 0.26359249521647454
       },
       {
        "candidate_id": "capture-04:echo:03",
        "delay_s": 0.007051681402286068,
        "delay_std_s": 4.1666666666666665e-05,
        "amplitude": 0.25416429457530315
       },
       {
        "candidate_id": "capture-04:echo:04",
        "delay_s": 0.01134787042114966,
        "delay_std_s": 4.1666666666666665e-05,
        "amplitude": 0.2121564734288571
       },
       {
        "candidate_id": "capture-04:echo:05",
        "delay_s": 0.011919863078540364,
        "delay_std_s": 4.1666666666666665e-05,
        "amplitude": 0.18171776248474633
       },
       {
        "candidate_id": "capture-04:echo:06",
        "delay_s": 0.01707834471402457,
        "delay_std_s": 4.1666666666666665e-05,
        "amplitude": 0.15548417264869602
       }
      ],
      "clock": {
       "alpha": 0.9998815346108708,
       "alpha_std": 1.1248942649084144e-06
      },
      "direct_std_s": 4.1666666666666665e-05,
      "status": "ok"
     },
     {
      "capture_id": "capture-05",
      "receiver_position_m": [
       0.7566217813086723,
       1.9038885564621655,
       2.08855480367412
      ],
      "receiver_position_std_m": 0.006,
      "receiver_pose_group_id": "receiver-pose-05",
      "candidates": [
       {
        "candidate_id": "capture-05:echo:00",
        "delay_s": 0.002326018416101092,
        "delay_std_s": 4.1666666666666665e-05,
        "amplitude": 0.45371030395762074
       },
       {
        "candidate_id": "capture-05:echo:01",
        "delay_s": 0.003462754576494307,
        "delay_std_s": 4.1666666666666665e-05,
        "amplitude": 0.448011807673039
       },
       {
        "candidate_id": "capture-05:echo:02",
        "delay_s": 0.005713772782618998,
        "delay_std_s": 4.1666666666666665e-05,
        "amplitude": 0.35654272213557703
       },
       {
        "candidate_id": "capture-05:echo:03",
        "delay_s": 0.006693568022484245,
        "delay_std_s": 4.1666666666666665e-05,
        "amplitude": 0.2878767838663232
       },
       {
        "candidate_id": "capture-05:echo:04",
        "delay_s": 0.010312233755444692,
        "delay_std_s": 4.1666666666666665e-05,
        "amplitude": 0.24204966207193035
       },
       {
        "candidate_id": "capture-05:echo:05",
        "delay_s": 0.011579829299628521,
        "delay_std_s": 4.1666666666666665e-05,
        "amplitude": 0.21002165446753004
       },
       {
        "candidate_id": "capture-05:echo:06",
        "delay_s": 0.01531772466654162,
        "delay_std_s": 4.1666666666666665e-05,
        "amplitude": 0.1905267174278084
       }
      ],
      "clock": {
       "alpha": 1.000203176240042,
       "alpha_std": 1.1248942649084144e-06
      },
      "direct_std_s": 4.1666666666666665e-05,
      "status": "ok"
     },
     {
      "capture_id": "capture-06",
      "receiver_position_m": [
       0.5639505479530454,
       1.6183378718995025,
       1.7709115258515786
      ],
      "receiver_position_std_m": 0.006,
      "receiver_pose_group_id": "receiver-pose-06",
      "candidates": [
       {
        "candidate_id": "capture-06:echo:00",
        "delay_s": 0.0036702755995081243,
        "delay_std_s": 4.1666666666666665e-05,
        "amplitude": 0.3654436167484534
       },
       {
        "candidate_id": "capture-06:echo:01",
        "delay_s": 0.004223165632075332,
        "delay_std_s": 4.1666666666666665e-05,
        "amplitude": 0.3847831223483328
       },
       {
        "candidate_id": "capture-06:echo:02",
        "delay_s": 0.005752556863851875,
        "delay_std_s": 4.1666666666666665e-05,
        "amplitude": 0.2905573840279391
       },
       {
        "candidate_id": "capture-06:echo:03",
        "delay_s": 0.008299801543849357,
        "delay_std_s": 4.1666666666666665e-05,
        "amplitude": 0.20594279038224356
       },
       {
        "candidate_id": "capture-06:echo:04",
        "delay_s": 0.010233737520228414,
        "delay_std_s": 4.1666666666666665e-05,
        "amplitude": 0.19530548756148833
       },
       {
        "candidate_id": "capture-06:echo:05",
        "delay_s": 0.013313051201153663,
        "delay_std_s": 4.1666666666666665e-05,
        "amplitude": 0.17563775017956434
       },
       {
        "candidate_id": "capture-06:echo:06",
        "delay_s": 0.016352271333077824,
        "delay_std_s": 4.1666666666666665e-05,
        "amplitude": 0.1545584371623281
       }
      ],
      "clock": {
       "alpha": 0.9997735433893051,
       "alpha_std": 1.1248942649084144e-06
      },
      "direct_std_s": 4.1666666666666665e-05,
      "status": "ok"
     },
     {
      "capture_id": "capture-07",
      "receiver_position_m": [
       -1.3297304443562432,
       2.8218684105853358,
       0.9384998473377993
      ],
      "receiver_position_std_m": 0.006,
      "receiver_pose_group_id": "receiver-pose-07",
      "candidates": [
       {
        "candidate_id": "capture-07:echo:00",
        "delay_s": 0.003947385741569223,
        "delay_std_s": 4.1666666666666665e-05,
        "amplitude": 0.37260563867105434
       },
       {
        "candidate_id": "capture-07:echo:01",
        "delay_s": 0.006829557006632528,
        "delay_std_s": 4.1666666666666665e-05,
        "amplitude": 0.30647053236395705
       },
       {
        "candidate_id": "capture-07:echo:02",
        "delay_s": 0.00808234972091545,
        "delay_std_s": 4.1666666666666665e-05,
        "amplitude": 0.2827692315062477
       },
       {
        "candidate_id": "capture-07:echo:03",
        "delay_s": 0.009155152210142688,
        "delay_std_s": 4.1666666666666665e-05,
        "amplitude": 0.22614137739359885
       },
       {
        "candidate_id": "capture-07:echo:04",
        "delay_s": 0.009612466440320431,
        "delay_std_s": 4.1666666666666665e-05,
        "amplitude": 0.18706999852688025
       },
       {
        "candidate_id": "capture-07:echo:05",
        "delay_s": 0.014618690997943327,
        "delay_std_s": 4.1666666666666665e-05,
        "amplitude": 0.1835857920937642
       }
      ],
      "clock": {
       "alpha": 0.9998758311305611,
       "alpha_std": 1.1248942649084144e-06
      },
      "direct_std_s": 4.1666666666666665e-05,
      "status": "ok"
     },
     {
      "capture_id": "capture-08",
      "receiver_position_m": [
       -2.4295750269935374,
       2.696309754572328,
       0.06711956893777604
      ],
      "receiver_position_std_m": 0.006,
      "receiver_pose_group_id": "receiver-pose-08",
      "candidates": [
       {
        "candidate_id": "capture-08:echo:00",
        "delay_s": 0.0015601589321499916,
        "delay_std_s": 4.1666666666666665e-05,
        "amplitude": 0.5520280723437417
       },
       {
        "candidate_id": "capture-08:echo:01",
        "delay_s": 0.004058260650971994,
        "delay_std_s": 4.1666666666666665e-05,
        "amplitude": 0.4093704335676322
       },
       {
        "candidate_id": "capture-08:echo:02",
        "delay_s": 0.005344862455412401,
        "delay_std_s": 4.1666666666666665e-05,
        "amplitude": 0.3849984352429678
       },
       {
        "candidate_id": "capture-08:echo:03",
        "delay_s": 0.007876413772034976,
        "delay_std_s": 4.1666666666666665e-05,
        "amplitude": 0.3009566286614293
       },
       {
        "candidate_id": "capture-08:echo:04",
        "delay_s": 0.010281105697467166,
        "delay_std_s": 4.1666666666666665e-05,
        "amplitude": 0.24915288914219794
       },
       {
        "candidate_id": "capture-08:echo:05",
        "delay_s": 0.015233661240182909,
        "delay_std_s": 4.1666666666666665e-05,
        "amplitude": 0.23193440506739083
       }
      ],
      "clock": {
       "alpha": 1.0002273699039768,
       "alpha_std": 1.1248942649084144e-06
      },
      "direct_std_s": 4.1666666666666665e-05,
      "status": "ok"
     },
     {
      "capture_id": "capture-09",
      "receiver_position_m": [
       -1.1321620082574537,
       2.103783246650004,
       0.6031821071277661
      ],
      "receiver_position_std_m": 0.006,
      "receiver_pose_group_id": "receiver-pose-09",
      "candidates": [
       {
        "candidate_id": "capture-09:echo:00",
        "delay_s": 0.004069089210400275,
        "delay_std_s": 4.1666666666666665e-05,
        "amplitude": 0.2971012445943444
       },
       {
        "candidate_id": "capture-09:echo:01",
        "delay_s": 0.008164126996287567,
        "delay_std_s": 4.1666666666666665e-05,
        "amplitude": 0.19615677942185714
       },
       {
        "candidate_id": "capture-09:echo:02",
        "delay_s": 0.008917359117735826,
        "delay_std_s": 4.1666666666666665e-05,
        "amplitude": 0.18949040426137126
       },
       {
        "candidate_id": "capture-09:echo:03",
        "delay_s": 0.011646932359540577,
        "delay_std_s": 4.1666666666666665e-05,
        "amplitude": 0.1380458245479878
       },
       {
        "candidate_id": "capture-09:echo:04",
        "delay_s": 0.012788759728347908,
        "delay_std_s": 4.1666666666666665e-05,
        "amplitude": 0.1531383365277325
       },
       {
        "candidate_id": "capture-09:echo:05",
        "delay_s": 0.016818796749296993,
        "delay_std_s": 4.1666666666666665e-05,
        "amplitude": 0.10896866978369237
       }
      ],
      "clock": {
       "alpha": 0.9997580481324282,
       "alpha_std": 1.1248942649084144e-06
      },
      "direct_std_s": 4.1666666666666665e-05,
      "status": "ok"
     },
     {
      "capture_id": "capture-10",
      "receiver_position_m": [
       -1.6225591466580747,
       3.5386181421966616,
       0.0405879612259283
      ],
      "receiver_position_std_m": 0.006,
      "receiver_pose_group_id": "receiver-pose-10",
      "candidates": [
       {
        "candidate_id": "capture-10:echo:00",
        "delay_s": 0.0016033099660561928,
        "delay_std_s": 4.1666666666666665e-05,
        "amplitude": 0.5723603936898568
       },
       {
        "candidate_id": "capture-10:echo:01",
        "delay_s": 0.0051239366599907105,
        "delay_std_s": 4.1666666666666665e-05,
        "amplitude": 0.4105753369579188
       },
       {
        "candidate_id": "capture-10:echo:02",
        "delay_s": 0.007715379534336314,
        "delay_std_s": 4.1666666666666665e-05,
        "amplitude": 0.31578605044133706
       },
       {
        "candidate_id": "capture-10:echo:03",
        "delay_s": 0.008272421819107383,
        "delay_std_s": 4.1666666666666665e-05,
        "amplitude": 0.353494469128884
       },
       {
        "candidate_id": "capture-10:echo:04",
        "delay_s": 0.012726912792811634,
        "delay_std_s": 4.1666666666666665e-05,
        "amplitude": 0.2599912230111875
       }
      ],
      "clock": {
       "alpha": 0.9998900412545251,
       "alpha_std": 1.1248942649084144e-06
      },
      "direct_std_s": 4.1666666666666665e-05,
      "status": "ok"
     },
     {
      "capture_id": "capture-11",
      "receiver_position_m": [
       0.09087829951602602,
       1.6720710238166085,
       1.4282962807626172
      ],
      "receiver_position_std_m": 0.006,
      "receiver_pose_group_id": "receiver-pose-11",
      "candidates": [
       {
        "candidate_id": "capture-11:echo:00",
        "delay_s": 0.005369113484957794,
        "delay_std_s": 4.1666666666666665e-05,
        "amplitude": 0.25035143945700017
       },
       {
        "candidate_id": "capture-11:echo:01",
        "delay_s": 0.005933488213638358,
        "delay_std_s": 4.1666666666666665e-05,
        "amplitude": 0.23266177120768083
       },
       {
        "candidate_id": "capture-11:echo:02",
        "delay_s": 0.006307216910264804,
        "delay_std_s": 4.1666666666666665e-05,
        "amplitude": 0.21359470205736938
       },
       {
        "candidate_id": "capture-11:echo:03",
        "delay_s": 0.010301111409401079,
        "delay_std_s": 4.1666666666666665e-05,
        "amplitude": 0.16804987843593466
       },
       {
        "candidate_id": "capture-11:echo:04",
        "delay_s": 0.015259608435474277,
        "delay_std_s": 4.1666666666666665e-05,
        "amplitude": 0.11601410244334065
       },
       {
        "candidate_id": "capture-11:echo:05",
        "delay_s": 0.016469946329129646,
        "delay_std_s": 4.1666666666666665e-05,
        "amplitude": 0.10421432452182051
       }
      ],
      "clock": {
       "alpha": 1.0000871668161122,
       "alpha_std": 1.1248942649084144e-06
      },
      "direct_std_s": 4.1666666666666665e-05,
      "status": "ok"
     }
    ]
   },
   {
    "session": {
     "session_id": "relocation-finite_panel_four_sources-1003-source-02",
     "source_position_m": [
      -1.063937097976136,
      1.8816893934796273,
      0.3439300468451523
     ],
     "coordinate_frame_id": "test-frame"
    },
    "observations": [
     {
      "capture_id": "capture-00",
      "receiver_position_m": [
       -1.021216344640526,
       3.2583296014536223,
       1.4728190422780376
      ],
      "receiver_position_std_m": 0.006,
      "receiver_pose_group_id": "receiver-pose-00",
      "candidates": [
       {
        "candidate_id": "capture-00:echo:00",
        "delay_s": 0.004910418476903534,
        "delay_std_s": 4.1666666666666665e-05,
        "amplitude": 0.33577628668161996
       },
       {
        "candidate_id": "capture-00:echo:01",
        "delay_s": 0.007118432047247017,
        "delay_std_s": 4.1666666666666665e-05,
        "amplitude": 0.2631500443745092
       },
       {
        "candidate_id": "capture-00:echo:02",
        "delay_s": 0.010077315866458637,
        "delay_std_s": 4.1666666666666665e-05,
        "amplitude": 0.2164819480400659
       },
       {
        "candidate_id": "capture-00:echo:03",
        "delay_s": 0.01117692059453101,
        "delay_std_s": 4.1666666666666665e-05,
        "amplitude": 0.21490667315050363
       },
       {
        "candidate_id": "capture-00:echo:04",
        "delay_s": 0.015152592111981264,
        "delay_std_s": 4.1666666666666665e-05,
        "amplitude": 0.1646927203786903
       }
      ],
      "clock": {
       "alpha": 0.9998498320476481,
       "alpha_std": 1.1248942649084144e-06
      },
      "direct_std_s": 4.1666666666666665e-05,
      "status": "ok"
     },
     {
      "capture_id": "capture-01",
      "receiver_position_m": [
       -1.3395350103286499,
       2.28426746056934,
       2.0939675115427914
      ],
      "receiver_position_std_m": 0.006,
      "receiver_pose_group_id": "receiver-pose-01",
      "candidates": [
       {
        "candidate_id": "capture-01:echo:00",
        "delay_s": 0.0024057813257237553,
        "delay_std_s": 4.1666666666666665e-05,
        "amplitude": 0.4914590565173447
       },
       {
        "candidate_id": "capture-01:echo:01",
        "delay_s": 0.005108619328765868,
        "delay_std_s": 4.1666666666666665e-05,
        "amplitude": 0.36398563633617603
       },
       {
        "candidate_id": "capture-01:echo:02",
        "delay_s": 0.005860505037026629,
        "delay_std_s": 4.1666666666666665e-05,
        "amplitude": 0.33742404105278434
       },
       {
        "candidate_id": "capture-01:echo:03",
        "delay_s": 0.008815719201905232,
        "delay_std_s": 4.1666666666666665e-05,
        "amplitude": 0.2667614069631221
       },
       {
        "candidate_id": "capture-01:echo:04",
        "delay_s": 0.009843026422614871,
        "delay_std_s": 4.1666666666666665e-05,
        "amplitude": 0.24749209894743568
       },
       {
        "candidate_id": "capture-01:echo:05",
        "delay_s": 0.012623622701262898,
        "delay_std_s": 4.1666666666666665e-05,
        "amplitude": 0.17782212760194402
       },
       {
        "candidate_id": "capture-01:echo:06",
        "delay_s": 0.017685271845950586,
        "delay_std_s": 4.1666666666666665e-05,
        "amplitude": 0.1552335247453706
       }
      ],
      "clock": {
       "alpha": 1.0002468902444885,
       "alpha_std": 1.1248942649084144e-06
      },
      "direct_std_s": 4.1666666666666665e-05,
      "status": "ok"
     },
     {
      "capture_id": "capture-02",
      "receiver_position_m": [
       0.2553713673204093,
       1.943866596104725,
       0.012289491846311801
      ],
      "receiver_position_std_m": 0.006,
      "receiver_pose_group_id": "receiver-pose-02",
      "candidates": [
       {
        "candidate_id": "capture-02:echo:00",
        "delay_s": 0.0023535766424749287,
        "delay_std_s": 4.1666666666666665e-05,
        "amplitude": 0.4318826577240541
       },
       {
        "candidate_id": "capture-02:echo:01",
        "delay_s": 0.006956888512707967,
        "delay_std_s": 4.1666666666666665e-05,
        "amplitude": 0.24668960836946097
       },
       {
        "candidate_id": "capture-02:echo:02",
        "delay_s": 0.008110243438480547,
        "delay_std_s": 4.1666666666666665e-05,
        "amplitude": 0.23427528763096656
       },
       {
        "candidate_id": "capture-02:echo:03",
        "delay_s": 0.010150407356381588,
        "delay_std_s": 4.1666666666666665e-05,
        "amplitude": 0.21269553440931688
       },
       {
        "candidate_id": "capture-02:echo:04",
        "delay_s": 0.010524942316088793,
        "delay_std_s": 4.1666666666666665e-05,
        "amplitude": 0.09241447842769078
       },
       {
        "candidate_id": "capture-02:echo:05",
        "delay_s": 0.01322280777011383,
        "delay_std_s": 4.1666666666666665e-05,
        "amplitude": 0.14764271446634336
       },
       {
        "candidate_id": "capture-02:echo:06",
        "delay_s": 0.015647448492989234,
        "delay_std_s": 4.1666666666666665e-05,
        "amplitude": 0.14984564136808087
       }
      ],
      "clock": {
       "alpha": 1.000196494356477,
       "alpha_std": 1.1248942649084144e-06
      },
      "direct_std_s": 4.1666666666666665e-05,
      "status": "ok"
     },
     {
      "capture_id": "capture-03",
      "receiver_position_m": [
       -1.1737507032858958,
       3.6170450710342545,
       0.6397477566420586
      ],
      "receiver_position_std_m": 0.006,
      "receiver_pose_group_id": "receiver-pose-03",
      "candidates": [
       {
        "candidate_id": "capture-03:echo:00",
        "delay_s": 0.0033712419929318995,
        "delay_std_s": 4.1666666666666665e-05,
        "amplitude": 0.4245175160401227
       },
       {
        "candidate_id": "capture-03:echo:01",
        "delay_s": 0.005864056112542118,
        "delay_std_s": 4.1666666666666665e-05,
        "amplitude": 0.30002425830877993
       },
       {
        "candidate_id": "capture-03:echo:02",
        "delay_s": 0.007342374613375289,
        "delay_std_s": 4.1666666666666665e-05,
        "amplitude": 0.1316446912424877
       },
       {
        "candidate_id": "capture-03:echo:03",
        "delay_s": 0.0077034025966571185,
        "delay_std_s": 4.1666666666666665e-05,
        "amplitude": 0.286348739570472
       },
       {
        "candidate_id": "capture-03:echo:04",
        "delay_s": 0.009682885590089913,
        "delay_std_s": 4.1666666666666665e-05,
        "amplitude": 0.21196964697913018
       },
       {
        "candidate_id": "capture-03:echo:05",
        "delay_s": 0.012045693534912815,
        "delay_std_s": 4.1666666666666665e-05,
        "amplitude": 0.19277102771383386
       },
       {
        "candidate_id": "capture-03:echo:06",
        "delay_s": 0.014772372047971877,
        "delay_std_s": 4.1666666666666665e-05,
        "amplitude": 0.17289774993939852
       }
      ],
      "clock": {
       "alpha": 0.9998221536287757,
       "alpha_std": 1.1248942649084144e-06
      },
      "direct_std_s": 4.1666666666666665e-05,
      "status": "ok"
     },
     {
      "capture_id": "capture-04",
      "receiver_position_m": [
       -1.6578127465714712,
       1.7224861066104302,
       0.9859871915932342
      ],
      "receiver_position_std_m": 0.006,
      "receiver_pose_group_id": "receiver-pose-04",
      "candidates": [
       {
        "candidate_id": "capture-04:echo:00",
        "delay_s": 0.004881880752712498,
        "delay_std_s": 4.1666666666666665e-05,
        "amplitude": 0.2412855235153142
       },
       {
        "candidate_id": "capture-04:echo:01",
        "delay_s": 0.005458456673485455,
        "delay_std_s": 4.1666666666666665e-05,
        "amplitude": 0.2321432477927856
       },
       {
        "candidate_id": "capture-04:echo:02",
        "delay_s": 0.008351842824470313,
        "delay_std_s": 4.1666666666666665e-05,
        "amplitude": 0.16426276557819683
       },
       {
        "candidate_id": "capture-04:echo:03",
        "delay_s": 0.011337220997983162,
        "delay_std_s": 4.1666666666666665e-05,
        "amplitude": 0.11578573926757016
       },
       {
        "candidate_id": "capture-04:echo:04",
        "delay_s": 0.01641921997334908,
        "delay_std_s": 4.1666666666666665e-05,
        "amplitude": 0.08393618508264636
       }
      ],
      "clock": {
       "alpha": 1.000063997632019,
       "alpha_std": 1.1248942649084144e-06
      },
      "direct_std_s": 4.1666666666666665e-05,
      "status": "ok"
     },
     {
      "capture_id": "capture-05",
      "receiver_position_m": [
       0.7566217813086723,
       1.9038885564621655,
       2.08855480367412
      ],
      "receiver_position_std_m": 0.006,
      "receiver_pose_group_id": "receiver-pose-05",
      "candidates": [
       {
        "candidate_id": "capture-05:echo:00",
        "delay_s": 0.0018861712512839174,
        "delay_std_s": 4.1666666666666665e-05,
        "amplitude": 0.5104607380441791
       },
       {
        "candidate_id": "capture-05:echo:01",
        "delay_s": 0.00407362760338655,
        "delay_std_s": 4.1666666666666665e-05,
        "amplitude": 0.4112880045414372
       },
       {
        "candidate_id": "capture-05:echo:02",
        "delay_s": 0.0049057422683638765,
        "delay_std_s": 4.1666666666666665e-05,
        "amplitude": 0.39269946521719484
       },
       {
        "candidate_id": "capture-05:echo:03",
        "delay_s": 0.006844817777586224,
        "delay_std_s": 4.1666666666666665e-05,
        "amplitude": 0.3194961182110515
       },
       {
        "candidate_id": "capture-05:echo:04",
        "delay_s": 0.007263052039928342,
        "delay_std_s": 4.1666666666666665e-05,
        "amplitude": 0.2698014617676423
       },
       {
        "candidate_id": "capture-05:echo:05",
        "delay_s": 0.011763860789093762,
        "delay_std_s": 4.1666666666666665e-05,
        "amplitude": 0.23705271378851295
       },
       {
        "candidate_id": "capture-05:echo:06",
        "delay_s": 0.012145434481178543,
        "delay_std_s": 4.1666666666666665e-05,
        "amplitude": 0.2546510477765239
       }
      ],
      "clock": {
       "alpha": 1.0000825192120166,
       "alpha_std": 1.1248942649084144e-06
      },
      "direct_std_s": 4.1666666666666665e-05,
      "status": "ok"
     },
     {
      "capture_id": "capture-06",
      "receiver_position_m": [
       0.5639505479530454,
       1.6183378718995025,
       1.7709115258515786
      ],
      "receiver_position_std_m": 0.006,
      "receiver_pose_group_id": "receiver-pose-06",
      "candidates": [
       {
        "candidate_id": "capture-06:echo:00",
        "delay_s": 0.003451185801620208,
        "delay_std_s": 4.1666666666666665e-05,
        "amplitude": 0.41747086075315293
       },
       {
        "candidate_id": "capture-06:echo:01",
        "delay_s": 0.0041693571785841625,
        "delay_std_s": 4.1666666666666665e-05,
        "amplitude": 0.43484973224033147
       },
       {
        "candidate_id": "capture-06:echo:02",
        "delay_s": 0.004834061325382227,
        "delay_std_s": 4.1666666666666665e-05,
        "amplitude": 0.4014814275206876
       },
       {
        "candidate_id": "capture-06:echo:03",
        "delay_s": 0.0067482858138869116,
        "delay_std_s": 4.1666666666666665e-05,
        "amplitude": 0.32869296057418035
       },
       {
        "candidate_id": "capture-06:echo:04",
        "delay_s": 0.008886713233128804,
        "delay_std_s": 4.1666666666666665e-05,
        "amplitude": 0.24501049852183587
       },
       {
        "candidate_id": "capture-06:echo:05",
        "delay_s": 0.01259216007205004,
        "delay_std_s": 4.1666666666666665e-05,
        "amplitude": 0.23074385601203773
       },
       {
        "candidate_id": "capture-06:echo:06",
        "delay_s": 0.013860924757031805,
        "delay_std_s": 4.1666666666666665e-05,
        "amplitude": 0.22151094123363677
       }
      ],
      "clock": {
       "alpha": 1.0002165353866177,
       "alpha_std": 1.1248942649084144e-06
      },
      "direct_std_s": 4.1666666666666665e-05,
      "status": "ok"
     },
     {
      "capture_id": "capture-07",
      "receiver_position_m": [
       -1.3297304443562432,
       2.8218684105853358,
       0.9384998473377993
      ],
      "receiver_position_std_m": 0.006,
      "receiver_pose_group_id": "receiver-pose-07",
      "candidates": [
       {
        "candidate_id": "capture-07:echo:00",
        "delay_s": 0.004862296063199251,
        "delay_std_s": 4.1666666666666665e-05,
        "amplitude": 0.25178415447340385
       },
       {
        "candidate_id": "capture-07:echo:01",
        "delay_s": 0.007159196012760413,
        "delay_std_s": 4.1666666666666665e-05,
        "amplitude": 0.21345671829848287
       },
       {
        "candidate_id": "capture-07:echo:02",
        "delay_s": 0.007972431737875636,
        "delay_std_s": 4.1666666666666665e-05,
        "amplitude": 0.20039881800458226
       },
       {
        "candidate_id": "capture-07:echo:03",
        "delay_s": 0.008822611605331224,
        "delay_std_s": 4.1666666666666665e-05,
        "amplitude": 0.1753738818046398
       },
       {
        "candidate_id": "capture-07:echo:04",
        "delay_s": 0.012233577737840251,
        "delay_std_s": 4.1666666666666665e-05,
        "amplitude": 0.14176798514234223
       },
       {
        "candidate_id": "capture-07:echo:05",
        "delay_s": 0.012995371000843846,
        "delay_std_s": 4.1666666666666665e-05,
        "amplitude": 0.12482326010920966
       },
       {
        "candidate_id": "capture-07:echo:06",
        "delay_s": 0.0181657280697691,
        "delay_std_s": 4.1666666666666665e-05,
        "amplitude": 0.11119208633353223
       }
      ],
      "clock": {
       "alpha": 0.9998801867886996,
       "alpha_std": 1.1248942649084144e-06
      },
      "direct_std_s": 4.1666666666666665e-05,
      "status": "ok"
     },
     {
      "capture_id": "capture-08",
      "receiver_position_m": [
       -2.4295750269935374,
       2.696309754572328,
       0.06711956893777604
      ],
      "receiver_position_std_m": 0.006,
      "receiver_pose_group_id": "receiver-pose-08",
      "candidates": [
       {
        "candidate_id": "capture-08:echo:00",
        "delay_s": 0.0022393189078851795,
        "delay_std_s": 4.1666666666666665e-05,
        "amplitude": 0.42262970594299865
       },
       {
        "candidate_id": "capture-08:echo:01",
        "delay_s": 0.0039086080663399,
        "delay_std_s": 4.1666666666666665e-05,
        "amplitude": 0.3576528773244584
       },
       {
        "candidate_id": "capture-08:echo:02",
        "delay_s": 0.005608841324431512,
        "delay_std_s": 4.1666666666666665e-05,
        "amplitude": 0.29875436352024
       },
       {
        "candidate_id": "capture-08:echo:03",
        "delay_s": 0.0095613532982948,
        "delay_std_s": 4.1666666666666665e-05,
        "amplitude": 0.2313111517526392
       },
       {
        "candidate_id": "capture-08:echo:04",
        "delay_s": 0.012642921228469089,
        "delay_std_s": 4.1666666666666665e-05,
        "amplitude": 0.19102037793049478
       },
       {
        "candidate_id": "capture-08:echo:05",
        "delay_s": 0.014576944977798502,
        "delay_std_s": 4.1666666666666665e-05,
        "amplitude": 0.14739531907417527
       },
       {
        "candidate_id": "capture-08:echo:06",
        "delay_s": 0.019707158614879865,
        "delay_std_s": 4.1666666666666665e-05,
        "amplitude": 0.13787516423356425
       }
      ],
      "clock": {
       "alpha": 0.9998934628721662,
       "alpha_std": 1.1248942649084144e-06
      },
      "direct_std_s": 4.1666666666666665e-05,
      "status": "ok"
     },
     {
      "capture_id": "capture-09",
      "receiver_position_m": [
       -1.1321620082574537,
       2.103783246650004,
       0.6031821071277661
      ],
      "receiver_position_std_m": 0.006,
      "receiver_pose_group_id": "receiver-pose-09",
      "candidates": [
       {
        "candidate_id": "capture-09:echo:00",
        "delay_s": 0.005741428781794467,
        "delay_std_s": 4.1666666666666665e-05,
        "amplitude": 0.0977731338848351
       },
       {
        "candidate_id": "capture-09:echo:01",
        "delay_s": 0.008098270314562712,
        "delay_std_s": 4.1666666666666665e-05,
        "amplitude": 0.07495793449567385
       }
      ],
      "clock": {
       "alpha": 0.9999009668466542,
       "alpha_std": 1.1248942649084144e-06
      },
      "direct_std_s": 4.1666666666666665e-05,
      "status": "ok"
     },
     {
      "capture_id": "capture-10",
      "receiver_position_m": [
       -1.6225591466580747,
       3.5386181421966616,
       0.0405879612259283
      ],
      "receiver_position_std_m": 0.006,
      "receiver_pose_group_id": "receiver-pose-10",
      "candidates": [
       {
        "candidate_id": "capture-10:echo:00",
        "delay_s": 0.002010401782231771,
        "delay_std_s": 4.1666666666666665e-05,
        "amplitude": 0.4986694259176065
       },
       {
        "candidate_id": "capture-10:echo:01",
        "delay_s": 0.0049114803405414745,
        "delay_std_s": 4.1666666666666665e-05,
        "amplitude": 0.3164103230341358
       },
       {
        "candidate_id": "capture-10:echo:02",
        "delay_s": 0.006577442622801816,
        "delay_std_s": 4.1666666666666665e-05,
        "amplitude": 0.27303747645537413
       },
       {
        "candidate_id": "capture-10:echo:03",
        "delay_s": 0.009323925405944561,
        "delay_std_s": 4.1666666666666665e-05,
        "amplitude": 0.23357718616824463
       },
       {
        "candidate_id": "capture-10:echo:04",
        "delay_s": 0.010906213569011877,
        "delay_std_s": 4.1666666666666665e-05,
        "amplitude": 0.18802887182447642
       },
       {
        "candidate_id": "capture-10:echo:05",
        "delay_s": 0.012521700067643103,
        "delay_std_s": 4.1666666666666665e-05,
        "amplitude": 0.19526961776712662
       },
       {
        "candidate_id": "capture-10:echo:06",
        "delay_s": 0.015969477924109507,
        "delay_std_s": 4.1666666666666665e-05,
        "amplitude": 0.1573493263058262
       }
      ],
      "clock": {
       "alpha": 1.00024263812112,
       "alpha_std": 1.1248942649084144e-06
      },
      "direct_std_s": 4.1666666666666665e-05,
      "status": "ok"
     },
     {
      "capture_id": "capture-11",
      "receiver_position_m": [
       0.09087829951602602,
       1.6720710238166085,
       1.4282962807626172
      ],
      "receiver_position_std_m": 0.006,
      "receiver_pose_group_id": "receiver-pose-11",
      "candidates": [
       {
        "candidate_id": "capture-11:echo:00",
        "delay_s": 0.005067984511565009,
        "delay_std_s": 4.1666666666666665e-05,
        "amplitude": 0.3227651031979147
       },
       {
        "candidate_id": "capture-11:echo:01",
        "delay_s": 0.0054169415086710495,
        "delay_std_s": 4.1666666666666665e-05,
        "amplitude": 0.31249528116624137
       },
       {
        "candidate_id": "capture-11:echo:02",
        "delay_s": 0.006161048506881462,
        "delay_std_s": 4.1666666666666665e-05,
        "amplitude": 0.27368782820657583
       },
       {
        "candidate_id": "capture-11:echo:03",
        "delay_s": 0.00700739935920873,
        "delay_std_s": 4.1666666666666665e-05,
        "amplitude": 0.26838447403743837
       },
       {
        "candidate_id": "capture-11:echo:04",
        "delay_s": 0.010996141058595706,
        "delay_std_s": 4.1666666666666665e-05,
        "amplitude": 0.17695524241395166
       },
       {
        "candidate_id": "capture-11:echo:05",
        "delay_s": 0.012963199487407541,
        "delay_std_s": 4.1666666666666665e-05,
        "amplitude": 0.18621874117649803
       },
       {
        "candidate_id": "capture-11:echo:06",
        "delay_s": 0.01609714430048028,
        "delay_std_s": 4.1666666666666665e-05,
        "amplitude": 0.1436262589784895
       }
      ],
      "clock": {
       "alpha": 1.000105853072525,
       "alpha_std": 1.1248942649084144e-06
      },
      "direct_std_s": 4.1666666666666665e-05,
      "status": "ok"
     }
    ]
   },
   {
    "session": {
     "session_id": "relocation-finite_panel_four_sources-1003-source-03",
     "source_position_m": [
      -0.5998043873611618,
      1.5599228361353603,
      0.9369995665007834
     ],
     "coordinate_frame_id": "test-frame"
    },
    "observations": [
     {
      "capture_id": "capture-00",
      "receiver_position_m": [
       -1.021216344640526,
       3.2583296014536223,
       1.4728190422780376
      ],
      "receiver_position_std_m": 0.006,
      "receiver_pose_group_id": "receiver-pose-00",
      "candidates": [
       {
        "candidate_id": "capture-00:echo:00",
        "delay_s": 0.0038556752153457627,
        "delay_std_s": 4.1666666666666665e-05,
        "amplitude": 0.4008976928044418
       },
       {
        "candidate_id": "capture-00:echo:01",
        "delay_s": 0.0068256854450000305,
        "delay_std_s": 4.1666666666666665e-05,
        "amplitude": 0.2802627350352223
       },
       {
        "candidate_id": "capture-00:echo:02",
        "delay_s": 0.007543401613749599,
        "delay_std_s": 4.1666666666666665e-05,
        "amplitude": 0.28179591408675325
       },
       {
        "candidate_id": "capture-00:echo:03",
        "delay_s": 0.008211597505345475,
        "delay_std_s": 4.1666666666666665e-05,
        "amplitude": 0.2663354845690685
       },
       {
        "candidate_id": "capture-00:echo:04",
        "delay_s": 0.009150489313716507,
        "delay_std_s": 4.1666666666666665e-05,
        "amplitude": 0.2441051198724564
       },
       {
        "candidate_id": "capture-00:echo:05",
        "delay_s": 0.009653095973926515,
        "delay_std_s": 4.1666666666666665e-05,
        "amplitude": 0.19760136949096058
       },
       {
        "candidate_id": "capture-00:echo:06",
        "delay_s": 0.014691231193345264,
        "delay_std_s": 4.1666666666666665e-05,
        "amplitude": 0.1777800875342213
       }
      ],
      "clock": {
       "alpha": 0.9999704545029309,
       "alpha_std": 1.1248942649084144e-06
      },
      "direct_std_s": 4.1666666666666665e-05,
      "status": "ok"
     },
     {
      "capture_id": "capture-01",
      "receiver_position_m": [
       -1.3395350103286499,
       2.28426746056934,
       2.0939675115427914
      ],
      "receiver_position_std_m": 0.006,
      "receiver_pose_group_id": "receiver-pose-01",
      "candidates": [
       {
        "candidate_id": "capture-01:echo:00",
        "delay_s": 0.002048072232924636,
        "delay_std_s": 4.1666666666666665e-05,
        "amplitude": 0.4856546865845875
       },
       {
        "candidate_id": "capture-01:echo:01",
        "delay_s": 0.005912444656738188,
        "delay_std_s": 4.1666666666666665e-05,
        "amplitude": 0.2893210231816254
       },
       {
        "candidate_id": "capture-01:echo:02",
        "delay_s": 0.008715695577376045,
        "delay_std_s": 4.1666666666666665e-05,
        "amplitude": 0.16528636474670655
       },
       {
        "candidate_id": "capture-01:echo:03",
        "delay_s": 0.010631025091893955,
        "delay_std_s": 4.1666666666666665e-05,
        "amplitude": 0.2197779898186752
       },
       {
        "candidate_id": "capture-01:echo:04",
        "delay_s": 0.012774390192593828,
        "delay_std_s": 4.1666666666666665e-05,
        "amplitude": 0.17009705435090017
       },
       {
        "candidate_id": "capture-01:echo:05",
        "delay_s": 0.017878479891661803,
        "delay_std_s": 4.1666666666666665e-05,
        "amplitude": 0.14510700903288426
       }
      ],
      "clock": {
       "alpha": 1.0001552450148312,
       "alpha_std": 1.1248942649084144e-06
      },
      "direct_std_s": 4.1666666666666665e-05,
      "status": "ok"
     },
     {
      "capture_id": "capture-02",
      "receiver_position_m": [
       0.2553713673204093,
       1.943866596104725,
       0.012289491846311801
      ],
      "receiver_position_std_m": 0.006,
      "receiver_pose_group_id": "receiver-pose-02",
      "candidates": [
       {
        "candidate_id": "capture-02:echo:00",
        "delay_s": 0.0034666496832714386,
        "delay_std_s": 4.1666666666666665e-05,
        "amplitude": 0.3403551600599628
       },
       {
        "candidate_id": "capture-02:echo:01",
        "delay_s": 0.005796307701338442,
        "delay_std_s": 4.1666666666666665e-05,
        "amplitude": 0.27078219248578306
       },
       {
        "candidate_id": "capture-02:echo:02",
        "delay_s": 0.008331794076756062,
        "delay_std_s": 4.1666666666666665e-05,
        "amplitude": 0.21513804944518847
       },
       {
        "candidate_id": "capture-02:echo:03",
        "delay_s": 0.008746437505510544,
        "delay_std_s": 4.1666666666666665e-05,
        "amplitude": 0.20415828347143386
       },
       {
        "candidate_id": "capture-02:echo:04",
        "delay_s": 0.010238401208576154,
        "delay_std_s": 4.1666666666666665e-05,
        "amplitude": 0.15361452420025826
       },
       {
        "candidate_id": "capture-02:echo:05",
        "delay_s": 0.01506076993444034,
        "delay_std_s": 4.1666666666666665e-05,
        "amplitude": 0.141304945207154
       }
      ],
      "clock": {
       "alpha": 1.0000421961195711,
       "alpha_std": 1.1248942649084144e-06
      },
      "direct_std_s": 4.1666666666666665e-05,
      "status": "ok"
     },
     {
      "capture_id": "capture-03",
      "receiver_position_m": [
       -1.1737507032858958,
       3.6170450710342545,
       0.6397477566420586
      ],
      "receiver_position_std_m": 0.006,
      "receiver_pose_group_id": "receiver-pose-03",
      "candidates": [
       {
        "candidate_id": "capture-03:echo:00",
        "delay_s": 0.004325082570134848,
        "delay_std_s": 4.1666666666666665e-05,
        "amplitude": 0.42765784633379933
       },
       {
        "candidate_id": "capture-03:echo:01",
        "delay_s": 0.0055429058299653455,
        "delay_std_s": 4.1666666666666665e-05,
        "amplitude": 0.3700787560591959
       },
       {
        "candidate_id": "capture-03:echo:02",
        "delay_s": 0.0061696277747637605,
        "delay_std_s": 4.1666666666666665e-05,
        "amplitude": 0.33983241364473865
       },
       {
        "candidate_id": "capture-03:echo:03",
        "delay_s": 0.007263366599065495,
        "delay_std_s": 4.1666666666666665e-05,
        "amplitude": 0.3383562615590746
       },
       {
        "candidate_id": "capture-03:echo:04",
        "delay_s": 0.008654787080912147,
        "delay_std_s": 4.1666666666666665e-05,
        "amplitude": 0.25869396988401394
       },
       {
        "candidate_id": "capture-03:echo:05",
        "delay_s": 0.009260258761744435,
        "delay_std_s": 4.1666666666666665e-05,
        "amplitude": 0.2866778477879259
       },
       {
        "candidate_id": "capture-03:echo:06",
        "delay_s": 0.013601920576233207,
        "delay_std_s": 4.1666666666666665e-05,
        "amplitude": 0.22691173030631775
       }
      ],
      "clock": {
       "alpha": 0.9997562135730846,
       "alpha_std": 1.1248942649084144e-06
      },
      "direct_std_s": 4.1666666666666665e-05,
      "status": "ok"
     },
     {
      "capture_id": "capture-04",
      "receiver_position_m": [
       -1.6578127465714712,
       1.7224861066104302,
       0.9859871915932342
      ],
      "receiver_position_std_m": 0.006,
      "receiver_pose_group_id": "receiver-pose-04",
      "candidates": [
       {
        "candidate_id": "capture-04:echo:00",
        "delay_s": 0.0048561607093601375,
        "delay_std_s": 4.1666666666666665e-05,
        "amplitude": 0.266607329570027
       },
       {
        "candidate_id": "capture-04:echo:01",
        "delay_s": 0.006440094513896814,
        "delay_std_s": 4.1666666666666665e-05,
        "amplitude": 0.21800847158138428
       },
       {
        "candidate_id": "capture-04:echo:02",
        "delay_s": 0.0069622007614829305,
        "delay_std_s": 4.1666666666666665e-05,
        "amplitude": 0.20147724308284404
       },
       {
        "candidate_id": "capture-04:echo:03",
        "delay_s": 0.009078600308556659,
        "delay_std_s": 4.1666666666666665e-05,
        "amplitude": 0.1836652396498763
       },
       {
        "candidate_id": "capture-04:echo:04",
        "delay_s": 0.012375794292344068,
        "delay_std_s": 4.1666666666666665e-05,
        "amplitude": 0.1402579534546076
       },
       {
        "candidate_id": "capture-04:echo:05",
        "delay_s": 0.015482877176924807,
        "delay_std_s": 4.1666666666666665e-05,
        "amplitude": 0.09829782771642841
       },
       {
        "candidate_id": "capture-04:echo:06",
        "delay_s": 0.020692723492753667,
        "delay_std_s": 4.1666666666666665e-05,
        "amplitude": 0.08285333834703808
       }
      ],
      "clock": {
       "alpha": 0.9998037943575674,
       "alpha_std": 1.1248942649084144e-06
      },
      "direct_std_s": 4.1666666666666665e-05,
      "status": "ok"
     },
     {
      "capture_id": "capture-05",
      "receiver_position_m": [
       0.7566217813086723,
       1.9038885564621655,
       2.08855480367412
      ],
      "receiver_position_std_m": 0.006,
      "receiver_pose_group_id": "receiver-pose-05",
      "candidates": [
       {
        "candidate_id": "capture-05:echo:00",
        "delay_s": 0.0018375127515740915,
        "delay_std_s": 4.1666666666666665e-05,
        "amplitude": 0.5312929359477339
       },
       {
        "candidate_id": "capture-05:echo:01",
        "delay_s": 0.003970866203585368,
        "delay_std_s": 4.1666666666666665e-05,
        "amplitude": 0.3720269300346961
       },
       {
        "candidate_id": "capture-05:echo:02",
        "delay_s": 0.00815798522305125,
        "delay_std_s": 4.1666666666666665e-05,
        "amplitude": 0.2478372399435871
       },
       {
        "candidate_id": "capture-05:echo:03",
        "delay_s": 0.008527046775608078,
        "delay_std_s": 4.1666666666666665e-05,
        "amplitude": 0.26181000474948674
       },
       {
        "candidate_id": "capture-05:echo:04",
        "delay_s": 0.013218739267328736,
        "delay_std_s": 4.1666666666666665e-05,
        "amplitude": 0.1939513413713457
       },
       {
        "candidate_id": "capture-05:echo:05",
        "delay_s": 0.014942350577271583,
        "delay_std_s": 4.1666666666666665e-05,
        "amplitude": 0.18691348653878623
       }
      ],
      "clock": {
       "alpha": 1.0002009202201538,
       "alpha_std": 1.1248942649084144e-06
      },
      "direct_std_s": 4.1666666666666665e-05,
      "status": "ok"
     },
     {
      "capture_id": "capture-06",
      "receiver_position_m": [
       0.5639505479530454,
       1.6183378718995025,
       1.7709115258515786
      ],
      "receiver_position_std_m": 0.006,
      "receiver_pose_group_id": "receiver-pose-06",
      "candidates": [
       {
        "candidate_id": "capture-06:echo:00",
        "delay_s": 0.0034419516878207404,
        "delay_std_s": 4.1666666666666665e-05,
        "amplitude": 0.39890473431497336
       },
       {
        "candidate_id": "capture-06:echo:01",
        "delay_s": 0.00422195374444806,
        "delay_std_s": 4.1666666666666665e-05,
        "amplitude": 0.3296049898002732
       },
       {
        "candidate_id": "capture-06:echo:02",
        "delay_s": 0.008171309389954133,
        "delay_std_s": 4.1666666666666665e-05,
        "amplitude": 0.24608921119563773
       },
       {
        "candidate_id": "capture-06:echo:03",
        "delay_s": 0.008565846289741982,
        "delay_std_s": 4.1666666666666665e-05,
        "amplitude": 0.23740751381933048
       },
       {
        "candidate_id": "capture-06:echo:04",
        "delay_s": 0.009977158406844695,
        "delay_std_s": 4.1666666666666665e-05,
        "amplitude": 0.17873320418585717
       },
       {
        "candidate_id": "capture-06:echo:05",
        "delay_s": 0.015122232588591682,
        "delay_std_s": 4.1666666666666665e-05,
        "amplitude": 0.1503079896433135
       },
       {
        "candidate_id": "capture-06:echo:06",
        "delay_s": 0.016005553367117432,
        "delay_std_s": 4.1666666666666665e-05,
        "amplitude": 0.15972805474571086
       }
      ],
      "clock": {
       "alpha": 1.0002404688242508,
       "alpha_std": 1.1248942649084144e-06
      },
      "direct_std_s": 4.1666666666666665e-05,
      "status": "ok"
     },
     {
      "capture_id": "capture-07",
      "receiver_position_m": [
       -1.3297304443562432,
       2.8218684105853358,
       0.9384998473377993
      ],
      "receiver_position_std_m": 0.006,
      "receiver_pose_group_id": "receiver-pose-07",
      "candidates": [
       {
        "candidate_id": "capture-07:echo:00",
        "delay_s": 0.006100227428836672,
        "delay_std_s": 4.1666666666666665e-05,
        "amplitude": 0.288792943374245
       },
       {
        "candidate_id": "capture-07:echo:01",
        "delay_s": 0.007020100448056029,
        "delay_std_s": 4.1666666666666665e-05,
        "amplitude": 0.26406912055366527
       },
       {
        "candidate_id": "capture-07:echo:02",
        "delay_s": 0.009351470037186935,
        "delay_std_s": 4.1666666666666665e-05,
        "amplitude": 0.239284753804043
       },
       {
        "candidate_id": "capture-07:echo:03",
        "delay_s": 0.011900212004656997,
        "delay_std_s": 4.1666666666666665e-05,
        "amplitude": 0.15709908190388294
       },
       {
        "candidate_id": "capture-07:echo:04",
        "delay_s": 0.01700889689197326,
        "delay_std_s": 4.1666666666666665e-05,
        "amplitude": 0.12470472758312326
       }
      ],
      "clock": {
       "alpha": 1.0000089595180603,
       "alpha_std": 1.1248942649084144e-06
      },
      "direct_std_s": 4.1666666666666665e-05,
      "status": "ok"
     },
     {
      "capture_id": "capture-08",
      "receiver_position_m": [
       -2.4295750269935374,
       2.696309754572328,
       0.06711956893777604
      ],
      "receiver_position_std_m": 0.006,
      "receiver_pose_group_id": "receiver-pose-08",
      "candidates": [
       {
        "candidate_id": "capture-08:echo:00",
        "delay_s": 0.002559035561147007,
        "delay_std_s": 4.1666666666666665e-05,
        "amplitude": 0.4924031063391716
       },
       {
        "candidate_id": "capture-08:echo:01",
        "delay_s": 0.003371720855729324,
        "delay_std_s": 4.1666666666666665e-05,
        "amplitude": 0.4533381560095591
       },
       {
        "candidate_id": "capture-08:echo:02",
        "delay_s": 0.005408155750830694,
        "delay_std_s": 4.1666666666666665e-05,
        "amplitude": 0.3466977018208857
       },
       {
        "candidate_id": "capture-08:echo:03",
        "delay_s": 0.006527010321343971,
        "delay_std_s": 4.1666666666666665e-05,
        "amplitude": 0.3422643296921713
       },
       {
        "candidate_id": "capture-08:echo:04",
        "delay_s": 0.009189428981543603,
        "delay_std_s": 4.1666666666666665e-05,
        "amplitude": 0.2994931481221492
       },
       {
        "candidate_id": "capture-08:echo:05",
        "delay_s": 0.01264882951342958,
        "delay_std_s": 4.1666666666666665e-05,
        "amplitude": 0.21682515726641086
       },
       {
        "candidate_id": "capture-08:echo:06",
        "delay_s": 0.01765170568908778,
        "delay_std_s": 4.1666666666666665e-05,
        "amplitude": 0.1897752019309127
       }
      ],
      "clock": {
       "alpha": 1.000034214217229,
       "alpha_std": 1.1248942649084144e-06
      },
      "direct_std_s": 4.1666666666666665e-05,
      "status": "ok"
     },
     {
      "capture_id": "capture-09",
      "receiver_position_m": [
       -1.1321620082574537,
       2.103783246650004,
       0.6031821071277661
      ],
      "receiver_position_std_m": 0.006,
      "receiver_pose_group_id": "receiver-pose-09",
      "candidates": [
       {
        "candidate_id": "capture-09:echo:00",
        "delay_s": 0.00633666770423369,
        "delay_std_s": 4.1666666666666665e-05,
        "amplitude": 0.18689664950603244
       },
       {
        "candidate_id": "capture-09:echo:01",
        "delay_s": 0.0073830621910156696,
        "delay_std_s": 4.1666666666666665e-05,
        "amplitude": 0.1557207993007455
       },
       {
        "candidate_id": "capture-09:echo:02",
        "delay_s": 0.007974014059620194,
        "delay_std_s": 4.1666666666666665e-05,
        "amplitude": 0.1585507592753267
       },
       {
        "candidate_id": "capture-09:echo:03",
        "delay_s": 0.009485085022086993,
        "delay_std_s": 4.1666666666666665e-05,
        "amplitude": 0.1318577571769433
       },
       {
        "candidate_id": "capture-09:echo:04",
        "delay_s": 0.01314302521651354,
        "delay_std_s": 4.1666666666666665e-05,
        "amplitude": 0.10666916669286036
       },
       {
        "candidate_id": "capture-09:echo:05",
        "delay_s": 0.014323887514606436,
        "delay_std_s": 4.1666666666666665e-05,
        "amplitude": 0.07926162246787327
       },
       {
        "candidate_id": "capture-09:echo:06",
        "delay_s": 0.019524004670235552,
        "delay_std_s": 4.1666666666666665e-05,
        "amplitude": 0.07390553118519212
       }
      ],
      "clock": {
       "alpha": 0.9999609712997662,
       "alpha_std": 1.1248942649084144e-06
      },
      "direct_std_s": 4.1666666666666665e-05,
      "status": "ok"
     },
     {
      "capture_id": "capture-10",
      "receiver_position_m": [
       -1.6225591466580747,
       3.5386181421966616,
       0.0405879612259283
      ],
      "receiver_position_std_m": 0.006,
      "receiver_pose_group_id": "receiver-pose-10",
      "candidates": [
       {
        "candidate_id": "capture-10:echo:00",
        "delay_s": 0.00240208107328937,
        "delay_std_s": 4.1666666666666665e-05,
        "amplitude": 0.46908273687945273
       },
       {
        "candidate_id": "capture-10:echo:01",
        "delay_s": 0.004849881697116018,
        "delay_std_s": 4.1666666666666665e-05,
        "amplitude": 0.41571824561155485
       },
       {
        "candidate_id": "capture-10:echo:02",
        "delay_s": 0.006090169936281397,
        "delay_std_s": 4.1666666666666665e-05,
        "amplitude": 0.32178937191086693
       },
       {
        "candidate_id": "capture-10:echo:03",
        "delay_s": 0.00648190969705991,
        "delay_std_s": 4.1666666666666665e-05,
        "amplitude": 0.3375843250980843
       },
       {
        "candidate_id": "capture-10:echo:04",
        "delay_s": 0.00924405431331517,
        "delay_std_s": 4.1666666666666665e-05,
        "amplitude": 0.2945146437937126
       },
       {
        "candidate_id": "capture-10:echo:05",
        "delay_s": 0.014280815408453834,
        "delay_std_s": 4.1666666666666665e-05,
        "amplitude": 0.2150183119682433
       }
      ],
      "clock": {
       "alpha": 0.9998687414228958,
       "alpha_std": 1.1248942649084144e-06
      },
      "direct_std_s": 4.1666666666666665e-05,
      "status": "ok"
     },
     {
      "capture_id": "capture-11",
      "receiver_position_m": [
       0.09087829951602602,
       1.6720710238166085,
       1.4282962807626172
      ],
      "receiver_position_std_m": 0.006,
      "receiver_pose_group_id": "receiver-pose-11",
      "candidates": [
       {
        "candidate_id": "capture-11:echo:00",
        "delay_s": 0.00552336985085915,
        "delay_std_s": 4.1666666666666665e-05,
        "amplitude": 0.2142429883268639
       },
       {
        "candidate_id": "capture-11:echo:01",
        "delay_s": 0.0063451394804372166,
        "delay_std_s": 4.1666666666666665e-05,
        "amplitude": 0.1690293523658211
       },
       {
        "candidate_id": "capture-11:echo:02",
        "delay_s": 0.008568736133283695,
        "delay_std_s": 4.1666666666666665e-05,
        "amplitude": 0.14357521214554989
       },
       {
        "candidate_id": "capture-11:echo:03",
        "delay_s": 0.00901977054794785,
        "delay_std_s": 4.1666666666666665e-05,
        "amplitude": 0.14176408505856444
       },
       {
        "candidate_id": "capture-11:echo:04",
        "delay_s": 0.012305004312285718,
        "delay_std_s": 4.1666666666666665e-05,
        "amplitude": 0.09181884061110139
       },
       {
        "candidate_id": "capture-11:echo:05",
        "delay_s": 0.016475749736900604,
        "delay_std_s": 4.1666666666666665e-05,
        "amplitude": 0.08653902910088536
       },
       {
        "candidate_id": "capture-11:echo:06",
        "delay_s": 0.017519084422326286,
        "delay_std_s": 4.1666666666666665e-05,
        "amplitude": 0.08342392556319266
       }
      ],
      "clock": {
       "alpha": 1.0000520716753112,
       "alpha_std": 1.1248942649084144e-06
      },
      "direct_std_s": 4.1666666666666665e-05,
      "status": "ok"
     }
    ]
   }
  ],
  "surfaces": [
   {
    "surface_id": "reflector-f4d5526dc7045ebd",
    "normal": [
     0.0018959933461920205,
     -0.001083452270390444,
     0.9999976156673621
    ],
    "offset_m": -0.6860097222127997,
    "support": [
     {
      "session_id": "relocation-finite_panel_four_sources-1003-source-00",
      "capture_id": "capture-01",
      "candidate_id": "capture-01:echo:02"
     },
     {
      "session_id": "relocation-finite_panel_four_sources-1003-source-00",
      "capture_id": "capture-02",
      "candidate_id": "capture-02:echo:00"
     },
     {
      "session_id": "relocation-finite_panel_four_sources-1003-source-00",
      "capture_id": "capture-03",
      "candidate_id": "capture-03:echo:00"
     },
     {
      "session_id": "relocation-finite_panel_four_sources-1003-source-00",
      "capture_id": "capture-04",
      "candidate_id": "capture-04:echo:01"
     },
     {
      "session_id": "relocation-finite_panel_four_sources-1003-source-00",
      "capture_id": "capture-05",
      "candidate_id": "capture-05:echo:02"
     },
     {
      "session_id": "relocation-finite_panel_four_sources-1003-source-00",
      "capture_id": "capture-06",
      "candidate_id": "capture-06:echo:02"
     },
     {
      "session_id": "relocation-finite_panel_four_sources-1003-source-00",
      "capture_id": "capture-07",
      "candidate_id": "capture-07:echo:00"
     },
     {
      "session_id": "relocation-finite_panel_four_sources-1003-source-00",
      "capture_id": "capture-08",
      "candidate_id": "capture-08:echo:00"
     },
     {
      "session_id": "relocation-finite_panel_four_sources-1003-source-00",
      "capture_id": "capture-09",
      "candidate_id": "capture-09:echo:00"
     },
     {
      "session_id": "relocation-finite_panel_four_sources-1003-source-00",
      "capture_id": "capture-10",
      "candidate_id": "capture-10:echo:00"
     },
     {
      "session_id": "relocation-finite_panel_four_sources-1003-source-00",
      "capture_id": "capture-11",
      "candidate_id": "capture-11:echo:01"
     },
     {
      "session_id": "relocation-finite_panel_four_sources-1003-source-01",
      "capture_id": "capture-00",
      "candidate_id": "capture-00:echo:00"
     },
     {
      "session_id": "relocation-finite_panel_four_sources-1003-source-01",
      "capture_id": "capture-01",
      "candidate_id": "capture-01:echo:01"
     },
     {
      "session_id": "relocation-finite_panel_four_sources-1003-source-01",
      "capture_id": "capture-02",
      "candidate_id": "capture-02:echo:00"
     },
     {
      "session_id": "relocation-finite_panel_four_sources-1003-source-01",
      "capture_id": "capture-03",
      "candidate_id": "capture-03:echo:00"
     },
     {
      "session_id": "relocation-finite_panel_four_sources-1003-source-01",
      "capture_id": "capture-04",
      "candidate_id": "capture-04:echo:00"
     },
     {
      "session_id": "relocation-finite_panel_four_sources-1003-source-01",
      "capture_id": "capture-05",
      "candidate_id": "capture-05:echo:02"
     },
     {
      "session_id": "relocation-finite_panel_four_sources-1003-source-01",
      "capture_id": "capture-06",
      "candidate_id": "capture-06:echo:02"
     },
     {
      "session_id": "relocation-finite_panel_four_sources-1003-source-01",
      "capture_id": "capture-07",
      "candidate_id": "capture-07:echo:00"
     },
     {
      "session_id": "relocation-finite_panel_four_sources-1003-source-01",
      "capture_id": "capture-08",
      "candidate_id": "capture-08:echo:00"
     },
     {
      "session_id": "relocation-finite_panel_four_sources-1003-source-01",
      "capture_id": "capture-09",
      "candidate_id": "capture-09:echo:00"
     },
     {
      "session_id": "relocation-finite_panel_four_sources-1003-source-01",
      "capture_id": "capture-10",
      "candidate_id": "capture-10:echo:00"
     },
     {
      "session_id": "relocation-finite_panel_four_sources-1003-source-01",
      "capture_id": "capture-11",
      "candidate_id": "capture-11:echo:01"
     },
     {
      "session_id": "relocation-finite_panel_four_sources-1003-source-02",
      "capture_id": "capture-00",
      "candidate_id": "capture-00:echo:00"
     },
     {
      "session_id": "relocation-finite_panel_four_sources-1003-source-02",
      "capture_id": "capture-01",
      "candidate_id": "capture-01:echo:02"
     },
     {
      "session_id": "relocation-finite_panel_four_sources-1003-source-02",
      "capture_id": "capture-02",
      "candidate_id": "capture-02:echo:00"
     },
     {
      "session_id": "relocation-finite_panel_four_sources-1003-source-02",
      "capture_id": "capture-03",
      "candidate_id": "capture-03:echo:00"
     },
     {
      "session_id": "relocation-finite_panel_four_sources-1003-source-02",
      "capture_id": "capture-04",
      "candidate_id": "capture-04:echo:01"
     },
     {
      "session_id": "relocation-finite_panel_four_sources-1003-source-02",
      "capture_id": "capture-05",
      "candidate_id": "capture-05:echo:02"
     },
     {
      "session_id": "relocation-finite_panel_four_sources-1003-source-02",
      "capture_id": "capture-06",
      "candidate_id": "capture-06:echo:02"
     },
     {
      "session_id": "relocation-finite_panel_four_sources-1003-source-02",
      "capture_id": "capture-07",
      "candidate_id": "capture-07:echo:00"
     },
     {
      "session_id": "relocation-finite_panel_four_sources-1003-source-02",
      "capture_id": "capture-08",
      "candidate_id": "capture-08:echo:00"
     },
     {
      "session_id": "relocation-finite_panel_four_sources-1003-source-02",
      "capture_id": "capture-09",
      "candidate_id": "capture-09:echo:00"
     },
     {
      "session_id": "relocation-finite_panel_four_sources-1003-source-02",
      "capture_id": "capture-10",
      "candidate_id": "capture-10:echo:00"
     },
     {
      "session_id": "relocation-finite_panel_four_sources-1003-source-02",
      "capture_id": "capture-11",
      "candidate_id": "capture-11:echo:00"
     },
     {
      "session_id": "relocation-finite_panel_four_sources-1003-source-03",
      "capture_id": "capture-00",
      "candidate_id": "capture-00:echo:01"
     },
     {
      "session_id": "relocation-finite_panel_four_sources-1003-source-03",
      "capture_id": "capture-01",
      "candidate_id": "capture-01:echo:02"
     },
     {
      "session_id": "relocation-finite_panel_four_sources-1003-source-03",
      "capture_id": "capture-02",
      "candidate_id": "capture-02:echo:00"
     },
     {
      "session_id": "relocation-finite_panel_four_sources-1003-source-03",
      "capture_id": "capture-03",
      "candidate_id": "capture-03:echo:00"
     },
     {
      "session_id": "relocation-finite_panel_four_sources-1003-source-03",
      "capture_id": "capture-04",
      "candidate_id": "capture-04:echo:02"
     },
     {
      "session_id": "relocation-finite_panel_four_sources-1003-source-03",
      "capture_id": "capture-05",
      "candidate_id": "capture-05:echo:02"
     },
     {
      "session_id": "relocation-finite_panel_four_sources-1003-source-03",
      "capture_id": "capture-06",
      "candidate_id": "capture-06:echo:02"
     },
     {
      "session_id": "relocation-finite_panel_four_sources-1003-source-03",
      "capture_id": "capture-07",
      "candidate_id": "capture-07:echo:00"
     },
     {
      "session_id": "relocation-finite_panel_four_sources-1003-source-03",
      "capture_id": "capture-08",
      "candidate_id": "capture-08:echo:00"
     },
     {
      "session_id": "relocation-finite_panel_four_sources-1003-source-03",
      "capture_id": "capture-09",
      "candidate_id": "capture-09:echo:00"
     },
     {
      "session_id": "relocation-finite_panel_four_sources-1003-source-03",
      "capture_id": "capture-10",
      "candidate_id": "capture-10:echo:00"
     },
     {
      "session_id": "relocation-finite_panel_four_sources-1003-source-03",
      "capture_id": "capture-11",
      "candidate_id": "capture-11:echo:02"
     }
    ]
   },
   {
    "surface_id": "reflector-6b3163d991cec770",
    "normal": [
     0.756748804692627,
     0.6537056949648442,
     0.0003331168122295295
    ],
    "offset_m": -1.0858114102814231,
    "support": [
     {
      "session_id": "relocation-finite_panel_four_sources-1003-source-00",
      "capture_id": "capture-00",
      "candidate_id": "capture-00:echo:01"
     },
     {
      "session_id": "relocation-finite_panel_four_sources-1003-source-00",
      "capture_id": "capture-01",
      "candidate_id": "capture-01:echo:01"
     },
     {
      "session_id": "relocation-finite_panel_four_sources-1003-source-00",
      "capture_id": "capture-02",
      "candidate_id": "capture-02:echo:02"
     },
     {
      "session_id": "relocation-finite_panel_four_sources-1003-source-00",
      "capture_id": "capture-04",
      "candidate_id": "capture-04:echo:00"
     },
     {
      "session_id": "relocation-finite_panel_four_sources-1003-source-00",
      "capture_id": "capture-05",
      "candidate_id": "capture-05:echo:03"
     },
     {
      "session_id": "relocation-finite_panel_four_sources-1003-source-00",
      "capture_id": "capture-06",
      "candidate_id": "capture-06:echo:03"
     },
     {
      "session_id": "relocation-finite_panel_four_sources-1003-source-00",
      "capture_id": "capture-07",
      "candidate_id": "capture-07:echo:01"
     },
     {
      "session_id": "relocation-finite_panel_four_sources-1003-source-00",
      "capture_id": "capture-08",
      "candidate_id": "capture-08:echo:01"
     },
     {
      "session_id": "relocation-finite_panel_four_sources-1003-source-00",
      "capture_id": "capture-09",
      "candidate_id": "capture-09:echo:01"
     },
     {
      "session_id": "relocation-finite_panel_four_sources-1003-source-00",
      "capture_id": "capture-10",
      "candidate_id": "capture-10:echo:02"
     },
     {
      "session_id": "relocation-finite_panel_four_sources-1003-source-00",
      "capture_id": "capture-11",
      "candidate_id": "capture-11:echo:03"
     },
     {
      "session_id": "relocation-finite_panel_four_sources-1003-source-01",
      "capture_id": "capture-00",
      "candidate_id": "capture-00:echo:02"
     },
     {
      "session_id": "relocation-finite_panel_four_sources-1003-source-01",
      "capture_id": "capture-01",
      "candidate_id": "capture-01:echo:02"
     },
     {
      "session_id": "relocation-finite_panel_four_sources-1003-source-01",
      "capture_id": "capture-03",
      "candidate_id": "capture-03:echo:04"
     },
     {
      "session_id": "relocation-finite_panel_four_sources-1003-source-01",
      "capture_id": "capture-04",
      "candidate_id": "capture-04:echo:01"
     },
     {
      "session_id": "relocation-finite_panel_four_sources-1003-source-01",
      "capture_id": "capture-05",
      "candidate_id": "capture-05:echo:04"
     },
     {
      "session_id": "relocation-finite_panel_four_sources-1003-source-01",
      "capture_id": "capture-06",
      "candidate_id": "capture-06:echo:04"
     },
     {
      "session_id": "relocation-finite_panel_four_sources-1003-source-01",
      "capture_id": "capture-07",
      "candidate_id": "capture-07:echo:02"
     },
     {
      "session_id": "relocation-finite_panel_four_sources-1003-source-01",
      "capture_id": "capture-08",
      "candidate_id": "capture-08:echo:01"
     },
     {
      "session_id": "relocation-finite_panel_four_sources-1003-source-01",
      "capture_id": "capture-09",
      "candidate_id": "capture-09:echo:01"
     },
     {
      "session_id": "relocation-finite_panel_four_sources-1003-source-01",
      "capture_id": "capture-10",
      "candidate_id": "capture-10:echo:02"
     },
     {
      "session_id": "relocation-finite_panel_four_sources-1003-source-01",
      "capture_id": "capture-11",
      "candidate_id": "capture-11:echo:03"
     },
     {
      "session_id": "relocation-finite_panel_four_sources-1003-source-02",
      "capture_id": "capture-00",
      "candidate_id": "capture-00:echo:01"
     },
     {
      "session_id": "relocation-finite_panel_four_sources-1003-source-02",
      "capture_id": "capture-01",
      "candidate_id": "capture-01:echo:01"
     },
     {
      "session_id": "relocation-finite_panel_four_sources-1003-source-02",
      "capture_id": "capture-02",
      "candidate_id": "capture-02:echo:02"
     },
     {
      "session_id": "relocation-finite_panel_four_sources-1003-source-02",
      "capture_id": "capture-03",
      "candidate_id": "capture-03:echo:02"
     },
     {
      "session_id": "relocation-finite_panel_four_sources-1003-source-02",
      "capture_id": "capture-04",
      "candidate_id": "capture-04:echo:00"
     },
     {
      "session_id": "relocation-finite_panel_four_sources-1003-source-02",
      "capture_id": "capture-05",
      "candidate_id": "capture-05:echo:03"
     },
     {
      "session_id": "relocation-finite_panel_four_sources-1003-source-02",
      "capture_id": "capture-06",
      "candidate_id": "capture-06:echo:03"
     },
     {
      "session_id": "relocation-finite_panel_four_sources-1003-source-02",
      "capture_id": "capture-07",
      "candidate_id": "capture-07:echo:01"
     },
     {
      "session_id": "relocation-finite_panel_four_sources-1003-source-02",
      "capture_id": "capture-08",
      "candidate_id": "capture-08:echo:01"
     },
     {
      "session_id": "relocation-finite_panel_four_sources-1003-source-02",
      "capture_id": "capture-09",
      "candidate_id": "capture-09:echo:01"
     },
     {
      "session_id": "relocation-finite_panel_four_sources-1003-source-02",
      "capture_id": "capture-10",
      "candidate_id": "capture-10:echo:02"
     },
     {
      "session_id": "relocation-finite_panel_four_sources-1003-source-02",
      "capture_id": "capture-11",
      "candidate_id": "capture-11:echo:03"
     },
     {
      "session_id": "relocation-finite_panel_four_sources-1003-source-03",
      "capture_id": "capture-00",
      "candidate_id": "capture-00:echo:02"
     },
     {
      "session_id": "relocation-finite_panel_four_sources-1003-source-03",
      "capture_id": "capture-01",
      "candidate_id": "capture-01:echo:01"
     },
     {
      "session_id": "relocation-finite_panel_four_sources-1003-source-03",
      "capture_id": "capture-02",
      "candidate_id": "capture-02:echo:03"
     },
     {
      "session_id": "relocation-finite_panel_four_sources-1003-source-03",
      "capture_id": "capture-03",
      "candidate_id": "capture-03:echo:03"
     },
     {
      "session_id": "relocation-finite_panel_four_sources-1003-source-03",
      "capture_id": "capture-04",
      "candidate_id": "capture-04:echo:00"
     },
     {
      "session_id": "relocation-finite_panel_four_sources-1003-source-03",
      "capture_id": "capture-05",
      "candidate_id": "capture-05:echo:03"
     },
     {
      "session_id": "relocation-finite_panel_four_sources-1003-source-03",
      "capture_id": "capture-06",
      "candidate_id": "capture-06:echo:03"
     },
     {
      "session_id": "relocation-finite_panel_four_sources-1003-source-03",
      "capture_id": "capture-07",
      "candidate_id": "capture-07:echo:01"
     },
     {
      "session_id": "relocation-finite_panel_four_sources-1003-source-03",
      "capture_id": "capture-08",
      "candidate_id": "capture-08:echo:01"
     },
     {
      "session_id": "relocation-finite_panel_four_sources-1003-source-03",
      "capture_id": "capture-09",
      "candidate_id": "capture-09:echo:01"
     },
     {
      "session_id": "relocation-finite_panel_four_sources-1003-source-03",
      "capture_id": "capture-10",
      "candidate_id": "capture-10:echo:02"
     },
     {
      "session_id": "relocation-finite_panel_four_sources-1003-source-03",
      "capture_id": "capture-11",
      "candidate_id": "capture-11:echo:03"
     }
    ]
   },
   {
    "surface_id": "reflector-f64ad930b07a75af",
    "normal": [
     -0.6554671247150752,
     0.7552228868668295,
     -0.0011133599077043216
    ],
    "offset_m": 4.616459871703658,
    "support": [
     {
      "session_id": "relocation-finite_panel_four_sources-1003-source-00",
      "capture_id": "capture-01",
      "candidate_id": "capture-01:echo:04"
     },
     {
      "session_id": "relocation-finite_panel_four_sources-1003-source-00",
      "capture_id": "capture-02",
      "candidate_id": "capture-02:echo:05"
     },
     {
      "session_id": "relocation-finite_panel_four_sources-1003-source-00",
      "capture_id": "capture-03",
      "candidate_id": "capture-03:echo:01"
     },
     {
      "session_id": "relocation-finite_panel_four_sources-1003-source-00",
      "capture_id": "capture-04",
      "candidate_id": "capture-04:echo:04"
     },
     {
      "session_id": "relocation-finite_panel_four_sources-1003-source-00",
      "capture_id": "capture-05",
      "candidate_id": "capture-05:echo:06"
     },
     {
      "session_id": "relocation-finite_panel_four_sources-1003-source-00",
      "capture_id": "capture-06",
      "candidate_id": "capture-06:echo:06"
     },
     {
      "session_id": "relocation-finite_panel_four_sources-1003-source-00",
      "capture_id": "capture-07",
      "candidate_id": "capture-07:echo:04"
     },
     {
      "session_id": "relocation-finite_panel_four_sources-1003-source-00",
      "capture_id": "capture-08",
      "candidate_id": "capture-08:echo:02"
     },
     {
      "session_id": "relocation-finite_panel_four_sources-1003-source-00",
      "capture_id": "capture-09",
      "candidate_id": "capture-09:echo:04"
     },
     {
      "session_id": "relocation-finite_panel_four_sources-1003-source-00",
      "capture_id": "capture-10",
      "candidate_id": "capture-10:echo:01"
     },
     {
      "session_id": "relocation-finite_panel_four_sources-1003-source-00",
      "capture_id": "capture-11",
      "candidate_id": "capture-11:echo:05"
     },
     {
      "session_id": "relocation-finite_panel_four_sources-1003-source-01",
      "capture_id": "capture-01",
      "candidate_id": "capture-01:echo:04"
     },
     {
      "session_id": "relocation-finite_panel_four_sources-1003-source-01",
      "capture_id": "capture-03",
      "candidate_id": "capture-03:echo:01"
     },
     {
      "session_id": "relocation-finite_panel_four_sources-1003-source-01",
      "capture_id": "capture-04",
      "candidate_id": "capture-04:echo:04"
     },
     {
      "session_id": "relocation-finite_panel_four_sources-1003-source-01",
      "capture_id": "capture-05",
      "candidate_id": "capture-05:echo:06"
     },
     {
      "session_id": "relocation-finite_panel_four_sources-1003-source-01",
      "capture_id": "capture-06",
      "candidate_id": "capture-06:echo:06"
     },
     {
      "session_id": "relocation-finite_panel_four_sources-1003-source-01",
      "capture_id": "capture-07",
      "candidate_id": "capture-07:echo:03"
     },
     {
      "session_id": "relocation-finite_panel_four_sources-1003-source-01",
      "capture_id": "capture-08",
      "candidate_id": "capture-08:echo:02"
     },
     {
      "session_id": "relocation-finite_panel_four_sources-1003-source-01",
      "capture_id": "capture-09",
      "candidate_id": "capture-09:echo:04"
     },
     {
      "session_id": "relocation-finite_panel_four_sources-1003-source-01",
      "capture_id": "capture-10",
      "candidate_id": "capture-10:echo:01"
     },
     {
      "session_id": "relocation-finite_panel_four_sources-1003-source-01",
      "capture_id": "capture-11",
      "candidate_id": "capture-11:echo:05"
     },
     {
      "session_id": "relocation-finite_panel_four_sources-1003-source-02",
      "capture_id": "capture-01",
      "candidate_id": "capture-01:echo:03"
     },
     {
      "session_id": "relocation-finite_panel_four_sources-1003-source-02",
      "capture_id": "capture-02",
      "candidate_id": "capture-02:echo:05"
     },
     {
      "session_id": "relocation-finite_panel_four_sources-1003-source-02",
      "capture_id": "capture-03",
      "candidate_id": "capture-03:echo:01"
     },
     {
      "session_id": "relocation-finite_panel_four_sources-1003-source-02",
      "capture_id": "capture-05",
      "candidate_id": "capture-05:echo:05"
     },
     {
      "session_id": "relocation-finite_panel_four_sources-1003-source-02",
      "capture_id": "capture-06",
      "candidate_id": "capture-06:echo:05"
     },
     {
      "session_id": "relocation-finite_panel_four_sources-1003-source-02",
      "capture_id": "capture-07",
      "candidate_id": "capture-07:echo:03"
     },
     {
      "session_id": "relocation-finite_panel_four_sources-1003-source-02",
      "capture_id": "capture-08",
      "candidate_id": "capture-08:echo:02"
     },
     {
      "session_id": "relocation-finite_panel_four_sources-1003-source-02",
      "capture_id": "capture-10",
      "candidate_id": "capture-10:echo:01"
     },
     {
      "session_id": "relocation-finite_panel_four_sources-1003-source-02",
      "capture_id": "capture-11",
      "candidate_id": "capture-11:echo:05"
     },
     {
      "session_id": "relocation-finite_panel_four_sources-1003-source-03",
      "capture_id": "capture-00",
      "candidate_id": "capture-00:echo:03"
     },
     {
      "session_id": "relocation-finite_panel_four_sources-1003-source-03",
      "capture_id": "capture-01",
      "candidate_id": "capture-01:echo:03"
     },
     {
      "session_id": "relocation-finite_panel_four_sources-1003-source-03",
      "capture_id": "capture-02",
      "candidate_id": "capture-02:echo:05"
     },
     {
      "session_id": "relocation-finite_panel_four_sources-1003-source-03",
      "capture_id": "capture-03",
      "candidate_id": "capture-03:echo:02"
     },
     {
      "session_id": "relocation-finite_panel_four_sources-1003-source-03",
      "capture_id": "capture-04",
      "candidate_id": "capture-04:echo:04"
     },
     {
      "session_id": "relocation-finite_panel_four_sources-1003-source-03",
      "capture_id": "capture-05",
      "candidate_id": "capture-05:echo:05"
     },
     {
      "session_id": "relocation-finite_panel_four_sources-1003-source-03",
      "capture_id": "capture-06",
      "candidate_id": "capture-06:echo:06"
     },
     {
      "session_id": "relocation-finite_panel_four_sources-1003-source-03",
      "capture_id": "capture-07",
      "candidate_id": "capture-07:echo:02"
     },
     {
      "session_id": "relocation-finite_panel_four_sources-1003-source-03",
      "capture_id": "capture-08",
      "candidate_id": "capture-08:echo:02"
     },
     {
      "session_id": "relocation-finite_panel_four_sources-1003-source-03",
      "capture_id": "capture-09",
      "candidate_id": "capture-09:echo:04"
     },
     {
      "session_id": "relocation-finite_panel_four_sources-1003-source-03",
      "capture_id": "capture-10",
      "candidate_id": "capture-10:echo:01"
     },
     {
      "session_id": "relocation-finite_panel_four_sources-1003-source-03",
      "capture_id": "capture-11",
      "candidate_id": "capture-11:echo:05"
     }
    ]
   },
   {
    "surface_id": "reflector-3e089bb5085aac10",
    "normal": [
     0.7577398084239549,
     0.6525196816134091,
     -0.0069604480289235686
    ],
    "offset_m": 4.278459849377843,
    "support": [
     {
      "session_id": "relocation-finite_panel_four_sources-1003-source-00",
      "capture_id": "capture-00",
      "candidate_id": "capture-00:echo:04"
     },
     {
      "session_id": "relocation-finite_panel_four_sources-1003-source-00",
      "capture_id": "capture-01",
      "candidate_id": "capture-01:echo:06"
     },
     {
      "session_id": "relocation-finite_panel_four_sources-1003-source-00",
      "capture_id": "capture-03",
      "candidate_id": "capture-03:echo:05"
     },
     {
      "session_id": "relocation-finite_panel_four_sources-1003-source-00",
      "capture_id": "capture-04",
      "candidate_id": "capture-04:echo:06"
     },
     {
      "session_id": "relocation-finite_panel_four_sources-1003-source-00",
      "capture_id": "capture-05",
      "candidate_id": "capture-05:echo:05"
     },
     {
      "session_id": "relocation-finite_panel_four_sources-1003-source-00",
      "capture_id": "capture-06",
      "candidate_id": "capture-06:echo:05"
     },
     {
      "session_id": "relocation-finite_panel_four_sources-1003-source-00",
      "capture_id": "capture-07",
      "candidate_id": "capture-07:echo:06"
     },
     {
      "session_id": "relocation-finite_panel_four_sources-1003-source-00",
      "capture_id": "capture-08",
      "candidate_id": "capture-08:echo:05"
     },
     {
      "session_id": "relocation-finite_panel_four_sources-1003-source-00",
      "capture_id": "capture-09",
      "candidate_id": "capture-09:echo:06"
     },
     {
      "session_id": "relocation-finite_panel_four_sources-1003-source-00",
      "capture_id": "capture-10",
      "candidate_id": "capture-10:echo:05"
     },
     {
      "session_id": "relocation-finite_panel_four_sources-1003-source-00",
      "capture_id": "capture-11",
      "candidate_id": "capture-11:echo:06"
     },
     {
      "session_id": "relocation-finite_panel_four_sources-1003-source-01",
      "capture_id": "capture-00",
      "candidate_id": "capture-00:echo:03"
     },
     {
      "session_id": "relocation-finite_panel_four_sources-1003-source-01",
      "capture_id": "capture-01",
      "candidate_id": "capture-01:echo:05"
     },
     {
      "session_id": "relocation-finite_panel_four_sources-1003-source-01",
      "capture_id": "capture-03",
      "candidate_id": "capture-03:echo:05"
     },
     {
      "session_id": "relocation-finite_panel_four_sources-1003-source-01",
      "capture_id": "capture-04",
      "candidate_id": "capture-04:echo:06"
     },
     {
      "session_id": "relocation-finite_panel_four_sources-1003-source-01",
      "capture_id": "capture-05",
      "candidate_id": "capture-05:echo:05"
     },
     {
      "session_id": "relocation-finite_panel_four_sources-1003-source-01",
      "capture_id": "capture-06",
      "candidate_id": "capture-06:echo:05"
     },
     {
      "session_id": "relocation-finite_panel_four_sources-1003-source-01",
      "capture_id": "capture-07",
      "candidate_id": "capture-07:echo:05"
     },
     {
      "session_id": "relocation-finite_panel_four_sources-1003-source-01",
      "capture_id": "capture-08",
      "candidate_id": "capture-08:echo:05"
     },
     {
      "session_id": "relocation-finite_panel_four_sources-1003-source-01",
      "capture_id": "capture-09",
      "candidate_id": "capture-09:echo:05"
     },
     {
      "session_id": "relocation-finite_panel_four_sources-1003-source-01",
      "capture_id": "capture-10",
      "candidate_id": "capture-10:echo:04"
     },
     {
      "session_id": "relocation-finite_panel_four_sources-1003-source-01",
      "capture_id": "capture-11",
      "candidate_id": "capture-11:echo:04"
     },
     {
      "session_id": "relocation-finite_panel_four_sources-1003-source-02",
      "capture_id": "capture-00",
      "candidate_id": "capture-00:echo:04"
     },
     {
      "session_id": "relocation-finite_panel_four_sources-1003-source-02",
      "capture_id": "capture-01",
      "candidate_id": "capture-01:echo:06"
     },
     {
      "session_id": "relocation-finite_panel_four_sources-1003-source-02",
      "capture_id": "capture-02",
      "candidate_id": "capture-02:echo:06"
     },
     {
      "session_id": "relocation-finite_panel_four_sources-1003-source-02",
      "capture_id": "capture-03",
      "candidate_id": "capture-03:echo:06"
     },
     {
      "session_id": "relocation-finite_panel_four_sources-1003-source-02",
      "capture_id": "capture-05",
      "candidate_id": "capture-05:echo:06"
     },
     {
      "session_id": "relocation-finite_panel_four_sources-1003-source-02",
      "capture_id": "capture-06",
      "candidate_id": "capture-06:echo:06"
     },
     {
      "session_id": "relocation-finite_panel_four_sources-1003-source-02",
      "capture_id": "capture-07",
      "candidate_id": "capture-07:echo:06"
     },
     {
      "session_id": "relocation-finite_panel_four_sources-1003-source-02",
      "capture_id": "capture-08",
      "candidate_id": "capture-08:echo:06"
     },
     {
      "session_id": "relocation-finite_panel_four_sources-1003-source-02",
      "capture_id": "capture-10",
      "candidate_id": "capture-10:echo:06"
     },
     {
      "session_id": "relocation-finite_panel_four_sources-1003-source-02",
      "capture_id": "capture-11",
      "candidate_id": "capture-11:echo:06"
     },
     {
      "session_id": "relocation-finite_panel_four_sources-1003-source-03",
      "capture_id": "capture-00",
      "candidate_id": "capture-00:echo:06"
     },
     {
      "session_id": "relocation-finite_panel_four_sources-1003-source-03",
      "capture_id": "capture-01",
      "candidate_id": "capture-01:echo:05"
     },
     {
      "session_id": "relocation-finite_panel_four_sources-1003-source-03",
      "capture_id": "capture-03",
      "candidate_id": "capture-03:echo:06"
     },
     {
      "session_id": "relocation-finite_panel_four_sources-1003-source-03",
      "capture_id": "capture-04",
      "candidate_id": "capture-04:echo:06"
     },
     {
      "session_id": "relocation-finite_panel_four_sources-1003-source-03",
      "capture_id": "capture-05",
      "candidate_id": "capture-05:echo:04"
     },
     {
      "session_id": "relocation-finite_panel_four_sources-1003-source-03",
      "capture_id": "capture-06",
      "candidate_id": "capture-06:echo:05"
     },
     {
      "session_id": "relocation-finite_panel_four_sources-1003-source-03",
      "capture_id": "capture-07",
      "candidate_id": "capture-07:echo:04"
     },
     {
      "session_id": "relocation-finite_panel_four_sources-1003-source-03",
      "capture_id": "capture-08",
      "candidate_id": "capture-08:echo:06"
     },
     {
      "session_id": "relocation-finite_panel_four_sources-1003-source-03",
      "capture_id": "capture-09",
      "candidate_id": "capture-09:echo:06"
     },
     {
      "session_id": "relocation-finite_panel_four_sources-1003-source-03",
      "capture_id": "capture-10",
      "candidate_id": "capture-10:echo:05"
     },
     {
      "session_id": "relocation-finite_panel_four_sources-1003-source-03",
      "capture_id": "capture-11",
      "candidate_id": "capture-11:echo:06"
     }
    ]
   },
   {
    "surface_id": "reflector-8aa1fc64cc72d7f8",
    "normal": [
     -0.0008974444199754974,
     -0.0021156598037368026,
     0.9999973592850673
    ],
    "offset_m": 2.5117697227412816,
    "support": [
     {
      "session_id": "relocation-finite_panel_four_sources-1003-source-00",
      "capture_id": "capture-00",
      "candidate_id": "capture-00:echo:00"
     },
     {
      "session_id": "relocation-finite_panel_four_sources-1003-source-00",
      "capture_id": "capture-01",
      "candidate_id": "capture-01:echo:00"
     },
     {
      "session_id": "relocation-finite_panel_four_sources-1003-source-00",
      "capture_id": "capture-02",
      "candidate_id": "capture-02:echo:03"
     },
     {
      "session_id": "relocation-finite_panel_four_sources-1003-source-00",
      "capture_id": "capture-03",
      "candidate_id": "capture-03:echo:02"
     },
     {
      "session_id": "relocation-finite_panel_four_sources-1003-source-00",
      "capture_id": "capture-04",
      "candidate_id": "capture-04:echo:02"
     },
     {
      "session_id": "relocation-finite_panel_four_sources-1003-source-00",
      "capture_id": "capture-05",
      "candidate_id": "capture-05:echo:00"
     },
     {
      "session_id": "relocation-finite_panel_four_sources-1003-source-00",
      "capture_id": "capture-06",
      "candidate_id": "capture-06:echo:01"
     },
     {
      "session_id": "relocation-finite_panel_four_sources-1003-source-00",
      "capture_id": "capture-07",
      "candidate_id": "capture-07:echo:02"
     },
     {
      "session_id": "relocation-finite_panel_four_sources-1003-source-00",
      "capture_id": "capture-09",
      "candidate_id": "capture-09:echo:03"
     },
     {
      "session_id": "relocation-finite_panel_four_sources-1003-source-00",
      "capture_id": "capture-11",
      "candidate_id": "capture-11:echo:02"
     },
     {
      "session_id": "relocation-finite_panel_four_sources-1003-source-01",
      "capture_id": "capture-01",
      "candidate_id": "capture-01:echo:00"
     },
     {
      "session_id": "relocation-finite_panel_four_sources-1003-source-01",
      "capture_id": "capture-03",
      "candidate_id": "capture-03:echo:02"
     },
     {
      "session_id": "relocation-finite_panel_four_sources-1003-source-01",
      "capture_id": "capture-04",
      "candidate_id": "capture-04:echo:02"
     },
     {
      "session_id": "relocation-finite_panel_four_sources-1003-source-01",
      "capture_id": "capture-05",
      "candidate_id": "capture-05:echo:00"
     },
     {
      "session_id": "relocation-finite_panel_four_sources-1003-source-01",
      "capture_id": "capture-06",
      "candidate_id": "capture-06:echo:01"
     },
     {
      "session_id": "relocation-finite_panel_four_sources-1003-source-01",
      "capture_id": "capture-07",
      "candidate_id": "capture-07:echo:01"
     },
     {
      "session_id": "relocation-finite_panel_four_sources-1003-source-01",
      "capture_id": "capture-08",
      "candidate_id": "capture-08:echo:03"
     },
     {
      "session_id": "relocation-finite_panel_four_sources-1003-source-01",
      "capture_id": "capture-09",
      "candidate_id": "capture-09:echo:02"
     },
     {
      "session_id": "relocation-finite_panel_four_sources-1003-source-01",
      "capture_id": "capture-10",
      "candidate_id": "capture-10:echo:03"
     },
     {
      "session_id": "relocation-finite_panel_four_sources-1003-source-01",
      "capture_id": "capture-11",
      "candidate_id": "capture-11:echo:02"
     },
     {
      "session_id": "relocation-finite_panel_four_sources-1003-source-02",
      "capture_id": "capture-01",
      "candidate_id": "capture-01:echo:00"
     },
     {
      "session_id": "relocation-finite_panel_four_sources-1003-source-02",
      "capture_id": "capture-02",
      "candidate_id": "capture-02:echo:03"
     },
     {
      "session_id": "relocation-finite_panel_four_sources-1003-source-02",
      "capture_id": "capture-03",
      "candidate_id": "capture-03:echo:03"
     },
     {
      "session_id": "relocation-finite_panel_four_sources-1003-source-02",
      "capture_id": "capture-04",
      "candidate_id": "capture-04:echo:02"
     },
     {
      "session_id": "relocation-finite_panel_four_sources-1003-source-02",
      "capture_id": "capture-05",
      "candidate_id": "capture-05:echo:00"
     },
     {
      "session_id": "relocation-finite_panel_four_sources-1003-source-02",
      "capture_id": "capture-06",
      "candidate_id": "capture-06:echo:00"
     },
     {
      "session_id": "relocation-finite_panel_four_sources-1003-source-02",
      "capture_id": "capture-07",
      "candidate_id": "capture-07:echo:02"
     },
     {
      "session_id": "relocation-finite_panel_four_sources-1003-source-02",
      "capture_id": "capture-08",
      "candidate_id": "capture-08:echo:03"
     },
     {
      "session_id": "relocation-finite_panel_four_sources-1003-source-02",
      "capture_id": "capture-10",
      "candidate_id": "capture-10:echo:03"
     },
     {
      "session_id": "relocation-finite_panel_four_sources-1003-source-02",
      "capture_id": "capture-11",
      "candidate_id": "capture-11:echo:01"
     },
     {
      "session_id": "relocation-finite_panel_four_sources-1003-source-03",
      "capture_id": "capture-00",
      "candidate_id": "capture-00:echo:00"
     },
     {
      "session_id": "relocation-finite_panel_four_sources-1003-source-03",
      "capture_id": "capture-01",
      "candidate_id": "capture-01:echo:00"
     },
     {
      "session_id": "relocation-finite_panel_four_sources-1003-source-03",
      "capture_id": "capture-02",
      "candidate_id": "capture-02:echo:02"
     },
     {
      "session_id": "relocation-finite_panel_four_sources-1003-source-03",
      "capture_id": "capture-03",
      "candidate_id": "capture-03:echo:01"
     },
     {
      "session_id": "relocation-finite_panel_four_sources-1003-source-03",
      "capture_id": "capture-04",
      "candidate_id": "capture-04:echo:01"
     },
     {
      "session_id": "relocation-finite_panel_four_sources-1003-source-03",
      "capture_id": "capture-05",
      "candidate_id": "capture-05:echo:00"
     },
     {
      "session_id": "relocation-finite_panel_four_sources-1003-source-03",
      "capture_id": "capture-06",
      "candidate_id": "capture-06:echo:00"
     },
     {
      "session_id": "relocation-finite_panel_four_sources-1003-source-03",
      "capture_id": "capture-08",
      "candidate_id": "capture-08:echo:03"
     },
     {
      "session_id": "relocation-finite_panel_four_sources-1003-source-03",
      "capture_id": "capture-09",
      "candidate_id": "capture-09:echo:02"
     },
     {
      "session_id": "relocation-finite_panel_four_sources-1003-source-03",
      "capture_id": "capture-10",
      "candidate_id": "capture-10:echo:03"
     },
     {
      "session_id": "relocation-finite_panel_four_sources-1003-source-03",
      "capture_id": "capture-11",
      "candidate_id": "capture-11:echo:00"
     }
    ]
   },
   {
    "surface_id": "reflector-6eb734ca08ab703c",
    "normal": [
     0.7569353502483636,
     0.6534775553859138,
     -0.003995015799368337
    ],
    "offset_m": 3.3839772744912326,
    "support": [
     {
      "session_id": "relocation-finite_panel_four_sources-1003-source-00",
      "capture_id": "capture-00",
      "candidate_id": "capture-00:echo:03"
     },
     {
      "session_id": "relocation-finite_panel_four_sources-1003-source-00",
      "capture_id": "capture-01",
      "candidate_id": "capture-01:echo:05"
     },
     {
      "session_id": "relocation-finite_panel_four_sources-1003-source-00",
      "capture_id": "capture-02",
      "candidate_id": "capture-02:echo:04"
     },
     {
      "session_id": "relocation-finite_panel_four_sources-1003-source-00",
      "capture_id": "capture-03",
      "candidate_id": "capture-03:echo:04"
     },
     {
      "session_id": "relocation-finite_panel_four_sources-1003-source-00",
      "capture_id": "capture-04",
      "candidate_id": "capture-04:echo:05"
     },
     {
      "session_id": "relocation-finite_panel_four_sources-1003-source-00",
      "capture_id": "capture-05",
      "candidate_id": "capture-05:echo:04"
     },
     {
      "session_id": "relocation-finite_panel_four_sources-1003-source-00",
      "capture_id": "capture-06",
      "candidate_id": "capture-06:echo:04"
     },
     {
      "session_id": "relocation-finite_panel_four_sources-1003-source-00",
      "capture_id": "capture-07",
      "candidate_id": "capture-07:echo:05"
     },
     {
      "session_id": "relocation-finite_panel_four_sources-1003-source-00",
      "capture_id": "capture-08",
      "candidate_id": "capture-08:echo:04"
     },
     {
      "session_id": "relocation-finite_panel_four_sources-1003-source-00",
      "capture_id": "capture-09",
      "candidate_id": "capture-09:echo:05"
     },
     {
      "session_id": "relocation-finite_panel_four_sources-1003-source-00",
      "capture_id": "capture-10",
      "candidate_id": "capture-10:echo:04"
     },
     {
      "session_id": "relocation-finite_panel_four_sources-1003-source-00",
      "capture_id": "capture-11",
      "candidate_id": "capture-11:echo:04"
     },
     {
      "session_id": "relocation-finite_panel_four_sources-1003-source-01",
      "capture_id": "capture-04",
      "candidate_id": "capture-04:echo:05"
     },
     {
      "session_id": "relocation-finite_panel_four_sources-1003-source-01",
      "capture_id": "capture-05",
      "candidate_id": "capture-05:echo:03"
     },
     {
      "session_id": "relocation-finite_panel_four_sources-1003-source-01",
      "capture_id": "capture-06",
      "candidate_id": "capture-06:echo:03"
     },
     {
      "session_id": "relocation-finite_panel_four_sources-1003-source-01",
      "capture_id": "capture-07",
      "candidate_id": "capture-07:echo:04"
     },
     {
      "session_id": "relocation-finite_panel_four_sources-1003-source-01",
      "capture_id": "capture-08",
      "candidate_id": "capture-08:echo:04"
     },
     {
      "session_id": "relocation-finite_panel_four_sources-1003-source-01",
      "capture_id": "capture-09",
      "candidate_id": "capture-09:echo:03"
     },
     {
      "session_id": "relocation-finite_panel_four_sources-1003-source-02",
      "capture_id": "capture-00",
      "candidate_id": "capture-00:echo:02"
     },
     {
      "session_id": "relocation-finite_panel_four_sources-1003-source-02",
      "capture_id": "capture-01",
      "candidate_id": "capture-01:echo:05"
     },
     {
      "session_id": "relocation-finite_panel_four_sources-1003-source-02",
      "capture_id": "capture-02",
      "candidate_id": "capture-02:echo:04"
     },
     {
      "session_id": "relocation-finite_panel_four_sources-1003-source-02",
      "capture_id": "capture-03",
      "candidate_id": "capture-03:echo:04"
     },
     {
      "session_id": "relocation-finite_panel_four_sources-1003-source-02",
      "capture_id": "capture-04",
      "candidate_id": "capture-04:echo:04"
     },
     {
      "session_id": "relocation-finite_panel_four_sources-1003-source-02",
      "capture_id": "capture-05",
      "candidate_id": "capture-05:echo:04"
     },
     {
      "session_id": "relocation-finite_panel_four_sources-1003-source-02",
      "capture_id": "capture-06",
      "candidate_id": "capture-06:echo:04"
     },
     {
      "session_id": "relocation-finite_panel_four_sources-1003-source-02",
      "capture_id": "capture-07",
      "candidate_id": "capture-07:echo:05"
     },
     {
      "session_id": "relocation-finite_panel_four_sources-1003-source-02",
      "capture_id": "capture-08",
      "candidate_id": "capture-08:echo:05"
     },
     {
      "session_id": "relocation-finite_panel_four_sources-1003-source-02",
      "capture_id": "capture-10",
      "candidate_id": "capture-10:echo:04"
     },
     {
      "session_id": "relocation-finite_panel_four_sources-1003-source-02",
      "capture_id": "capture-11",
      "candidate_id": "capture-11:echo:04"
     },
     {
      "session_id": "relocation-finite_panel_four_sources-1003-source-03",
      "capture_id": "capture-00",
      "candidate_id": "capture-00:echo:05"
     },
     {
      "session_id": "relocation-finite_panel_four_sources-1003-source-03",
      "capture_id": "capture-01",
      "candidate_id": "capture-01:echo:04"
     },
     {
      "session_id": "relocation-finite_panel_four_sources-1003-source-03",
      "capture_id": "capture-02",
      "candidate_id": "capture-02:echo:04"
     },
     {
      "session_id": "relocation-finite_panel_four_sources-1003-source-03",
      "capture_id": "capture-03",
      "candidate_id": "capture-03:echo:04"
     },
     {
      "session_id": "relocation-finite_panel_four_sources-1003-source-03",
      "capture_id": "capture-04",
      "candidate_id": "capture-04:echo:05"
     },
     {
      "session_id": "relocation-finite_panel_four_sources-1003-source-03",
      "capture_id": "capture-06",
      "candidate_id": "capture-06:echo:04"
     },
     {
      "session_id": "relocation-finite_panel_four_sources-1003-source-03",
      "capture_id": "capture-07",
      "candidate_id": "capture-07:echo:03"
     },
     {
      "session_id": "relocation-finite_panel_four_sources-1003-source-03",
      "capture_id": "capture-08",
      "candidate_id": "capture-08:echo:05"
     },
     {
      "session_id": "relocation-finite_panel_four_sources-1003-source-03",
      "capture_id": "capture-09",
      "candidate_id": "capture-09:echo:05"
     },
     {
      "session_id": "relocation-finite_panel_four_sources-1003-source-03",
      "capture_id": "capture-11",
      "candidate_id": "capture-11:echo:04"
     }
    ]
   },
   {
    "surface_id": "reflector-7a1c4e76897a3cab",
    "normal": [
     -0.6566924919305761,
     0.7541580882194411,
     -0.0007409556044793742
    ],
    "offset_m": -0.08676523187257687,
    "support": [
     {
      "session_id": "relocation-finite_panel_four_sources-1003-source-00",
      "capture_id": "capture-00",
      "candidate_id": "capture-00:echo:02"
     },
     {
      "session_id": "relocation-finite_panel_four_sources-1003-source-00",
      "capture_id": "capture-01",
      "candidate_id": "capture-01:echo:03"
     },
     {
      "session_id": "relocation-finite_panel_four_sources-1003-source-00",
      "capture_id": "capture-02",
      "candidate_id": "capture-02:echo:01"
     },
     {
      "session_id": "relocation-finite_panel_four_sources-1003-source-00",
      "capture_id": "capture-03",
      "candidate_id": "capture-03:echo:03"
     },
     {
      "session_id": "relocation-finite_panel_four_sources-1003-source-00",
      "capture_id": "capture-04",
      "candidate_id": "capture-04:echo:03"
     },
     {
      "session_id": "relocation-finite_panel_four_sources-1003-source-00",
      "capture_id": "capture-05",
      "candidate_id": "capture-05:echo:01"
     },
     {
      "session_id": "relocation-finite_panel_four_sources-1003-source-00",
      "capture_id": "capture-06",
      "candidate_id": "capture-06:echo:00"
     },
     {
      "session_id": "relocation-finite_panel_four_sources-1003-source-00",
      "capture_id": "capture-07",
      "candidate_id": "capture-07:echo:03"
     },
     {
      "session_id": "relocation-finite_panel_four_sources-1003-source-00",
      "capture_id": "capture-08",
      "candidate_id": "capture-08:echo:03"
     },
     {
      "session_id": "relocation-finite_panel_four_sources-1003-source-00",
      "capture_id": "capture-09",
      "candidate_id": "capture-09:echo:02"
     },
     {
      "session_id": "relocation-finite_panel_four_sources-1003-source-00",
      "capture_id": "capture-10",
      "candidate_id": "capture-10:echo:03"
     },
     {
      "session_id": "relocation-finite_panel_four_sources-1003-source-00",
      "capture_id": "capture-11",
      "candidate_id": "capture-11:echo:00"
     },
     {
      "session_id": "relocation-finite_panel_four_sources-1003-source-01",
      "capture_id": "capture-00",
      "candidate_id": "capture-00:echo:01"
     },
     {
      "session_id": "relocation-finite_panel_four_sources-1003-source-01",
      "capture_id": "capture-01",
      "candidate_id": "capture-01:echo:03"
     },
     {
      "session_id": "relocation-finite_panel_four_sources-1003-source-01",
      "capture_id": "capture-02",
      "candidate_id": "capture-02:echo:01"
     },
     {
      "session_id": "relocation-finite_panel_four_sources-1003-source-01",
      "capture_id": "capture-03",
      "candidate_id": "capture-03:echo:03"
     },
     {
      "session_id": "relocation-finite_panel_four_sources-1003-source-01",
      "capture_id": "capture-04",
      "candidate_id": "capture-04:echo:03"
     },
     {
      "session_id": "relocation-finite_panel_four_sources-1003-source-01",
      "capture_id": "capture-05",
      "candidate_id": "capture-05:echo:01"
     },
     {
      "session_id": "relocation-finite_panel_four_sources-1003-source-01",
      "capture_id": "capture-06",
      "candidate_id": "capture-06:echo:00"
     },
     {
      "session_id": "relocation-finite_panel_four_sources-1003-source-01",
      "capture_id": "capture-11",
      "candidate_id": "capture-11:echo:00"
     },
     {
      "session_id": "relocation-finite_panel_four_sources-1003-source-02",
      "capture_id": "capture-00",
      "candidate_id": "capture-00:echo:03"
     },
     {
      "session_id": "relocation-finite_panel_four_sources-1003-source-02",
      "capture_id": "capture-01",
      "candidate_id": "capture-01:echo:04"
     },
     {
      "session_id": "relocation-finite_panel_four_sources-1003-source-02",
      "capture_id": "capture-02",
      "candidate_id": "capture-02:echo:01"
     },
     {
      "session_id": "relocation-finite_panel_four_sources-1003-source-02",
      "capture_id": "capture-03",
      "candidate_id": "capture-03:echo:05"
     },
     {
      "session_id": "relocation-finite_panel_four_sources-1003-source-02",
      "capture_id": "capture-04",
      "candidate_id": "capture-04:echo:03"
     },
     {
      "session_id": "relocation-finite_panel_four_sources-1003-source-02",
      "capture_id": "capture-05",
      "candidate_id": "capture-05:echo:01"
     },
     {
      "session_id": "relocation-finite_panel_four_sources-1003-source-02",
      "capture_id": "capture-06",
      "candidate_id": "capture-06:echo:01"
     },
     {
      "session_id": "relocation-finite_panel_four_sources-1003-source-02",
      "capture_id": "capture-07",
      "candidate_id": "capture-07:echo:04"
     },
     {
      "session_id": "relocation-finite_panel_four_sources-1003-source-02",
      "capture_id": "capture-08",
      "candidate_id": "capture-08:echo:04"
     },
     {
      "session_id": "relocation-finite_panel_four_sources-1003-source-02",
      "capture_id": "capture-10",
      "candidate_id": "capture-10:echo:05"
     },
     {
      "session_id": "relocation-finite_panel_four_sources-1003-source-02",
      "capture_id": "capture-11",
      "candidate_id": "capture-11:echo:02"
     },
     {
      "session_id": "relocation-finite_panel_four_sources-1003-source-03",
      "capture_id": "capture-00",
      "candidate_id": "capture-00:echo:04"
     },
     {
      "session_id": "relocation-finite_panel_four_sources-1003-source-03",
      "capture_id": "capture-02",
      "candidate_id": "capture-02:echo:01"
     },
     {
      "session_id": "relocation-finite_panel_four_sources-1003-source-03",
      "capture_id": "capture-03",
      "candidate_id": "capture-03:echo:05"
     },
     {
      "session_id": "relocation-finite_panel_four_sources-1003-source-03",
      "capture_id": "capture-04",
      "candidate_id": "capture-04:echo:03"
     },
     {
      "session_id": "relocation-finite_panel_four_sources-1003-source-03",
      "capture_id": "capture-05",
      "candidate_id": "capture-05:echo:01"
     },
     {
      "session_id": "relocation-finite_panel_four_sources-1003-source-03",
      "capture_id": "capture-06",
      "candidate_id": "capture-06:echo:01"
     },
     {
      "session_id": "relocation-finite_panel_four_sources-1003-source-03",
      "capture_id": "capture-08",
      "candidate_id": "capture-08:echo:04"
     },
     {
      "session_id": "relocation-finite_panel_four_sources-1003-source-03",
      "capture_id": "capture-09",
      "candidate_id": "capture-09:echo:03"
     },
     {
      "session_id": "relocation-finite_panel_four_sources-1003-source-03",
      "capture_id": "capture-10",
      "candidate_id": "capture-10:echo:04"
     },
     {
      "session_id": "relocation-finite_panel_four_sources-1003-source-03",
      "capture_id": "capture-11",
      "candidate_id": "capture-11:echo:01"
     }
    ]
   }
  ]
 }
}
''')
