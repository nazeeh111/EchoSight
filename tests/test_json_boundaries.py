"""CLI/API malformed JSON, resource limits and retained input-byte guarantees."""
import contextlib
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from echosight.cli import main
from echosight.fileio import parse_json_object, read_json_object
from echosight.storage import MAX_JSON_BYTES, MAX_RESULT_BYTES


class JSONBoundaryTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)

    def run_cli(self, *arguments):
        stdout, stderr = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
            code = main(list(map(str, arguments)))
        self.assertNotIn('Traceback', stderr.getvalue())
        return code, stdout.getvalue(), stderr.getvalue()

    def test_inspect_rejects_nonobjects_and_malformed_count_fields_without_traceback(self):
        values = [[], None, True, 7, 'text', {'surfaces': 'xx'}, {'surfaces': None},
                  {'surfaces': [None]}, {'hypotheses': {}}, {'hypotheses': [4]}, {'interpretation': []}]
        path = self.root / 'result.json'
        for value in values:
            with self.subTest(value=value):
                path.write_text(json.dumps(value)); original = path.read_bytes()
                code, stdout, stderr = self.run_cli('inspect', path)
                self.assertEqual(code, 2); self.assertEqual(stdout, '')
                self.assertIn('EchoSight error:', stderr); self.assertEqual(path.read_bytes(), original)

    def test_valid_compact_inspection_retains_counts_and_provenance(self):
        value = {'status': 'partial', 'surfaces': [{'surface_id': 's'}], 'hypotheses': [],
                 'provenance': {'evidence_classes': ['supplied']}}
        path = self.root / 'result.json'; path.write_text(json.dumps(value))
        code, stdout, stderr = self.run_cli('inspect', path)
        self.assertEqual(code, 0, stderr)
        summary = json.loads(stdout)
        self.assertEqual(summary['surface_count'], 1); self.assertEqual(summary['hypothesis_count'], 0)
        self.assertEqual(summary['provenance'], value['provenance'])

    def test_inspect_enforces_real_result_byte_limit_before_decoding(self):
        path = self.root / 'oversized.json'
        with path.open('wb') as stream: stream.truncate(MAX_RESULT_BYTES + 1)
        code, stdout, stderr = self.run_cli('inspect', path)
        self.assertEqual(code, 2); self.assertEqual(stdout, '')
        self.assertIn('exceeds byte limit', stderr)
        self.assertEqual(path.stat().st_size, MAX_RESULT_BYTES + 1)

    def test_metadata_read_is_bounded_at_decode_including_reference_inputs(self):
        path = self.root / 'metadata.json'; path.write_bytes(b'{}' + b' ' * (MAX_JSON_BYTES - 2))
        self.assertEqual(read_json_object(path, MAX_JSON_BYTES), {})
        with path.open('ab') as stream: stream.write(b' ')
        with self.assertRaisesRegex(ValueError, 'exceeds byte limit'): read_json_object(path, MAX_JSON_BYTES)
        session = self.root / 'session.json'; session.write_text('{"captures":[]}')
        output = self.root / 'proposal.json'; output.write_bytes(b'prior proposal')
        with patch('echosight.calibration.calibrate_reference') as calibrate:
            code, _, stderr = self.run_cli('calibrate-reference', session, path, '--output', output)
        self.assertEqual(code, 2); self.assertIn('exceeds byte limit', stderr); calibrate.assert_not_called()
        self.assertEqual(output.read_bytes(), b'prior proposal')

    def test_duplicate_keys_nonfinite_overflow_and_deep_inputs_share_api_policy(self):
        from echosight.api import _strict_object
        invalid = [b'{"x":1,"x":2}', b'{"x":{"k":1,"k":2}}', b'{"x":NaN}',
                   b'{"x":Infinity}', b'{"x":-Infinity}', b'{"x":[{"v":1e400}]}',
                   b'{"x":' + b'[' * 70 + b'0' + b']' * 70 + b'}', b'[]', b'\xff']
        for raw in invalid:
            for parser in (parse_json_object, _strict_object):
                with self.subTest(raw=raw[:60], parser=parser):
                    with self.assertRaises(ValueError): parser(raw)
        valid = b'{"x":' + b'[' * 62 + b'0' + b']' * 62 + b'}'
        self.assertEqual(parse_json_object(valid), _strict_object(valid))
        self.assertEqual(parse_json_object(b'{"x":[1,2,3],"text":"hello"}'), {'x': [1, 2, 3], 'text': 'hello'})

    def test_compare_rejects_ambiguous_json_without_replacing_a_prior_output(self):
        before = self.root / 'before.json'; before.write_text('{"status":"partial","status":"no_result"}')
        after = self.root / 'after.json'; after.write_text('{"status":"no_result","surfaces":[]}')
        output = self.root / 'comparison.json'; output.write_bytes(b'prior comparison')
        with patch('echosight.evolution.compare_results') as compare:
            code, stdout, stderr = self.run_cli('compare', before, after, '--output', output)
        self.assertEqual(code, 2); self.assertEqual(stdout, ''); self.assertIn('invalid JSON', stderr)
        compare.assert_not_called(); self.assertEqual(output.read_bytes(), b'prior comparison')

    def test_tolerant_path_discovery_still_protects_audio_in_ambiguous_definitions(self):
        recording = self.root / 'audio.wav'; recording.write_bytes(b'original audio')
        session = self.root / 'session.json'
        session.write_text('{"captures":[],"captures":[{"capture_id":"c","recording_path":"audio.wav"}]}')
        with patch('echosight.cli.process_session') as process:
            code, _, stderr = self.run_cli('process', session, '--output', recording)
        self.assertEqual(code, 2); self.assertIn('output must be distinct', stderr); process.assert_not_called()
        self.assertEqual(recording.read_bytes(), b'original audio')
        protocol = self.root / 'protocol.json'
        protocol.write_text('{"epochs":[],"epochs":[{"session":"session.json"}]}')
        with patch('echosight.controlled.process_controlled_protocol') as process:
            code, _, stderr = self.run_cli('controlled', protocol, '--output', recording)
        self.assertEqual(code, 2); self.assertIn('output must be distinct', stderr); process.assert_not_called()
        self.assertEqual(recording.read_bytes(), b'original audio')

    def test_unrepresentable_geometry_integer_returns_error_without_losing_outputs(self):
        before = self.root / 'before.json'; after = self.root / 'after.json'
        before.write_text(json.dumps({'status': 'partial', 'surfaces': [
            {'surface_id': 's', 'normal': [1, 0, 0], 'offset_m': 10 ** 1000}]}))
        after.write_text('{"surfaces":[]}')
        output = self.root / 'comparison.json'; output.write_bytes(b'prior comparison')
        code, stdout, stderr = self.run_cli('compare', before, after, '--output', output)
        self.assertEqual(code, 2); self.assertEqual(stdout, ''); self.assertIn('EchoSight error:', stderr)
        self.assertEqual(output.read_bytes(), b'prior comparison')
