"""Small local command-line interface, also used by reproducible demonstrations."""
from __future__ import annotations

import argparse
import hashlib
import json
import signal
import sys
import tempfile
import threading
import time
from pathlib import Path

from .pipeline import process_session, save_result
from .fileio import require_distinct_output as _require_distinct_output, require_new_outputs, require_store_output, read_json_object, read_bytes_bounded


def _summary(result):
    if not isinstance(result, dict):
        raise ValueError('result must be an object')
    for field in ('surfaces', 'hypotheses'):
        items = result.get(field, [])
        if not isinstance(items, list) or any(not isinstance(item, dict) for item in items):
            raise ValueError(f'{field} must be an array of objects')
    if result.get('interpretation') is not None and not isinstance(result['interpretation'], dict):
        raise ValueError('interpretation must be an object')
    summary = {"session_id": result.get("session_id"), "result_id": result.get("result_id"),
            "status": result.get("status"), "surface_count": len(result.get("surfaces", [])),
            "hypothesis_count": len(result.get("hypotheses", [])),
            "dimensions": result.get("dimensions", []), "runtime_s": result.get("runtime_s"),
            "provenance": result.get("provenance"), "diagnostics": result.get("diagnostics", [])}
    if isinstance(result.get('interpretation'), dict):
        interpretation = result['interpretation']
        entries = interpretation.get('surface_interpretations', [])
        if not isinstance(entries, list) or any(not isinstance(entry, dict) for entry in entries):
            raise ValueError('invalid interpretation surface summaries')
        summary['interpretation'] = {key: interpretation.get(key) for key in ('status', 'context_id')}
        summary['interpretation']['surface_interpretations'] = [
            {key: entry.get(key) for key in ('surface_id', 'material', 'appearance')}
            for entry in entries]
    return summary


def _read_json_file(path, *, limit=None):
    if limit is None:
        from .storage import MAX_JSON_BYTES
        limit = MAX_JSON_BYTES
    return read_json_object(path, limit)


def _input_reference_definition(path):
    # Path discovery is deliberately tolerant, matching backend session/protocol
    # decoding: even invalid definitions must not lose protection of named audio.
    from .storage import MAX_JSON_BYTES
    return json.loads(read_bytes_bounded(path, MAX_JSON_BYTES))


def _recording_paths(spec, base):
    """Discover recording names without validating metadata or reading audio."""
    captures = spec.get("captures", []) if isinstance(spec, dict) else []
    if not isinstance(captures, list):
        return []
    return [base / capture["recording_path"] for capture in captures
            if isinstance(capture, dict) and isinstance(capture.get("recording_path"), str)
            and capture["recording_path"] and "\0" not in capture["recording_path"]]


def _session_input_paths(session):
    inputs = [session]
    try:
        inputs.extend(_recording_paths(_input_reference_definition(session), session.parent))
    except (ValueError, OSError, TypeError):
        # In particular, process retains its ordinary invalid_session result.
        pass
    return inputs


def _command_input_paths(args):
    command = args.command
    if command in ("process", "calibrate-reference", "material-reference", "export"):
        inputs = _session_input_paths(args.session)
        for name in ("interpretation_context", "reference", "provenance", "appearance"):
            path = getattr(args, name, None)
            if path is not None:
                inputs.append(path)
        return inputs
    if command == "compare":
        return [p for p in (args.previous, args.current, args.previous_comparison) if p is not None]
    if command == "replay":
        return [args.archive]
    if command == "controlled":
        inputs = [args.protocol]
        try:
            protocol = _input_reference_definition(args.protocol)
            epochs = protocol.get("epochs", []) if isinstance(protocol, dict) else []
            for epoch in epochs if isinstance(epochs, list) else []:
                session = epoch.get("session") if isinstance(epoch, dict) else None
                if isinstance(session, str) and session and "\0" not in session:
                    inputs.extend(_session_input_paths(args.protocol.parent / session))
                elif isinstance(session, dict):
                    inputs.extend(_recording_paths(session, args.protocol.parent))
        except (ValueError, OSError, TypeError):
            pass
        return inputs
    return []


def _require_replay_output(destination, root):
    """Keep caller result publication outside mutable store internals."""
    require_store_output(destination, root)
    if not destination.exists():
        return  # A fresh output cannot be an existing hardlink alias.
    root = root.resolve()
    inputs = [root / ".store.lock"]
    for name in ("sessions", "jobs"):
        directory = root / name
        if directory.is_dir():
            inputs.extend(path for path in directory.rglob("*") if path.is_file())
    _require_distinct_output(destination, inputs)


def _run_stored_session(store, session_id):
    job = store.start_job(session_id, process_session)
    try:
        while job["status"] in ("queued", "running"):
            time.sleep(.02)
            job = store.get_job(job["job_id"])
    except KeyboardInterrupt:
        store.cancel_job(job["job_id"])
        raise
    if job["status"] != "completed":
        raise ValueError(f"processing {job['status']}: {job.get('error', {})}")
    return store.get_result(session_id)


def main(argv=None):
    parser = argparse.ArgumentParser(description="EchoSight acoustic backend")
    sub = parser.add_subparsers(dest="command", required=True)
    command = sub.add_parser("nlos-fig2", help="reconstruct the pinned external measured Fig2 ultrasound scene offline")
    command.add_argument("--input", type=Path, required=True, help="caller-provided exact official Fig2 MAT; never downloaded automatically")
    command.add_argument("--output", type=Path, required=True, help="new directory; preserves partial output on failure")
    command.add_argument("--preset", choices=("li2025-fig2-phase-native",), required=True)
    command.add_argument("--sample-rate-hz", type=int, choices=(1000000,), required=True)
    command.add_argument("--memory-budget-gib", type=float, default=6, help="declared budget, minimum6GiB estimate; not a hard RAM ceiling")
    command.add_argument("--estimate-only", action="store_true", help="verify exact input and print resources without decoding or creating output")
    command = sub.add_parser("probe", help="write a probe WAV and its exact metadata")
    command.add_argument("directory", type=Path)
    command.add_argument("--channel", choices=("mono", "left", "right"), default="left")
    command.add_argument("--period", type=float, default=1.0, help="seconds between chirps; 1 s for reverberant rooms")
    command = sub.add_parser("simulate", help="generate synthetic raw recordings, separate evaluation truth")
    command.add_argument("directory", type=Path)
    command.add_argument("--scenario", default="room")
    command.add_argument("--seed", type=int, default=1)
    command.add_argument("--captures", type=int, default=None)
    command = sub.add_parser("process", help="infer structure from a recording session")
    command.add_argument("session", type=Path)
    command.add_argument("--output", type=Path, required=True)
    command.add_argument("--method", choices=("mapper", "baseline"), default="mapper")
    command.add_argument("--interpretation-context", type=Path, help="bounded material/appearance context JSON for this processing run")
    command = sub.add_parser("demo", help="generate and process reproducible synthetic recordings")
    command.add_argument("directory", type=Path)
    command.add_argument("--scenario", default="room")
    command.add_argument("--seed", type=int, default=1)
    command.add_argument("--captures", type=int, default=None)
    command.add_argument("--interpretation-context", type=Path, help="material/appearance context JSON saved in the generated demo session")
    command = sub.add_parser("refine-demo", help="show what additional independent recording positions establish")
    command.add_argument("directory", type=Path)
    command.add_argument("--seed", type=int, default=1)
    command.add_argument("--initial-captures", type=int, default=4)
    command.add_argument("--captures", type=int, default=12)
    command = sub.add_parser("inspect", help="summarize a saved result")
    command.add_argument("result", type=Path)
    command = sub.add_parser("compare", help="explain changes in inference from two saved results")
    command.add_argument("previous", type=Path)
    command.add_argument("current", type=Path)
    command.add_argument("--output", type=Path, required=True)
    command.add_argument("--previous-comparison", type=Path, help="carry declared display tracks from the comparison ending at previous")
    command = sub.add_parser("material-reference", help="process raw reference recordings and build a supplied-label material profile")
    command.add_argument("session", type=Path)
    command.add_argument("--surface-id", required=True)
    command.add_argument("--material-id", required=True)
    command.add_argument("--label", required=True)
    command.add_argument("--route-id", required=True)
    command.add_argument("--provenance", type=Path, required=True, help="JSON object with kind and note for the supplied reference label")
    command.add_argument("--appearance", type=Path, help="optional supplied palette/provenance JSON")
    command.add_argument("--prior-weight", type=float, default=1.)
    command.add_argument("--regularization-std-db", type=float, default=0., help="explicit diagonal regularization assumption, in dB")
    command.add_argument("--output", type=Path, required=True)
    command = sub.add_parser("controlled", help="process declared A-before/B-first/B-repeat/A-return recordings")
    command.add_argument("protocol",type=Path)
    command.add_argument("--output",type=Path,required=True)
    command = sub.add_parser("calibrate-reference", help="test source/effective-speed calibration against an independently surveyed reference plane")
    command.add_argument("session", type=Path)
    command.add_argument("reference", type=Path)
    command.add_argument("--output", type=Path, required=True)
    command = sub.add_parser("export", help="import and process a local recording session, then archive originals and result")
    command.add_argument("session", type=Path)
    command.add_argument("--output", type=Path, required=True)
    command = sub.add_parser("replay", help="reload an archive and recompute geometry from original recordings")
    command.add_argument("archive", type=Path)
    command.add_argument("--store", type=Path, required=True)
    command.add_argument("--output", type=Path, required=True)
    command = sub.add_parser("serve", help="run the local HTTP API")
    command.add_argument("--root", type=Path, default=Path("work/store"))
    command.add_argument("--host", default="127.0.0.1")
    command.add_argument("--port", type=int, default=8765)
    command.add_argument("--ui", action="store_true", help="Enable the same-origin local processing workspace")
    args = parser.parse_args(argv)
    try:
        protected_inputs = _command_input_paths(args)
        # Retain initial targets as well as names if symlinks change while processing.
        protected_inputs += [path.resolve() for path in protected_inputs]
        def check_output():
            _require_distinct_output(args.output, protected_inputs)
            if args.command == "replay":
                _require_replay_output(args.output, args.store)
        if protected_inputs:
            check_output()
        generated_results = []
        if args.command == "demo":
            generated_results = [args.directory / "result.json"]
        elif args.command == "refine-demo":
            generated_results = [args.directory / name for name in
                                 ("initial-result.json", "result.json", "comparison.json")]
        if generated_results:
            require_new_outputs(generated_results)
            context = getattr(args, "interpretation_context", None)
            if context is not None:
                for destination in generated_results:
                    _require_distinct_output(destination, [context])
        if args.command == "nlos-fig2":
            from .nlos import process_fig2
            from subprocess import TimeoutExpired
            try:
                result=process_fig2(args.input,args.output,preset=args.preset,sample_rate_hz=args.sample_rate_hz,
                    memory_budget_gib=args.memory_budget_gib,estimate_only=args.estimate_only)
            except TimeoutExpired:
                raise RuntimeError('Measured NLOS exceeded300s wall deadline; worker stopped and partial output retained') from None
            print(json.dumps(result,indent=2,allow_nan=False))
        elif args.command == "probe":
            import numpy as np
            from scipy.io.wavfile import write
            from .signals import generate_playback
            require_new_outputs([args.directory / "probe.wav", args.directory / "probe.json"])
            args.directory.mkdir(parents=True, exist_ok=True)
            samples, metadata = generate_playback({"period_s": args.period}, channel=args.channel)
            rate = metadata["sample_rate_hz"]
            require_new_outputs([args.directory / "probe.wav", args.directory / "probe.json"])
            with (args.directory / "probe.wav").open("xb") as stream:
                write(stream, rate, np.round(np.clip(samples, -1, 1) * 32767).astype(np.int16))
            metadata["playback_wav_sha256"] = hashlib.sha256((args.directory / "probe.wav").read_bytes()).hexdigest()
            require_new_outputs([args.directory / "probe.json"])
            save_result(metadata, args.directory / "probe.json", overwrite=False)
            print(args.directory / "probe.wav")
        elif args.command == "simulate":
            from .simulation import simulate_session
            print(simulate_session(args.directory, scenario=args.scenario, seed=args.seed, capture_count=args.captures))
        elif args.command in ("process", "demo"):
            supplied_context = None
            if args.interpretation_context is not None:
                from .interpretation import validate_context
                supplied_context = validate_context(_read_json_file(args.interpretation_context))
            if args.command == "demo":
                from .simulation import simulate_session
                session = simulate_session(args.directory, scenario=args.scenario, seed=args.seed,
                                           capture_count=args.captures, interpretation_context=supplied_context)
                destination = args.directory / "result.json"
            else:
                session, destination = args.session, args.output
            if args.interpretation_context is not None:
                from .storage import load_session
                session_path = session
                session = load_session(session_path)
                session['interpretation_context'] = supplied_context
            cancelled = threading.Event()
            previous_handler = signal.signal(signal.SIGINT, lambda *_: cancelled.set())
            try:
                result = process_session(session, cancel=cancelled.is_set,
                                         method=getattr(args, "method", "mapper"))
            finally:
                signal.signal(signal.SIGINT, previous_handler)
            if protected_inputs:
                check_output()
            if generated_results:
                require_new_outputs(generated_results)
            save_result(result, destination, overwrite=not bool(generated_results))
            print(json.dumps(_summary(result), indent=2, allow_nan=False))
            print(f"Saved: {destination}")
            if result.get("status") == "cancelled":
                return 130
        elif args.command == "inspect":
            from .storage import MAX_RESULT_BYTES
            print(json.dumps(_summary(_read_json_file(args.result, limit=MAX_RESULT_BYTES)), indent=2, allow_nan=False))
        elif args.command == "compare":
            from .evolution import compare_results
            from .storage import MAX_RESULT_BYTES
            prior = _read_json_file(args.previous_comparison) if args.previous_comparison else None
            result = compare_results(_read_json_file(args.previous, limit=MAX_RESULT_BYTES),
                                     _read_json_file(args.current, limit=MAX_RESULT_BYTES), previous_comparison=prior)
            check_output()
            save_result(result, args.output)
            print(json.dumps(result, indent=2, allow_nan=False))
        elif args.command == "controlled":
            from .controlled import process_controlled_protocol
            cancelled=threading.Event()
            previous_handler=signal.signal(signal.SIGINT,lambda *_:cancelled.set())
            try:result=process_controlled_protocol(args.protocol,cancel=cancelled.is_set)
            finally:signal.signal(signal.SIGINT,previous_handler)
            check_output()
            save_result(result,args.output)
            print(json.dumps({k:result[k] for k in ('status','diagnostics','physical_validation')},indent=2))
            if result['status']=='cancelled':return 130
            if result['status']=='inconclusive':return 2
        elif args.command == "calibrate-reference":
            from .calibration import calibrate_reference
            result = calibrate_reference(args.session, _read_json_file(args.reference))
            check_output()
            save_result(result, args.output)
            print(json.dumps({"status": result["status"], "diagnostics": result["diagnostics"],
                              "calibration_id": result.get("calibration_id")}, indent=2))
            if result["status"] != "calibration_proposal":
                return 2
        elif args.command == "material-reference":
            from .interpretation import build_material_profile
            provenance = _read_json_file(args.provenance)
            appearance = _read_json_file(args.appearance) if args.appearance else None
            cancelled = threading.Event()
            previous_handler = signal.signal(signal.SIGINT, lambda *_: cancelled.set())
            try:
                result = process_session(args.session, cancel=cancelled.is_set)
            finally:
                signal.signal(signal.SIGINT, previous_handler)
            if result.get('status') == 'cancelled':
                return 130
            profile = build_material_profile(result, args.surface_id, material_id=args.material_id,
                label=args.label, route_id=args.route_id, prior_weight=args.prior_weight,
                regularization_std_db=args.regularization_std_db, appearance=appearance, provenance=provenance)
            check_output()
            save_result(profile, args.output)
            print(json.dumps({'material_id': profile['material_id'], 'reference_summary': profile['reference_summary']}, indent=2))
        elif args.command == "refine-demo":
            from .simulation import simulate_session
            from .storage import load_session
            from .evolution import compare_results
            if not 3 <= args.initial_captures < args.captures:
                raise ValueError("initial capture count must be at least 3 and below final count")
            session = load_session(simulate_session(args.directory, seed=args.seed, capture_count=args.captures))
            initial = dict(session, captures=session["captures"][:args.initial_captures])
            before, after = process_session(initial), process_session(session)
            comparison = compare_results(before, after)
            require_new_outputs(generated_results)
            save_result(before, args.directory / "initial-result.json", overwrite=False)
            save_result(after, args.directory / "result.json", overwrite=False)
            save_result(comparison, args.directory / "comparison.json", overwrite=False)
            print(json.dumps({"initial": _summary(before), "refined": _summary(after), "comparison": comparison}, indent=2, allow_nan=False))
        elif args.command == "export":
            from .storage import SessionStore, load_session
            source = load_session(args.session)
            with tempfile.TemporaryDirectory(prefix="echosight-export-") as temp, SessionStore(temp) as store:
                session = store.create_session(dict(source, captures=[]))
                for capture in source["captures"]:
                    path = Path(capture["recording_path"])
                    metadata = {key: capture[key] for key in ("capture_id", "receiver_position_m", "receiver_position_std_m", "provenance", "device_id", "receiver_pose_group_id", "notes") if key in capture}
                    store.add_recording(session["session_id"], path, metadata,
                                        expected_sha256=capture.get("sha256"))
                _run_stored_session(store, session["session_id"])
                check_output()
                store.export_session(session["session_id"], args.output)
            print(args.output)
        elif args.command == "replay":
            from .storage import SessionStore
            with SessionStore(args.store) as store:
                session = store.import_archive(args.archive)
                result = _run_stored_session(store, session["session_id"])
                check_output()
                save_result(result, args.output)
            print(json.dumps(_summary(result), indent=2, allow_nan=False))
        elif args.command == "serve":
            from .api import create_server
            server = create_server(args.root, host=args.host, port=args.port, processor=process_session, ui=args.ui)
            print(f"EchoSight API: http://{args.host}:{server.server_address[1]}", flush=True)
            if args.ui: print(f"Processing workspace: http://{args.host}:{server.server_address[1]}/ui/results.html", flush=True)
            try:
                server.serve_forever()
            except KeyboardInterrupt:
                pass
            finally:
                server.server_close()
        return 0
    except KeyboardInterrupt:
        print("EchoSight cancelled", file=sys.stderr)
        return 130
    except (ValueError, OSError, KeyError, TypeError, RuntimeError, OverflowError) as exc:
        print(f"EchoSight error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
