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

    def test_export_and_replay_are_real_processing_commands(self):
        from echosight.cli import main
        from echosight.simulation import simulate_session
        with tempfile.TemporaryDirectory() as temp, contextlib.redirect_stdout(io.StringIO()):
            p=Path(temp);session=simulate_session(p/"input",seed=1,capture_count=12)
            spec=json.loads(Path(session).read_text())
            spec['captures'][0]['device_id']='phone-0'
            spec['captures'][0]['receiver_pose_group_id']='survey-stop-0'
            Path(session).write_text(json.dumps(spec))
            archive=p/"survey.zip"
            self.assertEqual(main(["export",str(session),"--output",str(archive)]),0)
            self.assertTrue(archive.is_file())
            import zipfile
            with zipfile.ZipFile(archive) as z:
                saved=json.loads(z.read('session.json'))
                self.assertEqual(saved['captures'][0]['receiver_pose_group_id'],'survey-stop-0')
            self.assertEqual(main(["replay",str(archive),"--store",str(p/"replay"),"--output",str(p/"result.json")]),0)
            result=json.loads((p/"result.json").read_text())
            self.assertEqual(len(result["surfaces"]),6)
            self.assertEqual(result["provenance"]["evidence_classes"],["simulated"])

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
