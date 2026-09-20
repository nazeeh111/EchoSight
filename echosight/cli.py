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


def _summary(result):
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


def _read_json_file(path):
    from .storage import MAX_JSON_BYTES
    with Path(path).open('rb') as stream:
        raw = stream.read(MAX_JSON_BYTES + 1)
    if len(raw) > MAX_JSON_BYTES:
        raise ValueError('input metadata exceeds 1 MiB')
    return json.loads(raw)


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
    args = parser.parse_args(argv)
    try:
        if args.command == "probe":
            import numpy as np
            from scipy.io.wavfile import write
            from .signals import generate_playback
            args.directory.mkdir(parents=True, exist_ok=True)
            samples, metadata = generate_playback({"period_s": args.period}, channel=args.channel)
            rate = metadata["sample_rate_hz"]
            write(args.directory / "probe.wav", rate, np.round(np.clip(samples, -1, 1) * 32767).astype(np.int16))
            metadata["playback_wav_sha256"] = hashlib.sha256((args.directory / "probe.wav").read_bytes()).hexdigest()
            save_result(metadata, args.directory / "probe.json")
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
                session = simulate_session(args.directory, scenario=args.scenario, seed=args.seed, capture_count=args.captures)
                destination = args.directory / "result.json"
            else:
                session, destination = args.session, args.output
            if args.interpretation_context is not None:
                from .storage import load_session
                session_path = session
                session = load_session(session_path)
                session['interpretation_context'] = supplied_context
                if args.command == 'demo':
                    # Keep the generated demo reproducible, including its interpretation input.
                    saved = _read_json_file(session_path)
                    saved['interpretation_context'] = supplied_context
                    save_result(saved, session_path)
            cancelled = threading.Event()
            previous_handler = signal.signal(signal.SIGINT, lambda *_: cancelled.set())
            try:
                result = process_session(session, cancel=cancelled.is_set,
                                         method=getattr(args, "method", "mapper"))
            finally:
                signal.signal(signal.SIGINT, previous_handler)
            save_result(result, destination)
            print(json.dumps(_summary(result), indent=2, allow_nan=False))
            print(f"Saved: {destination}")
            if result.get("status") == "cancelled":
                return 130
        elif args.command == "inspect":
            print(json.dumps(_summary(json.loads(args.result.read_text())), indent=2, allow_nan=False))
        elif args.command == "compare":
            from .evolution import compare_results
            from .storage import MAX_JSON_BYTES, MAX_RESULT_BYTES
            def read_comparison_input(path, limit):
                with path.open('rb') as stream: raw = stream.read(limit + 1)
                if len(raw) > limit: raise ValueError("comparison input exceeds byte limit")
                return json.loads(raw)
            prior = read_comparison_input(args.previous_comparison, MAX_JSON_BYTES) if args.previous_comparison else None
            result = compare_results(read_comparison_input(args.previous, MAX_RESULT_BYTES),
                                     read_comparison_input(args.current, MAX_RESULT_BYTES), previous_comparison=prior)
            save_result(result, args.output)
            print(json.dumps(result, indent=2, allow_nan=False))
        elif args.command == "controlled":
            from .controlled import process_controlled_protocol
            cancelled=threading.Event()
            previous_handler=signal.signal(signal.SIGINT,lambda *_:cancelled.set())
            try:result=process_controlled_protocol(args.protocol,cancel=cancelled.is_set)
            finally:signal.signal(signal.SIGINT,previous_handler)
            save_result(result,args.output)
            print(json.dumps({k:result[k] for k in ('status','diagnostics','physical_validation')},indent=2))
            if result['status']=='cancelled':return 130
            if result['status']=='inconclusive':return 2
        elif args.command == "calibrate-reference":
            from .calibration import calibrate_reference
            if args.reference.stat().st_size > 1024 * 1024:
                raise ValueError("reference metadata exceeds 1 MiB")
            result = calibrate_reference(args.session, json.loads(args.reference.read_text()))
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
            save_result(before, args.directory / "initial-result.json")
            save_result(after, args.directory / "result.json")
            save_result(comparison, args.directory / "comparison.json")
            print(json.dumps({"initial": _summary(before), "refined": _summary(after), "comparison": comparison}, indent=2, allow_nan=False))
        elif args.command == "export":
            from .storage import SessionStore, load_session
            source = load_session(args.session)
            with tempfile.TemporaryDirectory(prefix="echosight-export-") as temp, SessionStore(temp) as store:
                session = store.create_session(dict(source, captures=[]))
                for capture in source["captures"]:
                    path = Path(capture["recording_path"])
                    if path.stat().st_size > 64 * 1024 * 1024:
                        raise ValueError("recording exceeds 64 MiB")
                    if capture.get("sha256") and hashlib.sha256(path.read_bytes()).hexdigest() != capture["sha256"]:
                        raise ValueError("recording checksum differs from manifest")
                    metadata = {key: capture[key] for key in ("capture_id", "receiver_position_m", "receiver_position_std_m", "provenance", "device_id", "receiver_pose_group_id", "notes") if key in capture}
                    store.add_recording(session["session_id"], path, metadata)
                _run_stored_session(store, session["session_id"])
                store.export_session(session["session_id"], args.output)
            print(args.output)
        elif args.command == "replay":
            from .storage import SessionStore
            with SessionStore(args.store) as store:
                session = store.import_archive(args.archive)
                result = _run_stored_session(store, session["session_id"])
                save_result(result, args.output)
            print(json.dumps(_summary(result), indent=2, allow_nan=False))
        elif args.command == "serve":
            from .api import create_server
            server = create_server(args.root, host=args.host, port=args.port, processor=process_session)
            print(f"EchoSight API: http://{args.host}:{server.server_address[1]}", flush=True)
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
    except (ValueError, OSError, KeyError, TypeError, RuntimeError) as exc:
        print(f"EchoSight error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
