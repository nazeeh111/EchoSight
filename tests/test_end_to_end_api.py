"""Actual HTTP upload -> acoustic processing -> geometry -> archive replay."""
import json
import tempfile
import threading
import time
import unittest
import urllib.request
from pathlib import Path


class EndToEndAPITests(unittest.TestCase):
    def test_real_recordings_through_http_and_replayed_processing(self):
        from echosight.api import create_server
        from echosight.pipeline import process_session
        from echosight.simulation import simulate_session
        from echosight.storage import SessionStore
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            path = simulate_session(root / "input", seed=1, capture_count=12)
            session = json.loads(path.read_text())
            server = create_server(root / "store", port=0)
            worker = threading.Thread(target=server.serve_forever, daemon=True)
            worker.start()
            base = f"http://127.0.0.1:{server.server_address[1]}"

            def request(method, route, body=None, headers=None, raw=False):
                if isinstance(body, dict): body = json.dumps(body).encode()
                req = urllib.request.Request(base + route, data=body, headers=headers or {}, method=method)
                with urllib.request.urlopen(req, timeout=20) as response:
                    data = response.read()
                    return data if raw else json.loads(data)

            try:
                created = request("POST", "/v1/sessions", dict(session, captures=[]))
                route = f"/v1/sessions/{created['session_id']}"
                for capture in session["captures"]:
                    metadata = {k:capture[k] for k in ("capture_id", "receiver_position_m", "receiver_position_std_m", "provenance")}
                    request("POST", route + "/recordings", (path.parent / capture["recording_path"]).read_bytes(),
                            {"X-Capture-Metadata":json.dumps(metadata)})
                job = request("POST", route + "/jobs", {})
                end = time.monotonic() + 20
                while time.monotonic() < end:
                    job = request("GET", f"/v1/jobs/{job['job_id']}")
                    if job["status"] in {"completed", "failed", "cancelled"}: break
                    time.sleep(.02)
                self.assertEqual(job["status"], "completed", job)
                result = request("GET", route + "/result")
                self.assertEqual(len(result["surfaces"]), 6)
                self.assertEqual(len(result["recording_manifest"]), 12)
                self.assertFalse(result["stale"])
                self.assertTrue(any(abs(s["normal"][2]) > .9 for s in result["surfaces"]))
                archive = root / "export.zip"
                archive.write_bytes(request("GET", route + "/export", raw=True))
                with SessionStore(root / "replay") as replay:
                    restored = replay.import_archive(archive)
                    with self.assertRaises(KeyError):
                        replay.get_result(restored["session_id"])
                    self.assertEqual(restored["replay"]["archived_result"]["status"], "quarantined_unverified")
                    self.assertEqual(restored["replay"]["archived_result"]["binding_issues"], [])
                    recomputed = process_session(replay.get_session(restored["session_id"]))
                self.assertEqual(recomputed["result_id"], result["result_id"])
                self.assertEqual(recomputed["surfaces"], result["surfaces"])
            finally:
                server.shutdown(); server.server_close(); worker.join()


if __name__ == "__main__": unittest.main()
