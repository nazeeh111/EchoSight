import copy,unittest
import numpy as np
from echosight.timing_bootstrap import validate,timing_variance
from echosight.inference import _covariance

class TimingCovarianceTests(unittest.TestCase):
 def observation(self):
  return dict(candidates=[dict(candidate_id='a',delay_s=.01,delay_std_s=.001),dict(candidate_id='b',delay_s=.02,delay_std_s=.002)],direct_std_s=.003,clock=dict(alpha=1.,alpha_std=.004),receiver_position_std_m=0.,candidate_delay_covariance=dict(candidate_ids=['b','a'],covariance_s2=[[4e-8,1e-8],[1e-8,2e-8]],includes_direct_reference=True,includes_relative_clock=True,includes_empirical_direct_kernel=True,includes_amplitude_nuisance=True))
 def test_components_not_double_counted_and_ordered_ids(self):
  o=self.observation();s=np.array([0.,0.,1.]);r=np.array([[1.,.5,1.]])
  rows=[dict(o=o,peaks=o['candidates'],t=np.array([.01,.02]))]
  qs=np.array([[0.,3.,1.],[0.,0.,5.]])
  session=dict(source_position_std_m=0,sound_speed_std_m_s=0,source_clock_std_ppm=0)
  _,C,_=_covariance(qs,[(0,0,0),(1,0,1)],s,r,343.,rows,session)
  np.testing.assert_allclose(C,[[2e-8,1e-8],[1e-8,4e-8]],rtol=0,atol=1e-20)
  self.assertAlmostEqual(timing_variance(o,o['candidates'][0]),2e-8)
 def test_legacy_calibration_variance_matches_inference(self):
  o=self.observation();del o['candidate_delay_covariance'];c=o['candidates'][0]
  self.assertAlmostEqual(timing_variance(o,c),.001**2+.003**2+(.01*.004)**2)
 def test_full_repetition_covariance_retains_named_components(self):
  from tests.test_joint_kernel import JointKernelTests
  from echosight.signals import process_recording
  from echosight.timing_bootstrap import estimate
  y,fs,p=JointKernelTests().waveform();y+=np.random.default_rng(919).normal(0,.02,len(y))
  o=process_recording(y,fs,p,'r',estimator='joint_kernel')
  block=estimate(y,fs,p,o,process_recording,draws=15)
  self.assertEqual(block['status'],'estimated',block)
  o['candidate_delay_covariance']=block;_,C=validate(o)
  self.assertGreater(np.linalg.eigvalsh(C).min(),0)
  floor=block['declared_timing_floor_s']
  np.testing.assert_allclose(C-np.array(block['noise_covariance_s2']),floor**2*(np.eye(len(C))+np.ones_like(C)),atol=1e-22)
  self.assertEqual(block['coverage_status'],'development_unqualified')
 def test_bootstrap_failure_and_cancellation_do_not_return_covariance(self):
  from tests.test_joint_kernel import JointKernelTests
  from echosight.signals import process_recording
  from echosight.timing_bootstrap import estimate
  y,fs,p=JointKernelTests().waveform();o=process_recording(y,fs,p,'r',estimator='joint_kernel')
  failed=estimate(y,fs,p,o,lambda *a,**k:dict(status='rejected'),draws=15)
  self.assertEqual(failed['status'],'unstable');self.assertNotIn('covariance_s2',failed)
  cancelled=estimate(y,fs,p,o,process_recording,draws=15,cancel=lambda:True)
  self.assertEqual(cancelled['status'],'cancelled');self.assertNotIn('covariance_s2',cancelled)
  with self.assertRaises(ValueError):estimate(y,fs,p,o,process_recording,draws=100000)
 def test_matrix_validation(self):
  o=self.observation();validate(o)
  for replacement in [[[1.,2.],[2.,1.]],[[1e-20,2e-20],[2e-20,1e-20]],[[1.,0.],[1.,1.]],[[float('nan'),0.],[0.,1.]],[[1.]]]:
   b=copy.deepcopy(o);b['candidate_delay_covariance']['covariance_s2']=replacement
   with self.assertRaises(ValueError):validate(b)
  for key,value in [('includes_direct_reference',False),('includes_relative_clock',False),('candidate_ids',['a','a'])]:
   b=copy.deepcopy(o);b['candidate_delay_covariance'][key]=value
   with self.assertRaises(ValueError):validate(b)
if __name__=='__main__':unittest.main()
