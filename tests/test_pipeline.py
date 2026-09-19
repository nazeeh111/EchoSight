"""Integration acceptance: public entry starts with recordings, never echo truth."""
import json
import tempfile
import unittest
from pathlib import Path


class PipelineTests(unittest.TestCase):
    def test_missing_pose_and_probe_returns_calibration_diagnostic(self):
        from echosight.pipeline import process_session
        result = process_session({"session_id": "uncalibrated", "captures": [
            {"capture_id": "phone1", "recording_path": "missing.wav"}]})
        self.assertEqual(result["status"], "no_result")
        self.assertIn("missing_calibration", str(result["diagnostics"]))

    def test_recordings_recover_height_without_truth_and_reload_exactly(self):
        from echosight.simulation import simulate_session
        from echosight.pipeline import process_session, save_result
        from echosight.storage import load_session
        with tempfile.TemporaryDirectory() as temp:
            path = simulate_session(temp, seed=2)
            session = load_session(path)
            # Deliberately bogus annotations must never influence inference.
            session["truth"] = {"room": [999,999,999]}
            session["captures"][0]["diagnostics"] = ["sample_grid_unverified"]
            result = process_session(session)
            self.assertGreaterEqual(len(result["surfaces"]), 4)
            self.assertTrue(any(abs(p["normal"][2]) > .9 for p in result["surfaces"]))
            self.assertNotIn("truth", result["acquisition"])
            self.assertEqual(result["provenance"]["evidence_classes"], ["simulated"])
            self.assertFalse(result["provenance"]["physical_validation"])
            self.assertEqual(len(result["provenance"]["implementation_sha256"]),64)
            self.assertIn("numpy",result["provenance"]["runtime_versions"])
            self.assertIn("sample_grid_unverified",result["observations"][0]["input_diagnostics"])
            target = save_result(result, Path(temp) / "result.json")
            self.assertEqual(result, json.loads(target.read_text()))

    def test_cancelled_before_reading_missing_recordings(self):
        from echosight.pipeline import process_session
        result = process_session({"schema_version": "1.0", "session_id": "cancel",
            "captures": []}, cancel=lambda: True)
        self.assertEqual(result["status"], "cancelled")

    def test_result_serialization_rejects_nonfinite(self):
        from echosight.pipeline import save_result
        with tempfile.TemporaryDirectory() as temp:
            with self.assertRaises(ValueError):
                save_result({"value": float("nan")}, Path(temp) / "result.json")
            self.assertFalse((Path(temp) / "result.json").exists())

    def test_declared_recording_checksum_mismatch_is_rejected(self):
        from echosight.simulation import simulate_session
        from echosight.pipeline import process_session
        from echosight.storage import load_session
        with tempfile.TemporaryDirectory() as temp:
            session = load_session(simulate_session(temp, seed=1))
            for capture in session["captures"]: capture["sha256"] = "0" * 64
            result = process_session(session)
            self.assertEqual(result["status"], "no_result")
            self.assertTrue(all(o["status"] == "rejected" for o in result["observations"]))
            self.assertIn("checksum", str(result["observations"]))


if __name__ == "__main__":
    unittest.main()
