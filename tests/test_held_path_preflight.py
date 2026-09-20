import copy
import json
import math
from pathlib import Path
import unittest

from evaluation.held_path_preflight import check_plan


class HeldPathPreflightTests(unittest.TestCase):
    def plan(self, separation):
        return dict(candidate_window_s=.125, required_path_ids=['a', 'b'], captures=[
            dict(capture_id='held', paths=[dict(path_id='a', excess_delay_s=1.),
                                          dict(path_id='b', excess_delay_s=1. + separation)])])

    def test_inclusive_boundary_rejects_both_paths(self):
        result = check_plan(self.plan(.125))
        self.assertFalse(result['ideal_gate_pass'])
        self.assertEqual((result['unique'], result['expected']), (0, 2))
        self.assertEqual(result['captures'][0]['conflicting_pairs'][0]['path_ids'], ['a', 'b'])

    def test_overlapping_windows_can_have_unique_ideal_candidates(self):
        result = check_plan(self.plan(.1875))
        self.assertTrue(result['ideal_gate_pass'])
        self.assertFalse(result['captures'][0]['all_windows_disjoint'])
        self.assertTrue(check_plan(self.plan(.375))['captures'][0]['all_windows_disjoint'])

    def test_equal_arrivals_and_every_capture_count(self):
        plan = self.plan(.375)
        other = self.plan(0)['captures'][0]
        other['capture_id'] = 'collision'
        plan['captures'].append(other)
        original = copy.deepcopy(plan)
        result = check_plan(plan)
        self.assertEqual((result['unique'], result['expected']), (2, 4))
        self.assertFalse(result['ideal_gate_pass'])
        self.assertEqual(plan, original)

    def test_original_held_geometry_rejects_four_perfect_paths(self):
        path = Path(__file__).resolve().parents[1] / 'evidence/calibration-room-transfer/ideal-held-catalog.json'
        result = check_plan(json.loads(path.read_text()))
        self.assertEqual((result['unique'], result['expected']), (20, 24))
        self.assertFalse(result['ideal_gate_pass'])
        self.assertEqual([r['capture_id'] for r in result['captures'] if not r['ideal_gate_pass']],
                         ['capture-14', 'capture-15'])

    def test_incomplete_duplicate_or_invalid_catalog_cannot_pass(self):
        cases = []
        missing = self.plan(.375); missing['captures'][0]['paths'].pop(); cases.append(missing)
        duplicate = self.plan(.375); duplicate['captures'][0]['paths'][1]['path_id'] = 'a'; cases.append(duplicate)
        duplicate_capture = self.plan(.375); duplicate_capture['captures'] *= 2; cases.append(duplicate_capture)
        empty = self.plan(.375); empty['captures'] = []; cases.append(empty)
        for value in (math.nan, math.inf, -1., 0., True, '0.1'):
            bad = self.plan(.375); bad['candidate_window_s'] = value; cases.append(bad)
            bad = self.plan(.375); bad['captures'][0]['paths'][0]['excess_delay_s'] = value; cases.append(bad)
        for plan in cases:
            with self.subTest(plan=plan), self.assertRaises(ValueError):
                check_plan(plan)


if __name__ == '__main__':
    unittest.main()
