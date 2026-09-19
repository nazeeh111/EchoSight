"""Small local command-line interface, also used by reproducible demonstrations."""
from __future__ import annotations

import argparse
import hashlib
import json
import signal
import sys
import threading
from pathlib import Path

from .pipeline import process_session, save_result


def _summary(result):
    return {"session_id": result.get("session_id"), "result_id": result.get("result_id"),
            "status": result.get("status"), "surface_count": len(result.get("surfaces", [])),
            "hypothesis_count": len(result.get("hypotheses", [])),
            "dimensions": result.get("dimensions", []), "runtime_s": result.get("runtime_s"),
            "provenance": result.get("provenance"), "diagnostics": result.get("diagnostics", [])}


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
    command.add_argument("--captures", type=int, default=8)
    command = sub.add_parser("process", help="infer structure from a recording session")
    command.add_argument("session", type=Path)
    command.add_argument("--output", type=Path, required=True)
    command.add_argument("--method", choices=("mapper", "baseline"), default="mapper")
    command = sub.add_parser("demo", help="generate and process reproducible synthetic recordings")
    command.add_argument("directory", type=Path)
    command.add_argument("--scenario", default="room")
    command.add_argument("--seed", type=int, default=1)
    command.add_argument("--captures", type=int, default=8)
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
            if args.command == "demo":
                from .simulation import simulate_session
                session = simulate_session(args.directory, scenario=args.scenario, seed=args.seed, capture_count=args.captures)
                destination = args.directory / "result.json"
            else:
                session, destination = args.session, args.output
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
            result = compare_results(json.loads(args.previous.read_text()), json.loads(args.current.read_text()))
            save_result(result, args.output)
            print(json.dumps(result, indent=2, allow_nan=False))
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
    except (ValueError, OSError, KeyError, TypeError) as exc:
        print(f"EchoSight error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
