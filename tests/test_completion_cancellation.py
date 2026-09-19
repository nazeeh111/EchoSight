"""Cancellation at final work boundaries must not publish completed decisions."""
import contextlib
import copy
import io
import json
from pathlib import Path
import signal
import tempfile
import unittest
from unittest.mock import patch
from jsonschema import ValidationError

from echosight import controlled
from echosight.cli import main
from echosight.pipeline import process_session, save_result
from evaluation.controlled_development import recording_protocol
from tests.test_schemas import validator


class CompletionCancellationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.scratch = tempfile.TemporaryDirectory()
        cls.root = Path(cls.scratch.name)
        cls.protocols = {}
        cls.results = {}
        for scenario in ('moved', 'failed_return'):
            protocol = recording_protocol(cls.root / scenario, scenario)
            cls.protocols[scenario] = protocol
            cls.results[scenario] = [process_session(e['session']) for e in protocol['epochs']]
        cls.original_bytes = json.dumps(cls.results, sort_keys=True)

    @classmethod
    def tearDownClass(cls):
        cls.scratch.cleanup()

    def assert_cancelled_comparison(self, result, scenario):
        self.assertEqual(result['status'], 'cancelled')
        self.assertEqual(result['receiver_evidence'], [])
        self.assertEqual(result['conditional_spatial_changes'], [])
        self.assertFalse(result['physical_scene_change_established'])
        self.assertEqual(len(result['epoch_results']), 4)
        for retained, original in zip(result['epoch_results'], self.results[scenario]):
            self.assertEqual(retained['result']['surfaces'], original['surfaces'])
            self.assertEqual([o['recording_sha256'] for o in retained['result']['observations']],
                             [o['recording_sha256'] for o in original['observations']])
        self.assertIn('cancelled_by_caller', str(result['diagnostics']))
        self.assertEqual(json.dumps(self.results, sort_keys=True), self.original_bytes)
        validator('controlled-result').validate(result)

    def test_controlled_core_and_cli_mid_late_and_last_receiver_early_returns(self):
        for boundary in ('mid_receiver', 'spatial', 'last_no_change', 'last_failed_return'):
            scenario = 'failed_return' if boundary == 'last_failed_return' else 'moved'
            protocol = copy.deepcopy(self.protocols[scenario])
            if boundary == 'last_no_change':
                protocol['controls']['differential_timing_std_s'] = .001
            for via_cli in (False, True):
                with self.subTest(boundary=boundary, cli=via_cli):
                    state = {'cancelled': False, 'calls': 0}
                    target = '_spatial_changes' if boundary == 'spatial' else '_receiver_evidence'
                    original = getattr(controlled, target)
                    def wrapped(*args, **kwargs):
                        value = original(*args, **kwargs)
                        state['calls'] += 1
                        stop = boundary in ('mid_receiver', 'spatial') or state['calls'] == 12
                        if stop:
                            if via_cli:
                                signal.raise_signal(signal.SIGINT)
                            else:
                                state['cancelled'] = True
                        return value
                    completed_inputs = copy.deepcopy(self.results[scenario])
                    before = json.dumps(completed_inputs, sort_keys=True)
                    with patch('echosight.pipeline.process_session', side_effect=completed_inputs), \
                         patch('echosight.controlled.' + target, side_effect=wrapped):
                        if via_cli:
                            path = self.root / 'protocol.json'
                            destination = self.root / 'cancelled.json'
                            save_result(protocol, path)
                            with contextlib.redirect_stdout(io.StringIO()):
                                code = main(['controlled', str(path), '--output', str(destination)])
                            self.assertEqual(code, 130)
                            result = json.loads(destination.read_text())
                        else:
                            result = controlled.process_controlled_protocol(protocol, cancel=lambda: state['cancelled'])
                    self.assertEqual(json.dumps(completed_inputs, sort_keys=True), before)
                    self.assert_cancelled_comparison(result, scenario)

    def test_uncancelled_decisions_remain_available(self):
        for scenario, high_budget, expected in (('moved', False, 'conditional_spatial_change'),
                                                ('moved', True, 'no_repeatable_change'),
                                                ('failed_return', False, 'inconclusive')):
            protocol = copy.deepcopy(self.protocols[scenario])
            if high_budget:
                protocol['controls']['differential_timing_std_s'] = .001
            with patch('echosight.pipeline.process_session', side_effect=copy.deepcopy(self.results[scenario])):
                result = controlled.process_controlled_protocol(protocol)
            self.assertEqual(result['status'], expected)
            self.assertEqual(len(result['receiver_evidence']), 12)

    def test_cancelled_schemas_reject_claim_bearing_completed_results(self):
        scene = copy.deepcopy(self.results['moved'][0])
        self.assertTrue(scene['surfaces'])
        validator('result').validate(scene)
        scene['status'] = 'cancelled'
        with self.assertRaises(ValidationError):
            validator('result').validate(scene)
        with patch('echosight.pipeline.process_session', side_effect=copy.deepcopy(self.results['moved'])):
            comparison = controlled.process_controlled_protocol(self.protocols['moved'])
        self.assertTrue(comparison['conditional_spatial_changes'])
        self.assertTrue(comparison['receiver_evidence'])
        validator('controlled-result').validate(comparison)
        comparison['status'] = 'cancelled'
        with self.assertRaises(ValidationError):
            validator('controlled-result').validate(comparison)

    def test_shared_scene_finalizer_is_copying_idempotent_and_clears_all_modes(self):
        from echosight.inference import _cancelled_result
        for diagnostics in (['existing'], ['cancelled_by_caller'],
                            [{'code': 'cancelled_by_caller', 'message': 'prior cancellation'}]):
            original = {'status': 'ok', 'diagnostics': diagnostics,
                        'search': {'complete': True, 'proposals': 3}, 'runtime_s': 1.25,
                        'observations': [{'recording_sha256': 'input-hash'}],
                        'processed_sessions': [{'session': {'session_id': 'input'}}]}
            for key in ('surfaces', 'hypotheses', 'dimensions', 'guidance',
                        'shared_image_source_covariance_m2', 'higher_order_explanations',
                        'shared_plane_parameter_covariance_m2', 'score',
                        'parent_model_comparison', 'path_model_comparison'):
                original[key] = ['unfinished']
            before = copy.deepcopy(original)
            result = _cancelled_result(original)
            self.assertEqual(original, before)
            self.assertEqual(_cancelled_result(result), result)
            self.assertEqual(result['status'], 'cancelled')
            for key in ('surfaces', 'hypotheses', 'dimensions', 'guidance'):
                self.assertEqual(result[key], [])
            for key in ('shared_image_source_covariance_m2', 'higher_order_explanations',
                        'shared_plane_parameter_covariance_m2', 'score',
                        'parent_model_comparison', 'path_model_comparison'):
                self.assertNotIn(key, result)
            self.assertEqual(result['search'], {'complete': False, 'proposals': 3})
            self.assertEqual(result['runtime_s'], 1.25)
            self.assertEqual(result['observations'], before['observations'])
            self.assertEqual(result['processed_sessions'], before['processed_sessions'])

    def test_outer_pipeline_terminal_callback_core_and_cli(self):
        session = self.protocols['moved']['epochs'][0]['session']
        for method in ('mapper', 'baseline'):
            for via_cli in (False, True):
                with self.subTest(method=method, cli=via_cli):
                    state = {'cancelled': False}
                    def terminal(fraction, message=''):
                        if fraction == 1 and message in ('ok', 'partial', 'ambiguous', 'no_result'):
                            state['cancelled'] = True
                            if via_cli:
                                signal.raise_signal(signal.SIGINT)
                    if via_cli:
                        path = self.root / 'session.json'
                        destination = self.root / 'pipeline-cancelled.json'
                        save_result(session, path)
                        def run(*args, **kwargs):
                            return process_session(*args, **kwargs, progress=terminal)
                        with patch('echosight.cli.process_session', side_effect=run), contextlib.redirect_stdout(io.StringIO()):
                            code = main(['process', str(path), '--method', method, '--output', str(destination)])
                        self.assertEqual(code, 130)
                        result = json.loads(destination.read_text())
                    else:
                        result = process_session(session, method=method, cancel=lambda: state['cancelled'], progress=terminal)
                    self.assertTrue(state['cancelled'])
                    self.assertEqual(result['status'], 'cancelled')
                    for key in ('surfaces', 'hypotheses', 'dimensions', 'guidance'):
                        self.assertEqual(result[key], [])
                    for key in ('shared_image_source_covariance_m2', 'higher_order_explanations', 'score'):
                        self.assertNotIn(key, result)
                    self.assertEqual(len(result['observations']), 12)
                    self.assertEqual(len(result['provenance']['recordings']), 12)
                    self.assertTrue(result['result_id'])
                    self.assertIn('cancelled_by_caller', str(result['diagnostics']))
                    validator('result').validate(result)


if __name__ == '__main__':
    unittest.main()
