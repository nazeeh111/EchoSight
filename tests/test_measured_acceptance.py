"""Frozen evaluator gates must reject fabricated extent claims as well as bad fits."""
import copy
import json
from pathlib import Path
import unittest
from evaluation.dechorate_multisource import acceptance_failures

class MeasuredAcceptanceTests(unittest.TestCase):
    def setUp(self):
        self.spec=json.loads((Path(__file__).resolve().parents[1]/'evaluation/dechorate_multisource_protocol.json').read_text())
        self.metrics=dict(predicted_count=5,matched_count=5,horizontal_matched=1,false_surfaces=0)
        self.result={'surfaces':[{'extent_status':'unknown','mesh_semantics':'reflection_support_convex_hull_not_physical_edges'}]}

    def test_geometry_success_cannot_claim_physical_extent(self):
        self.assertEqual(acceptance_failures(self.result,self.metrics,'joint_mapper',1.,self.spec),[])
        for key,value in [('extent_status','known_physical_extent'),('mesh_semantics','closed_room_boundary')]:
            invalid=copy.deepcopy(self.result);invalid['surfaces'][0][key]=value
            self.assertIn('unsupported_physical_extent_or_enclosure_semantics',acceptance_failures(invalid,self.metrics,'joint_mapper',1.,self.spec))
        invalid=copy.deepcopy(self.result);del invalid['surfaces'][0]['extent_status']
        self.assertTrue(acceptance_failures(invalid,self.metrics,'joint_mapper',1.,self.spec))

    def test_controls_and_recovery_are_separate(self):
        empty={'surfaces':[]};zero=dict(predicted_count=0,matched_count=0,horizontal_matched=0,false_surfaces=0)
        for arm in ('null','shuffled_geometry'):
            self.assertFalse(acceptance_failures(empty,zero,arm,1.,self.spec))
            self.assertIn('definitive_geometry_in_control',acceptance_failures(self.result,self.metrics,arm,1.,self.spec))
        self.assertIn('insufficient_room_planes',acceptance_failures(empty,zero,'joint_mapper',1.,self.spec))

    def test_every_frozen_numeric_gate_is_applied(self):
        for key,value,expected in [('matched_count',3,'insufficient_room_planes'),('horizontal_matched',0,'insufficient_horizontal_planes'),('false_surfaces',1,'unmatched_definitive_planes')]:
            metrics=dict(self.metrics);metrics[key]=value
            self.assertIn(expected,acceptance_failures(self.result,metrics,'joint_mapper',1.,self.spec))
        self.assertIn('runtime_limit',acceptance_failures(self.result,self.metrics,'joint_mapper',301.,self.spec))
        self.assertIn('runtime_limit',acceptance_failures({'surfaces':[]},dict(predicted_count=0),'null',301.,self.spec))

if __name__=='__main__':unittest.main()
