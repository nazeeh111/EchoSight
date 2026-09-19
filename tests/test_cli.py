import contextlib
import io
import json
import tempfile
import unittest
from pathlib import Path


class CLITests(unittest.TestCase):
    def test_inspect_prints_result_evidence_summary(self):
        from echosight.cli import main
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "result.json"
            path.write_text(json.dumps({"status": "partial", "surfaces": [{"surface_id": "s"}],
                                       "provenance": {"evidence_classes": ["simulated"]}}))
            stream = io.StringIO()
            with contextlib.redirect_stdout(stream):
                self.assertEqual(main(["inspect", str(path)]), 0)
            self.assertIn('"surface_count": 1', stream.getvalue())
            self.assertIn("simulated", stream.getvalue())

    def test_bad_input_has_nonzero_exit_without_traceback(self):
        from echosight.cli import main
        stream = io.StringIO()
        with contextlib.redirect_stderr(stream):
            self.assertEqual(main(["inspect", "/definitely/missing/result.json"]), 2)
        self.assertIn("error", stream.getvalue().lower())


if __name__ == "__main__":
    unittest.main()
