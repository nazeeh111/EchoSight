"""Empirical source calibration enters through actual quantized recordings."""
import copy
import tempfile
import unittest
from pathlib import Path
import numpy as np
from scipy.io.wavfile import write


class CalibrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from echosight.signals import generate_probe
        cls.temp=tempfile.TemporaryDirectory();cls.root=Path(cls.temp.name)
        rng=np.random.default_rng(81);x,probe=generate_probe();fs=probe['sample_rate_hz'];xt=np.arange(len(x))/fs
        cls.true_source=np.array([1.57,-.04,1.32]);cls.points=rng.uniform([.5,-3.,.4],[4.,3.,2.7],(20,3))
        cls.session=dict(schema_version='1.0',session_id='calibration-test',source_position_m=[1.5,0.,1.3],probe=probe,captures=[])
        cls.bad=copy.deepcopy(cls.session)
        for i,r in enumerate(cls.points):
            q=cls.true_source.copy();q[0]*=-1
            alpha=1+rng.uniform(-300,300)*1e-6;offset=rng.uniform(.04,.10)
            t=(np.arange(round((len(x)/fs+.2)*fs))/fs-offset)/alpha
            direct=np.linalg.norm(r-cls.true_source)/346.;reflected=np.linalg.norm(r-q)/346.
            noise=rng.normal(0,.00015,len(t))
            for mode,session in [('good',cls.session),('bad',cls.bad)]:
                bias=.001 if mode=='bad' and i>=16 else 0.
                y=.55*np.interp(t-direct,xt,x,left=0,right=0)+.2*np.interp(t-reflected-bias,xt,x,left=0,right=0)+noise
                path=cls.root/f'{mode}-{i}.wav';write(path,fs,np.round(y*32767).astype(np.int16))
                session['captures'].append(dict(capture_id=str(i),receiver_position_m=r.tolist(),receiver_position_std_m=.003,recording_path=str(path),provenance='simulated'))
        cls.reference=dict(normal=[1.,0.,0.],offset_m=0.,offset_std_m=.003,normal_std_rad=.0005,training_capture_ids=[str(i) for i in range(16)],validation_capture_ids=[str(i) for i in range(16,20)])

    @classmethod
    def tearDownClass(cls):cls.temp.cleanup()

    def test_raw_calibration_improves_independent_pose_predictions(self):
        from echosight.calibration import calibrate_reference
        out=calibrate_reference(self.session,self.reference)
        self.assertEqual(out['status'],'calibration_proposal')
        self.assertFalse(out['physical_validation'])
        self.assertLess(out['validation_fitted_rms_s'],out['validation_nominal_rms_s']/20)
        self.assertLess(np.linalg.norm(np.asarray(out['calibration']['source_position_m'])-self.true_source),.005)
        self.assertLess(abs(out['calibration']['effective_speed_m_s']-346.),.5)
        covariance=np.asarray(out['calibration']['source_effective_speed_covariance'])
        self.assertEqual(covariance.shape,(4,4));self.assertGreater(np.min(np.linalg.eigvalsh(covariance)),0)
        self.assertGreater(np.linalg.norm(covariance[:3,3]),0)
        self.assertNotIn('sound_speed_m_s',out['calibration'])
        self.assertNotIn('source_clock_scale',out['calibration'])
        self.assertEqual(len(out['evidence']),20)

    def test_validation_model_shift_is_not_silently_refitted(self):
        from echosight.calibration import calibrate_reference
        out=calibrate_reference(self.bad,self.reference)
        self.assertEqual(out['status'],'rejected')
        self.assertNotIn('calibration',out)
        self.assertTrue(out['diagnostics'])

    def test_shared_reference_uncertainty_is_not_divided_by_capture_count(self):
        from echosight.calibration import calibrate_reference
        a=calibrate_reference(self.session,self.reference)
        ref=dict(self.reference,offset_std_m=.02)
        b=calibrate_reference(self.session,ref)
        self.assertEqual(b['status'],'calibration_proposal')
        ca=np.array(a['calibration']['source_effective_speed_covariance']);cb=np.array(b['calibration']['source_effective_speed_covariance'])
        self.assertGreater(cb[0,0],ca[0,0]*2)
        self.assertGreater(np.trace(cb),np.trace(ca))

    def test_missing_uncertainty_invalid_partition_and_degenerate_poses(self):
        from echosight.calibration import calibrate_reference
        ref=dict(self.reference);del ref['offset_std_m']
        with self.assertRaises(ValueError):calibrate_reference(self.session,ref)
        ref=dict(self.reference,validation_capture_ids=['0','17','18','19'])
        with self.assertRaises(ValueError):calibrate_reference(self.session,ref)
        session=copy.deepcopy(self.session)
        for c in session['captures']:c['receiver_position_m'][2]=1.3
        self.assertEqual(calibrate_reference(session,self.reference)['diagnostics'],['nonspatial_calibration_positions'])
        session=copy.deepcopy(self.session);session['captures'][16]['receiver_position_m']=session['captures'][0]['receiver_position_m']
        with self.assertRaises(ValueError):calibrate_reference(session,self.reference)

    def test_reference_and_relative_clock_timing_uncertainty_is_propagated(self):
        from unittest.mock import patch
        from echosight.calibration import calibrate_reference
        from echosight.pipeline import process_session
        observations=process_session(self.session)
        covariances=[]
        for direct,rate in [(0.,0.),(.00008,.0001)]:
            data=copy.deepcopy(observations)
            for observation in data['observations']:
                observation['direct_std_s']=direct
                observation['clock']['alpha_std']=rate
            with patch('echosight.pipeline.process_session',return_value=data):
                out=calibrate_reference(self.session,self.reference)
            self.assertEqual(out['status'],'calibration_proposal')
            covariances.append(np.array(out['calibration']['source_effective_speed_covariance']))
        self.assertGreater(np.trace(covariances[1]),np.trace(covariances[0])*2)

    def test_validation_cannot_reuse_one_pose_or_raw_recording(self):
        from echosight.calibration import calibrate_reference
        same=copy.deepcopy(self.session)
        for capture in same['captures'][17:]:
            capture['receiver_position_m']=same['captures'][16]['receiver_position_m']
            capture['recording_path']=same['captures'][16]['recording_path']
        with self.assertRaises(ValueError):calibrate_reference(same,self.reference)
        from unittest.mock import patch
        from echosight.pipeline import process_session
        data=process_session(self.session)
        data['observations'][-1]['recording_sha256']=data['observations'][-2]['recording_sha256']
        with patch('echosight.pipeline.process_session',return_value=data):
            out=calibrate_reference(self.session,self.reference)
        self.assertEqual(out['status'],'rejected')
        self.assertEqual(out['diagnostics'][-1]['code'],'reference_recordings_reused')


if __name__=='__main__':unittest.main()
