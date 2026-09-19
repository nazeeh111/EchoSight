import contextlib
import io
import json
import tempfile
import unittest
from pathlib import Path


class CLITests(unittest.TestCase):
    def test_probe_has_explicit_channel_and_file_hash(self):
        import hashlib
        import numpy as np
        from scipy.io.wavfile import read
        from echosight.cli import main
        with tempfile.TemporaryDirectory() as temp, contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(main(["probe",temp,"--channel","left","--period","1.0"]),0)
            p=Path(temp);rate,samples=read(p/"probe.wav")
            self.assertEqual(samples.shape[1],2)
            self.assertFalse(np.any(samples[:,1]))
            metadata=json.loads((p/"probe.json").read_text())
            self.assertEqual(metadata["period_s"],1.)
            self.assertEqual(metadata["playback_wav_sha256"],hashlib.sha256((p/"probe.wav").read_bytes()).hexdigest())

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
