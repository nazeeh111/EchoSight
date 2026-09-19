import unittest
import numpy as np
from echosight.signals import generate_probe,process_recording
class JointKernelTests(unittest.TestCase):
 def waveform(self,gap=.00025):
  x,p=generate_probe();fs=48000;t=np.arange(len(x))/fs;u=np.arange(len(x)+fs//3)/fs
  y=.4*np.interp(u-.06,t,x,left=0,right=0)+.2*np.interp(u-.072,t,x,left=0,right=0)+.16*np.interp(u-.072-gap,t,x,left=0,right=0)
  return y,fs,p
 def test_overlap_and_repetition_support(self):
  y,fs,p=self.waveform();r=process_recording(y,fs,p,'r',estimator='joint_kernel');self.assertEqual(r['status'],'ok')
  self.assertEqual(len(r['candidates']),2,r['candidates'])
  for c,d in zip(r['candidates'],[.012,.01225]):
   self.assertLess(abs(c['delay_s']-d),.00005);self.assertEqual(c['repeat_support'],7)
 def test_unknown_option_before_signal_work(self):
  with self.assertRaisesRegex(ValueError,'unsupported response estimator'):
   process_recording(object(),48000,{},'r',estimator='unknown')
 def test_cancel_during_joint_fit(self):
  y,fs,p=self.waveform();count=0
  def cancel():
   nonlocal count
   count+=1;return count>14
  r=process_recording(y,fs,p,'r',estimator='joint_kernel',cancel=cancel)
  self.assertEqual(r['status'],'rejected');self.assertEqual(r['diagnostics'][-1]['code'],'cancelled')
 def test_echo_in_only_four_repetitions_is_not_supported(self):
  x,p=generate_probe();fs=48000;t=np.arange(len(x))/fs;u=np.arange(len(x)+fs//3)/fs
  partial=x.copy();partial[p['pilot_start_samples'][4]:]=0
  y=.4*np.interp(u-.06,t,x,left=0,right=0)+.2*np.interp(u-.072,t,partial,left=0,right=0)
  r=process_recording(y,fs,p,'r',estimator='joint_kernel')
  self.assertEqual(r['candidates'],[],r['candidates'])
if __name__=='__main__':unittest.main()
