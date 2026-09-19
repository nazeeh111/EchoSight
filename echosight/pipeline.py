"""Recording-to-scene orchestration shared by CLI, HTTP and evaluation."""
from __future__ import annotations

import hashlib
import importlib.metadata
import json
import os
import platform
import tempfile
import time
from pathlib import Path

from . import __version__


def save_result(result: dict, destination: str | Path) -> Path:
    """Atomically persist JSON; never emit nonstandard NaN/Infinity values."""
    payload = json.dumps(result, indent=2, sort_keys=True, allow_nan=False) + "\n"
    destination = Path(destination)
    destination.parent.mkdir(parents=True, exist_ok=True)
    fd, temp = tempfile.mkstemp(prefix=".echosight-", dir=destination.parent)
    try:
        with os.fdopen(fd, "w") as stream:
            stream.write(payload)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temp, destination)
    finally:
        if os.path.exists(temp):
            os.unlink(temp)
    return destination


def _empty(session: dict, status: str, diagnostics: list) -> dict:
    return {"schema_version": "1.0", "session_id": session.get("session_id"),
            "status": status, "surfaces": [], "hypotheses": [], "dimensions": [],
            "guidance": [], "diagnostics": diagnostics, "observations": [],
            "provenance": {"software_version": __version__, "physical_validation": False}}


def process_session(session: dict | str | Path, cancel=None, progress=None,
                    *, method: str = "mapper") -> dict:
    """Process raw records without accepting scene truth or preassigned echoes.

    `cancel` is a zero-argument predicate. `progress` receives fraction/message.
    A rejected capture remains visible and does not erase other evidence.
    """
    start = time.perf_counter()
    cancel = cancel or (lambda: False)
    progress = progress or (lambda fraction, message="": None)
    if cancel():
        return _empty(session if isinstance(session, dict) else {}, "cancelled", [])
    from .storage import load_session, validate_session, read_recording_snapshot
    from .signals import process_recording
    from .inference import infer_scene, infer_baseline

    if method not in ("mapper", "baseline"):
        raise ValueError("method must be mapper or baseline")
    try:
        session = load_session(session) if isinstance(session, (str, Path)) else validate_session(session)
    except (ValueError, OSError, TypeError) as exc:
        return _empty(session if isinstance(session, dict) else {}, "no_result",
                      [{"code": "invalid_session", "message": str(exc)}])

    missing = [key for key in ("session_id", "source_position_m", "probe") if not session.get(key)]
    missing += [f"{capture['capture_id']}.receiver_position_m" for capture in session["captures"]
                if capture.get("receiver_position_m") is None]
    if missing:
        return _empty(session, "no_result", [{"code": "missing_calibration",
                      "message": "Supply required acquisition metadata: " + ", ".join(missing)}])

    observations = []
    fingerprints = []
    captures = session.get("captures", [])
    progress(0.0, "Validating recordings")
    for index, capture in enumerate(captures):
        if cancel():
            result = _empty(session, "cancelled", [])
            result["observations"] = observations
            return result
        capture_id = capture["capture_id"]
        try:
            path = Path(capture["recording_path"])
            samples, rate, digest = read_recording_snapshot(path)
            if capture.get("sha256") is not None and digest != capture["sha256"]:
                raise ValueError("recording checksum differs from its imported manifest")
            observation = process_recording(samples, rate, session["probe"], capture_id,
                                            sound_speed_m_s=session.get("sound_speed_m_s", 343.0),
                                            cancel=cancel)
            observation["recording_sha256"] = digest
            fingerprints.append({"capture_id": capture_id, "sha256": digest})
        except (OSError, ValueError, KeyError) as exc:
            observation = {"capture_id": capture_id, "status": "rejected", "candidates": [],
                           "diagnostics": [{"code": "recording_rejected", "message": str(exc)}]}
        observation.update({"capture_id": capture_id,
                            "receiver_position_m": capture["receiver_position_m"],
                            "receiver_position_std_m": capture.get("receiver_position_std_m", 0.01),
                            "input_diagnostics": capture.get("diagnostics", []),
                            "input_format": capture.get("format", "unspecified_lossless"),
                            "provenance": capture.get("provenance", "measured")})
        observations.append(observation)
        progress(0.65 * (index + 1) / max(len(captures), 1), f"Processed capture {capture_id}")

    # Only calibrated acquisition information enters inference. Unknown keys,
    # annotations and scene truth are deliberately excluded from this boundary.
    keys = ("schema_version", "session_id", "sound_speed_m_s", "sound_speed_std_m_s",
            "source_clock_scale", "source_clock_std_ppm", "source_position_m",
            "source_position_std_m", "effective_speed_m_s", "source_effective_speed_covariance", "probe")
    fitting_session = {key: session[key] for key in keys if key in session}
    fitting_session["coordinate_frame_id"] = session.get("coordinate_frame_id", "session:" + session["session_id"])
    fitting_session["captures"] = [{key: capture[key] for key in
        ("capture_id", "receiver_position_m", "receiver_position_std_m", "provenance")
        if key in capture} for capture in captures]
    if cancel():
        result = _empty(session, "cancelled", [])
    elif method == "baseline":
        result = infer_baseline(fitting_session, observations)
    else:
        result = infer_scene(fitting_session, observations, cancel=cancel,
                             progress=lambda value, message="": progress(0.65 + 0.35 * value, message))
    result["schema_version"] = "1.0"
    result["session_id"] = session["session_id"]
    result["observations"] = observations
    result["acquisition"] = fitting_session
    provenance = result.setdefault("provenance", {})
    if not isinstance(provenance, dict):
        provenance = result["provenance"] = {"inference": provenance}
    provenance.update({"software_version": __version__, "physical_validation": False,
                       "evidence_classes": sorted({o["provenance"] for o in observations}),
                       "recordings": fingerprints, "method": method,
                       "coordinates": "right-handed, metres, z up",
                       "poses": "supplied acoustic-center positions",
                       "geometry": "inferred from recording-derived excess delays"})
    implementation = hashlib.sha256()
    for module in sorted(Path(__file__).parent.glob("*.py")):
        implementation.update(module.name.encode())
        implementation.update(module.read_bytes())
    provenance["implementation_sha256"] = implementation.hexdigest()
    provenance["runtime_versions"] = {"python": platform.python_version(),
        "numpy": importlib.metadata.version("numpy"), "scipy": importlib.metadata.version("scipy")}
    fingerprint = json.dumps({"session": fitting_session, "recordings": fingerprints,
                              "method": method, "software": __version__,
                              "implementation": provenance["implementation_sha256"],
                              "runtime": provenance["runtime_versions"]}, sort_keys=True, allow_nan=False)
    result["result_id"] = "result-" + hashlib.sha256(fingerprint.encode()).hexdigest()[:20]
    result["runtime_s"] = time.perf_counter() - start
    progress(1.0, result.get("status", "complete"))
    return result
