"""Interpretation stays downstream of raw acoustic geometry and publication."""
import copy
import tempfile
import unittest
from pathlib import Path

from echosight.inference import _cancelled_result
from echosight.pipeline import process_session
from echosight.simulation import simulate_session
from echosight.storage import load_session


class InterpretationPipelineTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory()
        path = simulate_session(Path(cls.temp.name), seed=1, capture_count=12)
        cls.session = load_session(path)
        cls.original = process_session(cls.session)

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()

    def test_context_is_bound_after_geometry_and_preserved_for_replay(self):
        session = copy.deepcopy(self.session)
        context = {'schema_version': '1.0', 'route_id': 'declared-test-route',
                   'profiles': [], 'maximum_squared_distance': 16, 'minimum_views': 3}
        session['interpretation_context'] = context
        before = copy.deepcopy(session)
        result = process_session(session)
        self.assertIn('interpretation', result)
        self.assertEqual(result['acquisition']['interpretation_context'], context)
        self.assertEqual(result['interpretation']['source_result_id'], result['result_id'])
        self.assertNotEqual(result['result_id'], self.original['result_id'])
        self.assertEqual(result['surfaces'], self.original['surfaces'])
        self.assertEqual(result['observations'], self.original['observations'])
        self.assertEqual(result['hypotheses'], self.original['hypotheses'])
        self.assertEqual(session, before)

    def test_shared_cancellation_retracts_interpretation_claims(self):
        result = copy.deepcopy(self.original)
        result['interpretation'] = {'schema_version': '1.0', 'status': 'estimated',
                                    'surface_interpretations': [{'surface_id': 'surface'}]}
        original = copy.deepcopy(result)
        cancelled = _cancelled_result(result)
        self.assertEqual(cancelled['status'], 'cancelled')
        self.assertEqual(cancelled['surfaces'], [])
        self.assertNotIn('interpretation', cancelled)
        self.assertEqual(result, original)
