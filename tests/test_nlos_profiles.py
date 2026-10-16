"""Native threshold decisions must not be inferred from display bytes."""
import json
import unittest
import numpy as np
from echosight import nlos_display as display

class NativeThresholdProfiles(unittest.TestCase):
    def diagnostics(self, volume, spacing=.001372):
        self.assertTrue(callable(getattr(display,'threshold_diagnostics',None)), 'native threshold diagnostic computation is missing')
        return display.threshold_diagnostics(volume,spacing)

    def test_strict_native_crossing_differs_from_rounded_display(self):
        v=np.zeros((4,2,3));v[:,0,0]=[0,.99999,1.00001,2];v[3,0,1]=4.5
        d=self.diagnostics(v)
        self.assertEqual(d['divisors'],[3,4,4.5,5,6])
        self.assertEqual(d['first_crossing_volume_indices'][2][1][2],2)
        quantized=np.rint(v[:,0,0]/v.max()*255)
        self.assertEqual(int(np.flatnonzero(quantized>255/4.5)[0]),1)
        v[:,0,0]=[0,1,1,2]
        self.assertEqual(self.diagnostics(v)['first_crossing_volume_indices'][2][1][2],3)

    def test_first_maximum_ties_below_threshold_and_unknowns(self):
        v=np.zeros((4,2,3));v[3,0,1]=4.5;v[:,1,0]=[0,2,2,0];v[:,1,1]=.3
        d=self.diagnostics(v)
        self.assertEqual(d['axial_maximum_volume_indices'][0][2],1)
        self.assertEqual(d['axial_maximum_amplitudes'][0][2],2)
        self.assertTrue(all(grid[0][1] is None for grid in d['first_crossing_volume_indices']))
        self.assertEqual(d['axial_maximum_volume_indices'][0][1],0)
        # Missing native crossings must serialize as null, never NaN or index zero.
        self.assertIn('null',json.dumps(d,allow_nan=False))

    def test_all_zero_profile_has_no_crossing_despite_argmax_zero(self):
        d=self.diagnostics(np.zeros((8,2,3)))
        self.assertTrue(all(value is None for grid in d['first_crossing_volume_indices'] for row in grid for value in row))
        self.assertEqual(d['axial_maximum_volume_indices'],[[0]*3]*2)
        self.assertEqual(d['axial_maximum_amplitudes'],[[0.]*3]*2)

    def test_native_indices_and_reversed_spatial_mapping_outside_display_window(self):
        v=np.zeros((1300,2,3));v[3,0,0]=4.5;v[1250,1,1]=4.5
        d=self.diagnostics(v);raw,spec=display.axial_display(v,.001372)
        self.assertEqual(d['first_crossing_volume_indices'][2][1][2],3)
        self.assertEqual(d['first_crossing_volume_indices'][2][0][1],1250)
        self.assertEqual(d['axial_maximum_volume_indices'][0][1],1250)
        self.assertLess(3,spec['first_volume_index_zero_based'])
        self.assertGreaterEqual(1250,spec['first_volume_index_zero_based']+spec['frame_count'])
        self.assertEqual(d['volume_shape'],[1300,2,3])
        self.assertEqual(d['depth_bin_spacing_m'],.001372)
        self.assertEqual(d['default_divisor'],4.5)

if __name__=='__main__':unittest.main()
