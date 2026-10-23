"""Prevent generated artifacts and exports from replacing retained input bytes."""
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from echosight.pipeline import save_result
from echosight.simulation import simulate_session
from echosight.storage import SessionStore
from tests.test_storage import wav_bytes


class OutputPreservationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)

    def test_exclusive_json_publishes_complete_bytes_and_preserves_prior_destinations(self):
        target = self.root / 'result.json'
        save_result({'status': 'partial'}, target, overwrite=False)
        original = target.read_bytes()
        with self.assertRaises(FileExistsError): save_result({'status': 'no_result'}, target, overwrite=False)
        self.assertEqual(target.read_bytes(), original)
        save_result({'status': 'no_result'}, target)  # Explicit result replacement still works.
        self.assertEqual(json.loads(target.read_text())['status'], 'no_result')
        self.assertFalse(list(self.root.glob('.echosight-*')))

    def test_exclusive_json_late_writer_and_dangling_symlink_remain_untouched(self):
        target = self.root / 'result.json'
        real_link = os.link
        def competing_writer(source, destination):
            Path(destination).write_bytes(b'concurrent owner')
            return real_link(source, destination)
        with patch('echosight.pipeline.os.link', side_effect=competing_writer):
            with self.assertRaises(FileExistsError): save_result({'status': 'partial'}, target, overwrite=False)
        self.assertEqual(target.read_bytes(), b'concurrent owner')
        link = self.root / 'link.json'; link.symlink_to(self.root / 'absent.json')
        with self.assertRaises(FileExistsError): save_result({}, link, overwrite=False)
        self.assertTrue(link.is_symlink()); self.assertFalse((self.root / 'absent.json').exists())
        self.assertFalse(list(self.root.glob('.echosight-*')))

    def test_simulation_preflights_whole_group_before_writing_anything(self):
        for name in ('capture-03.wav', 'probe.wav', 'session.json', 'truth.json'):
            with self.subTest(name=name), tempfile.TemporaryDirectory(dir=self.root) as folder:
                root = Path(folder); target = root / name; target.write_bytes(b'precious original')
                with self.assertRaises(FileExistsError): simulate_session(root, 'null', capture_count=4)
                self.assertEqual(target.read_bytes(), b'precious original')
                self.assertEqual(list(root.iterdir()), [target])

    def test_simulation_preserves_broken_links_and_accepts_unrelated_files(self):
        bad = self.root / 'bad'; bad.mkdir(); link = bad / 'truth.json'; link.symlink_to('absent.json')
        with self.assertRaises(FileExistsError): simulate_session(bad, 'null', capture_count=4)
        self.assertTrue(link.is_symlink()); self.assertFalse((bad / 'probe.wav').exists())
        good = self.root / 'good'; good.mkdir(); note = good / 'notes.txt'; note.write_bytes(b'keep')
        manifest = simulate_session(good, 'null', seed=7, capture_count=4)
        self.assertEqual(len(json.loads(manifest.read_text())['captures']), 4)
        self.assertEqual(note.read_bytes(), b'keep')

    def test_simulation_never_truncates_a_recording_created_after_preflight(self):
        import echosight.simulation as simulation
        root = self.root / 'race'; real_write = simulation.wavfile.write; calls = []
        def competing_writer(stream, *args, **kwargs):
            if not calls:
                (root / 'capture-01.wav').write_bytes(b'concurrent recording')
            calls.append(1); return real_write(stream, *args, **kwargs)
        with patch.object(simulation.wavfile, 'write', side_effect=competing_writer):
            with self.assertRaises(FileExistsError): simulate_session(root, 'null', capture_count=4)
        self.assertEqual((root / 'capture-01.wav').read_bytes(), b'concurrent recording')
        self.assertFalse((root / 'session.json').exists())

    def test_store_export_protects_internal_metadata_raw_bytes_and_lock(self):
        source = self.root / 'input.wav'; source.write_bytes(wav_bytes())
        with SessionStore(self.root / 'store') as store:
            sid = store.create_session({'session_id': 'survey'})['session_id']
            capture = store.add_recording(sid, source, {'capture_id': 'c', 'provenance': 'supplied'})
            directory = store.root / 'sessions' / sid
            targets = [directory / 'session.json', directory / capture['recording_path'],
                       store.root / '.store.lock', store.root / 'jobs' / 'new.json']
            originals = {p: p.read_bytes() for p in targets if p.exists()}
            for target in targets:
                with self.subTest(target=target), self.assertRaises(ValueError): store.export_session(sid, target)
            for p, original in originals.items(): self.assertEqual(p.read_bytes(), original)
            self.assertFalse(targets[-1].exists())
            archive = store.export_session(sid)
            self.assertTrue(archive.is_file())

    def test_store_export_rejects_symlink_and_hardlink_aliases_before_writing(self):
        with SessionStore(self.root / 'store') as store:
            sid = store.create_session({'session_id': 'survey'})['session_id']
            original = store.root / 'sessions' / sid / 'session.json'; before = original.read_bytes()
            for name, kind in [('symbolic', 'symlink'), ('hard', 'hardlink')]:
                alias = self.root / name
                if kind == 'symlink': alias.symlink_to(original)
                else: os.link(original, alias)
                with self.assertRaises(ValueError): store.export_session(sid, alias)
                self.assertEqual(original.read_bytes(), before); self.assertEqual(alias.read_bytes(), before)
            alias_dir = self.root / 'aliased'; alias_dir.symlink_to(store.root / 'jobs', target_is_directory=True)
            with self.assertRaises(ValueError): store.export_session(sid, alias_dir / 'new.json')
            self.assertFalse((store.root / 'jobs' / 'new.json').exists())

    def test_store_export_rechecks_alias_after_building_archive(self):
        import zipfile
        with SessionStore(self.root / 'store') as store:
            sid = store.create_session({'session_id': 'survey'})['session_id']
            original = store.root / 'sessions' / sid / 'session.json'; before = original.read_bytes()
            target = self.root / 'late.zip'; real_close = zipfile.ZipFile.close
            def change_after_close(archive):
                real_close(archive)
                if not target.is_symlink(): target.symlink_to(original)
            with patch.object(zipfile.ZipFile, 'close', change_after_close):
                with self.assertRaises(ValueError): store.export_session(sid, target)
            self.assertTrue(target.is_symlink()); self.assertEqual(original.read_bytes(), before)
            self.assertFalse(list(self.root.glob('.export-*')))

    def test_malformed_recording_parent_retains_diagnostic_result_behavior(self):
        import contextlib
        import io
        from echosight.cli import main
        (self.root / 'plain').write_bytes(b'not a directory')
        session = self.root / 'session.json'
        session.write_text(json.dumps({'captures': [{'capture_id': 'c', 'recording_path': 'plain/capture.wav'}]}))
        output = self.root / 'result.json'; output.write_text('{}')
        stdout, stderr = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
            self.assertEqual(main(['process', str(session), '--output', str(output)]), 0, stderr.getvalue())
        self.assertEqual(json.loads(output.read_text())['status'], 'no_result')
        self.assertEqual((self.root / 'plain').read_bytes(), b'not a directory')

    def test_store_export_preserves_outward_links_with_reserved_location(self):
        with SessionStore(self.root / 'store') as store:
            first = store.create_session({'session_id': 'first'})['session_id']
            second = store.create_session({'session_id': 'second'})['session_id']
            path = store.root / 'sessions' / second / 'session.json'
            original = path.read_bytes(); outside = self.root / 'outside.json'; outside.write_bytes(original)
            path.unlink(); path.symlink_to(outside)
            for target in (path, self.root / 'alias' / 'sessions' / second / 'session.json'):
                if target != path: (self.root / 'alias').symlink_to(store.root, target_is_directory=True)
                with self.assertRaises(ValueError): store.export_session(first, target)
                self.assertTrue(path.is_symlink()); self.assertEqual(outside.read_bytes(), original)
            linked = store.root / 'sessions' / second / 'external'; linked.symlink_to(self.root / 'external', target_is_directory=True)
            (self.root / 'external').mkdir()
            with self.assertRaises(ValueError): store.export_session(first, linked / 'new.zip')
            self.assertFalse((self.root / 'external/new.zip').exists())
