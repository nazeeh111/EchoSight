"""Renderable geometry and evidence linkage at the frontend boundary."""
import tempfile
import unittest
import numpy as np


class FrontendContractTests(unittest.TestCase):
    def test_triangles_coordinates_and_evidence_match_recording_results(self):
        from echosight.simulation import simulate_session
        from echosight.pipeline import process_session
        with tempfile.TemporaryDirectory() as temp:
            result = process_session(simulate_session(temp, seed=1, capture_count=12))
        self.assertEqual(result["schema_version"], "1.0")
        self.assertEqual(len(result["surfaces"]), 6)
        candidates = {(o["capture_id"],c["candidate_id"]): c for o in result["observations"] for c in o["candidates"]}
        used = set()
        for surface in result["surfaces"]:
            vertices=np.asarray(surface["vertices_m"])
            normal=np.asarray(surface["normal"])
            self.assertEqual(surface["extent_status"],"unknown")
            self.assertAlmostEqual(np.linalg.norm(normal),1.)
            self.assertLess(np.max(np.abs(vertices @ normal - surface["offset_m"])),1e-8)
            for triangle in surface["triangles"]:
                self.assertEqual(len(triangle),3)
                self.assertTrue(all(0 <= i < len(vertices) for i in triangle))
            for support in surface["support"]:
                key=(support["capture_id"],support["candidate_id"])
                self.assertIn(key,candidates)
                self.assertNotIn(key,used);used.add(key)
                self.assertEqual(support["observed_delay_s"], candidates[key]["delay_s"])
                self.assertAlmostEqual(support["residual_s"],support["observed_delay_s"]-support["predicted_delay_s"])


if __name__ == "__main__": unittest.main()
