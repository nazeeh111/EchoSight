"""Regression from retained raw recording-derived candidate evidence.

The fixture contains no generated path labels. Evaluation geometry is read only
once inference returns, using the original frozen relocation matching limits.
"""
import json
from pathlib import Path
import unittest
from unittest.mock import patch
from echosight import multisource
from echosight.multisource import infer_scene_bundle
from evaluation.metrics import score_surfaces


class MultisourceSupportRecovery(unittest.TestCase):
    def test_cancellation_during_refit_stops_before_another_fit(self):
        folder = Path(__file__).with_name('fixtures')
        data = json.loads((folder / 'higher-order-1129-observations.json').read_text())
        fit = multisource.least_squares
        cancelled = False
        fits_after_request = 0

        def request_cancellation_after_refit(*args, **kwargs):
            nonlocal cancelled, fits_after_request
            if cancelled:
                fits_after_request += 1
            result = fit(*args, **kwargs)
            if kwargs.get('loss', 'linear') == 'linear':
                cancelled = True
            return result

        with patch.object(multisource, 'least_squares', request_cancellation_after_refit):
            result = infer_scene_bundle(data['processed_sessions'], data['bundle'], cancel=lambda: cancelled)
        self.assertTrue(cancelled)
        self.assertEqual(fits_after_request, 0)
        self.assertEqual(result['status'], 'cancelled')
        self.assertEqual(result['surfaces'], [])
        self.assertEqual(result['hypotheses'], [])

    def test_weak_candidate_cannot_erase_supported_room(self):
        folder = Path(__file__).with_name('fixtures')
        data = json.loads((folder / 'higher-order-1129-observations.json').read_text())
        before = json.dumps(data, sort_keys=True)
        result = infer_scene_bundle(data['processed_sessions'], data['bundle'])
        self.assertEqual(json.dumps(data, sort_keys=True), before)
        truth = json.loads((folder / 'higher-order-1129-evaluation.json').read_text())
        metrics = score_surfaces(result, truth, maximum_normal_error_deg=5., maximum_offset_error_m=.15)
        self.assertEqual(metrics['matched_count'], 6, result['diagnostics'])
        self.assertEqual(metrics['horizontal_matched'], 2)
        self.assertEqual(metrics['false_surfaces'], 0)
        self.assertEqual(result['status'], 'partial')
        self.assertTrue(any('joint_refit_pruned_unsupported_candidates' in str(d) for d in result['diagnostics']))
        for surface in result['surfaces']:
            support = surface['support']
            counts = {item['session']['session_id']: 0 for item in data['processed_sessions']}
            for evidence in support:
                counts[evidence['session_id']] += 1
            self.assertTrue(all(count >= 4 for count in counts.values()), counts)
            self.assertEqual(surface['extent_status'], 'unknown')


if __name__ == '__main__':
    unittest.main()
