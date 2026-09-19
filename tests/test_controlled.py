"""Development controls enter through independently rendered lossless recordings."""
import copy
import json
from pathlib import Path
import tempfile
import unittest
import numpy as np
from scipy.io import wavfile
from echosight.controlled import process_controlled_protocol
from echosight.signals import generate_probe


from evaluation.controlled_development import recording_protocol


class ControlledAcquisitionTests(unittest.TestCase):
    def test_missing_controls_and_cancellation_are_explicit(self):
        result=process_controlled_protocol({'schema_version':'1.0'})
        self.assertEqual(result['status'],'inconclusive')
        self.assertIn('protocol_invalid',str(result['diagnostics']))
        self.assertEqual(process_controlled_protocol({},cancel=lambda:True)['status'],'cancelled')

    def test_raw_null_and_gain_only_do_not_claim_spatial_change(self):
        for scenario in ['null','gain_only']:
            with self.subTest(scenario=scenario),tempfile.TemporaryDirectory() as folder:
                result=process_controlled_protocol(recording_protocol(folder,scenario))
                self.assertEqual(result['status'],'no_repeatable_change',result['diagnostics'])
                self.assertFalse(result['conditional_spatial_changes'])
                self.assertFalse(result['physical_scene_change_established'])

    def test_route_and_calibration_drift_rejected_before_processing(self):
        with tempfile.TemporaryDirectory() as folder:
            protocol=recording_protocol(folder)
            for kind in ['route','calibration','source','reused_device']:
                with self.subTest(kind=kind):
                    changed=copy.deepcopy(protocol)
                    if kind=='route':changed['epochs'][1]['route_ids']['phone-00']='different-route'
                    if kind=='calibration':changed['epochs'][1]['calibration_id']='different-calibration'
                    if kind=='source':changed['epochs'][1]['source_configuration_id']='different-source'
                    if kind=='reused_device':changed['epochs'][0]['session']['captures'][1]['device_id']='phone-00'
                    result=process_controlled_protocol(changed)
                    self.assertEqual(result['status'],'inconclusive');self.assertEqual(result['epoch_results'],[])

    def test_reversible_reflector_move_is_supported_by_positive_echoes(self):
        with tempfile.TemporaryDirectory() as folder:
            result=process_controlled_protocol(recording_protocol(folder,'moved'))
            self.assertIn(result['status'],('repeatable_acoustic_change_unlocalized','conditional_spatial_change'),result['diagnostics'])
            self.assertGreaterEqual(sum(bool(e['shifted_positive_echoes']) for e in result['receiver_evidence']),6)
            self.assertTrue(any(s['delay_change_s']<0 for e in result['receiver_evidence'] for s in e['shifted_positive_echoes']))
            self.assertFalse(result['physical_scene_change_established'])
            self.assertFalse(result['physical_validation'])
            self.assertEqual(result['status'],'conditional_spatial_change')
            from echosight.controlled import _spatial_changes
            epochs=[copy.deepcopy(e['result']) for e in result['epoch_results']]
            shift=np.array([70.,-45.,23.])
            for epoch in epochs:
                epoch['acquisition']['source_position_m']=(np.asarray(epoch['acquisition']['source_position_m'])+shift).tolist()
                for plane in epoch['surfaces']:
                    plane['offset_m']+=float(np.asarray(plane['normal'])@shift)
                    plane['image_source_m']=(np.asarray(plane['image_source_m'])+shift).tolist()
            translated=_spatial_changes(epochs,result['receiver_evidence'])
            self.assertEqual(len(translated),len(result['conditional_spatial_changes']))
            self.assertAlmostEqual(translated[0]['offset_change_m'],result['conditional_spatial_changes'][0]['offset_change_m'],places=10)
            self.assertAlmostEqual(translated[0]['conservative_offset_std_bound_m'],result['conditional_spatial_changes'][0]['conservative_offset_std_bound_m'],places=12)

    def test_shared_timing_budget_does_not_shrink_across_receivers(self):
        with tempfile.TemporaryDirectory() as folder:
            protocol=recording_protocol(folder,'moved')
            protocol['controls']['differential_timing_std_s']=.001
            result=process_controlled_protocol(protocol)
            self.assertIn(result['status'],('no_repeatable_change','inconclusive'))
            self.assertFalse(result['conditional_spatial_changes'])
            self.assertFalse(any(e['shifted_positive_echoes'] for e in result['receiver_evidence']))

    def test_four_stationary_phones_keep_ambiguous_geometry_unlocalized(self):
        with tempfile.TemporaryDirectory() as folder:
            result=process_controlled_protocol(recording_protocol(folder,'moved',receiver_count=4))
            self.assertEqual(result['status'],'repeatable_acoustic_change_unlocalized')
            self.assertGreaterEqual(sum(e['repeatable_change'] for e in result['receiver_evidence']),3)
            self.assertFalse(result['conditional_spatial_changes'])

    def test_clock_uncertainty_and_duplicate_bytes_cannot_strengthen_evidence(self):
        from unittest.mock import patch
        from echosight.pipeline import process_session
        with tempfile.TemporaryDirectory() as folder:
            protocol=recording_protocol(folder,'moved',receiver_count=4)
            results=[process_session(epoch['session']) for epoch in protocol['epochs']]
            enlarged=copy.deepcopy(results)
            for result in enlarged:
                for observation in result['observations']:
                    observation['clock']['alpha_std']=.05
            with patch('echosight.pipeline.process_session',side_effect=enlarged):
                out=process_controlled_protocol(protocol)
            self.assertFalse(any(e['shifted_positive_echoes'] for e in out['receiver_evidence']))
            self.assertNotIn(out['status'],('repeatable_acoustic_change_unlocalized','conditional_spatial_change'))
            copied=copy.deepcopy(results)
            for i in (2,3):
                for observation,original in zip(copied[i]['observations'],copied[3-i]['observations']):
                    observation['recording_sha256']=original['recording_sha256']
            with patch('echosight.pipeline.process_session',side_effect=copied):
                out=process_controlled_protocol(protocol)
            self.assertEqual(out['status'],'inconclusive')
            self.assertIn('recordings_reused',str(out['diagnostics']))

    def test_failure_to_restore_A_prevents_change_claim(self):
        with tempfile.TemporaryDirectory() as folder:
            result=process_controlled_protocol(recording_protocol(folder,'failed_return'))
            self.assertEqual(result['status'],'inconclusive')
            self.assertIn('return_or_repeat_failed',str(result['diagnostics']))

if __name__=='__main__':unittest.main()
