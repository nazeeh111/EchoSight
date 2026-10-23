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


class NamedInputPreservationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.session = self.root / "session.json"
        self.recording = self.root / "capture.wav"
        self.recording.write_bytes(b"original recording")
        self.session.write_text(json.dumps({"captures": [{"recording_path": "capture.wav"}]}))
        self.extra = self.root / "extra.json"
        self.extra.write_text('{}')
        self.carry = self.root / "carry.json"
        self.carry.write_text('{}')
        self.appearance = self.root / "appearance.json"
        self.appearance.write_text('{}')
        self.stdout, self.stderr = io.StringIO(), io.StringIO()
        self.enterContext(contextlib.redirect_stdout(self.stdout))
        self.enterContext(contextlib.redirect_stderr(self.stderr))

    def commands(self):
        return [
            (["compare", str(self.session), str(self.extra)], [self.session, self.extra], "echosight.evolution.compare_results"),
            (["compare", str(self.session), str(self.extra), "--previous-comparison", str(self.carry)], [self.carry], "echosight.evolution.compare_results"),
            (["calibrate-reference", str(self.session), str(self.extra)], [self.session, self.recording, self.extra], "echosight.calibration.calibrate_reference"),
            (["material-reference", str(self.session), "--provenance", str(self.extra), "--appearance", str(self.appearance),
              "--surface-id", "wall", "--material-id", "brick", "--label", "Brick", "--route-id", "route"],
             [self.session, self.recording, self.extra, self.appearance], "echosight.cli.process_session"),
            (["export", str(self.session)], [self.session, self.recording], "echosight.storage.load_session"),
            (["replay", str(self.extra), "--store", str(self.root / "store")], [self.extra], "echosight.storage.SessionStore"),
        ]

    def test_named_inputs_refuse_same_symlink_and_hardlink_before_work(self):
        for command, inputs, processor in self.commands():
            for source in inputs:
                for alias_kind in ("same", "symlink", "hardlink"):
                    with self.subTest(command=command[0], source=source.name, alias=alias_kind):
                        self.stdout.truncate(0); self.stdout.seek(0)
                        alias = self.root / "alias-output"
                        if alias_kind == "same":
                            output = source
                        else:
                            output = alias
                            if alias_kind == "symlink": alias.symlink_to(source)
                            else: os.link(source, alias)
                        original = source.read_bytes()
                        with patch(processor) as work:
                            self.assertEqual(main([*command, "--output", str(output)]), 2)
                            work.assert_not_called()
                        self.assertEqual(source.read_bytes(), original)
                        self.assertEqual(self.stdout.getvalue(), "")
                        self.assertNotIn("Traceback", self.stderr.getvalue())
                        if alias_kind == "symlink": self.assertTrue(alias.is_symlink())
                        if alias_kind == "hardlink": self.assertTrue(alias.samefile(source))
                        if alias_kind != "same": alias.unlink()

    def test_controlled_protects_protocol_nested_manifests_and_inline_recordings(self):
        nested = self.root / "nested"
        nested.mkdir()
        manifest = nested / "session.json"
        raw = nested / "raw.wav"
        raw.write_bytes(b"nested raw")
        manifest.write_text(json.dumps({"captures": [{"recording_path": "raw.wav"}]}))
        protocol = self.root / "protocol.json"
        protocol.write_text(json.dumps({"epochs": [{"session": "nested/session.json"},
            {"session": {"captures": [{"recording_path": "capture.wav"}]}}]}))
        for source in (protocol, manifest, raw, self.recording):
            for alias_kind in ("same", "symlink", "hardlink"):
                with self.subTest(source=source.name, alias=alias_kind):
                    output = source if alias_kind == "same" else self.root / "controlled-output"
                    if alias_kind == "symlink": output.symlink_to(source)
                    elif alias_kind == "hardlink": os.link(source, output)
                    original = source.read_bytes()
                    with patch("echosight.controlled.process_controlled_protocol") as work:
                        self.assertEqual(main(["controlled", str(protocol), "--output", str(output)]), 2)
                        work.assert_not_called()
                    self.assertEqual(source.read_bytes(), original)
                    if alias_kind != "same": output.unlink()

    def test_processing_alias_change_is_checked_for_every_publication(self):
        for command, inputs, processor in self.commands():
            if command[0] in ("export", "replay"):
                continue
            with self.subTest(command=command[0]):
                output = self.root / "late-output"
                source = inputs[0]
                original = source.read_bytes()
                def work(*args, **kwargs):
                    output.symlink_to(source)
                    return {"status": "no_result", "diagnostics": []}
                # Metadata is deliberately minimal; mocked processing isolates publication.
                with patch(processor, side_effect=work), patch("echosight.interpretation.build_material_profile", return_value={}):
                    self.assertEqual(main([*command, "--output", str(output)]), 2)
                self.assertEqual(source.read_bytes(), original)
                self.assertTrue(output.is_symlink())
                output.unlink()
        output = self.root / "late-output"
        protocol = self.root / "protocol.json"
        protocol.write_text('{}')
        def controlled(*args, **kwargs):
            output.symlink_to(protocol)
            return {}
        with patch("echosight.controlled.process_controlled_protocol", side_effect=controlled):
            self.assertEqual(main(["controlled", str(protocol), "--output", str(output)]), 2)
        self.assertEqual(protocol.read_text(), '{}')

    def test_export_rechecks_after_processing_before_archive_publication(self):
        output = self.root / "archive.zip"
        def processed(*args):
            output.symlink_to(self.recording)
        with patch("echosight.storage.load_session", return_value={"captures": []}), \
             patch("echosight.storage.SessionStore") as store, \
             patch("echosight.cli._run_stored_session", side_effect=processed):
            store.return_value.__enter__.return_value.create_session.return_value = {"session_id": "s"}
            self.assertEqual(main(["export", str(self.session), "--output", str(output)]), 2)
            store.return_value.__enter__.return_value.export_session.assert_not_called()
        self.assertEqual(self.recording.read_bytes(), b"original recording")
        self.assertTrue(output.is_symlink())

    def test_replay_protects_store_internal_paths_and_external_hardlinks_before_open(self):
        store = self.root / "store"
        manifest = store / "sessions" / "s" / "session.json"
        manifest.parent.mkdir(parents=True)
        manifest.write_bytes(b"existing manifest")
        alias = self.root / "manifest-alias"
        os.link(manifest, alias)
        directory_alias = self.root / "store-alias"
        directory_alias.symlink_to(store, target_is_directory=True)
        outputs = [manifest, store / "jobs" / "new.json", store / ".store.lock", alias,
                   directory_alias / "sessions" / "new" / "session.json"]
        for output in outputs:
            with self.subTest(output=output), patch("echosight.storage.SessionStore") as opened:
                self.assertEqual(main(["replay", str(self.extra), "--store", str(store), "--output", str(output)]), 2)
                opened.assert_not_called()
        self.assertEqual(manifest.read_bytes(), b"existing manifest")
        self.assertTrue(alias.samefile(manifest))

    def test_replay_protects_new_paths_below_symlinked_store_directories(self):
        store = self.root / "store"
        store.mkdir()
        outside = self.root / "outside"
        outside.mkdir()
        (store / "sessions").symlink_to(outside, target_is_directory=True)
        output = store / "sessions" / "new-session" / "session.json"
        with patch("echosight.storage.SessionStore") as opened:
            self.assertEqual(main(["replay", str(self.extra), "--store", str(store), "--output", str(output)]), 2)
            opened.assert_not_called()
        self.assertFalse((outside / "new-session").exists())

    def test_replay_rechecks_after_processing(self):
        output = self.root / "result.json"
        def processed(*args):
            output.symlink_to(self.extra)
            return {"status": "no_result"}
        with patch("echosight.storage.SessionStore") as store, \
             patch("echosight.cli._run_stored_session", side_effect=processed):
            store.return_value.__enter__.return_value.import_archive.return_value = {"session_id": "s"}
            self.assertEqual(main(["replay", str(self.extra), "--store", str(self.root / "store"), "--output", str(output)]), 2)
        self.assertEqual(self.extra.read_text(), '{}')
        self.assertTrue(output.is_symlink())

    def test_real_comparison_replaces_unrelated_output_and_preserves_inputs(self):
        from echosight.evolution import compare_results
        output = self.root / "comparison.json"
        output.write_text('{"old":true}')
        self.session.write_text('{}')
        before = {p: p.read_bytes() for p in (self.session, self.extra)}
        self.assertEqual(main(["compare", str(self.session), str(self.extra), "--output", str(output)]), 0)
        self.assertEqual(json.loads(output.read_text()), compare_results({}, {}))
        for path, raw in before.items(): self.assertEqual(path.read_bytes(), raw)

    def test_probe_refuses_either_existing_output_without_generating(self):
        for name in ("probe.wav", "probe.json"):
            for alias_kind in ("regular", "symlink", "hardlink", "dangling"):
                with self.subTest(name=name, alias=alias_kind):
                    target = self.root / name
                    if alias_kind == "regular": target.write_bytes(b"old probe")
                    elif alias_kind == "symlink": target.symlink_to(self.recording)
                    elif alias_kind == "hardlink": os.link(self.recording, target)
                    else: target.symlink_to(self.root / "missing")
                    with patch("echosight.signals.generate_playback") as generate:
                        self.assertEqual(main(["probe", str(self.root)]), 2)
                        generate.assert_not_called()
                    self.assertTrue(target.exists() or target.is_symlink())
                    self.assertEqual(self.recording.read_bytes(), b"original recording")
                    target.unlink()

    def test_probe_rechecks_both_targets_after_generation(self):
        import numpy as np
        target = self.root / "probe.json"
        def generate(*args, **kwargs):
            target.symlink_to(self.extra)
            return np.zeros(2), {"sample_rate_hz": 48000}
        with patch("echosight.signals.generate_playback", side_effect=generate):
            self.assertEqual(main(["probe", str(self.root)]), 2)
        self.assertTrue(target.is_symlink())
        self.assertEqual(self.extra.read_text(), '{}')
        self.assertFalse((self.root / "probe.wav").exists())
        self.assertEqual(self.stdout.getvalue(), "")

    def test_probe_can_generate_into_directory_with_unrelated_files(self):
        import numpy as np
        with patch("echosight.signals.generate_playback", return_value=(np.zeros(2), {"sample_rate_hz": 48000})):
            self.assertEqual(main(["probe", str(self.root)]), 0)
        self.assertTrue((self.root / "probe.wav").is_file())
        self.assertIn("playback_wav_sha256", json.loads((self.root / "probe.json").read_text()))
        self.assertEqual(self.recording.read_bytes(), b"original recording")

    def test_demo_context_is_saved_during_initial_manifest_publication(self):
        context = {"schema_version": "1.0", "route_id": "local", "profiles": [],
                   "maximum_squared_distance": 10, "minimum_views": 1}
        self.extra.write_text(json.dumps(context))
        original = self.extra.read_bytes()
        destination = self.root / "demo"
        result = {"status": "no_result", "surfaces": [], "diagnostics": []}
        with patch("echosight.cli.process_session", return_value=result) as process:
            self.assertEqual(main(["demo", str(destination), "--scenario", "null", "--captures", "4",
                                   "--interpretation-context", str(self.extra)]), 0)
            processed_session = process.call_args.args[0]
        manifest = json.loads((destination / "session.json").read_text())
        self.assertEqual(manifest["interpretation_context"], context)
        self.assertEqual(processed_session["interpretation_context"], context)
        self.assertEqual(len(manifest["captures"]), 4)
        self.assertTrue(all(Path(capture["recording_path"]).is_file()
                            for capture in processed_session["captures"]))
        self.assertEqual(self.extra.read_bytes(), original)
        self.assertEqual(json.loads((destination / "result.json").read_text()), result)

    def test_demo_results_preflight_before_simulation(self):
        for command, names in (("demo", ("result.json",)),
                               ("refine-demo", ("initial-result.json", "result.json", "comparison.json"))):
            for name in names:
                with self.subTest(command=command, name=name):
                    target = self.root / name
                    target.write_bytes(b"old result")
                    with patch("echosight.simulation.simulate_session") as simulate:
                        self.assertEqual(main([command, str(self.root)]), 2)
                        simulate.assert_not_called()
                    self.assertEqual(target.read_bytes(), b"old result")
                    target.unlink()


if __name__ == "__main__":
    unittest.main()
