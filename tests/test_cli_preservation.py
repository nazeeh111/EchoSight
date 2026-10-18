"""Ordinary CLI file preservation; no recording processing or inference."""
import contextlib
import io
import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from echosight.cli import main


class ProcessPreservationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.session = self.root / "session.json"
        self.original = b'{"session_id":"survey","source_position_m":null,"probe":{},"captures":[]}\n'
        self.session.write_bytes(self.original)
        self.stdout, self.stderr = io.StringIO(), io.StringIO()
        self.enterContext(contextlib.redirect_stdout(self.stdout))
        self.enterContext(contextlib.redirect_stderr(self.stderr))

    def assert_refused(self, output, *extra):
        with patch("echosight.cli.process_session") as processor:
            self.assertEqual(main(["process", str(self.session), "--output", str(output), *extra]), 2)
            processor.assert_not_called()
        self.assertEqual(self.session.read_bytes(), self.original)
        self.assertIn("output", self.stderr.getvalue().lower())
        self.assertNotIn("Traceback", self.stderr.getvalue())
        self.assertNotIn("Saved:", self.stdout.getvalue())
        self.assertFalse(list(self.root.glob(".echosight-*")))

    def test_same_session_path_refuses_before_processing(self):
        self.assert_refused(self.session)

    def test_parent_symlink_alias_refuses_before_processing(self):
        alias = self.root / "alias"
        alias.symlink_to(self.root, target_is_directory=True)
        self.assert_refused(alias / self.session.name)
        self.assertTrue(alias.is_symlink())

    def test_hardlink_alias_refuses_before_processing(self):
        alias = self.root / "alias.json"
        os.link(self.session, alias)
        self.assert_refused(alias)
        self.assertTrue(self.session.samefile(alias))
        self.assertEqual(alias.read_bytes(), self.original)

    def test_context_path_is_preserved_even_before_context_validation(self):
        context = self.root / "context.json"
        context.write_bytes(b'{"supplied":"context"}\n')
        self.assert_refused(context, "--interpretation-context", str(context))
        self.assertEqual(context.read_bytes(), b'{"supplied":"context"}\n')
        self.assertIn("input", self.stderr.getvalue().lower())

    def test_relative_recording_path_is_preserved_without_reading_audio(self):
        recordings = self.root / "recordings"
        recordings.mkdir()
        recording = recordings / "capture.wav"
        recording.write_bytes(b"disposable raw recording bytes")
        spec = json.loads(self.original)
        spec["captures"] = [{"capture_id": "c1", "recording_path": "recordings/capture.wav"}]
        self.original = (json.dumps(spec) + "\n").encode()
        self.session.write_bytes(self.original)
        self.assert_refused(recording)
        self.assertEqual(recording.read_bytes(), b"disposable raw recording bytes")

    def test_output_symlink_to_input_is_preserved(self):
        alias = self.root / "output.json"
        alias.symlink_to(self.session)
        self.assert_refused(alias)
        self.assertTrue(alias.is_symlink())

    def test_distinct_output_retains_real_missing_calibration_result(self):
        output = self.root / "result.json"
        with patch("echosight.signals.process_recording", side_effect=AssertionError("No audio processing")), \
             patch("echosight.inference.infer_scene", side_effect=AssertionError("No inference")):
            self.assertEqual(main(["process", str(self.session), "--output", str(output)]), 0)
        result = json.loads(output.read_text())
        self.assertEqual(result["status"], "no_result")
        self.assertEqual(result["diagnostics"][0]["code"], "missing_calibration")
        self.assertEqual(self.session.read_bytes(), self.original)

    def test_distinct_output_retains_real_invalid_session_result(self):
        self.original = b"{invalid JSON\n"
        self.session.write_bytes(self.original)
        output = self.root / "result.json"
        self.assertEqual(main(["process", str(self.session), "--output", str(output)]), 0)
        self.assertEqual(json.loads(output.read_text())["diagnostics"][0]["code"], "invalid_session")
        self.assertEqual(self.session.read_bytes(), self.original)

    def test_alias_created_during_processing_refuses_before_save(self):
        output = self.root / "result.json"
        def change_destination(*args, **kwargs):
            output.symlink_to(self.session)
            return {"status": "no_result"}
        with patch("echosight.cli.process_session", side_effect=change_destination):
            self.assertEqual(main(["process", str(self.session), "--output", str(output)]), 2)
        self.assertTrue(output.is_symlink())
        self.assertEqual(self.session.read_bytes(), self.original)
        self.assertNotIn("Saved:", self.stdout.getvalue())

    def test_distinct_existing_result_can_be_replaced(self):
        output = self.root / "result.json"
        output.write_text('{"old":"result"}')
        result = {"status": "no_result", "surfaces": [], "diagnostics": []}
        with patch("echosight.cli.process_session", return_value=result) as processor:
            self.assertEqual(main(["process", str(self.session), "--output", str(output)]), 0)
            processor.assert_called_once()
        self.assertEqual(json.loads(output.read_text()), result)
        self.assertEqual(self.session.read_bytes(), self.original)


if __name__ == "__main__":
    unittest.main()
