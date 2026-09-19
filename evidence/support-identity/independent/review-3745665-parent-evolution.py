"""Explain changes in acoustic inference without claiming physical disappearance."""
from __future__ import annotations

import hashlib
import json
import numpy as np
from scipy.optimize import linear_sum_assignment


def _identifier(value, name):
    if not isinstance(value, str) or not 1 <= len(value) <= 160:
        raise ValueError(f"{name} must be a string of 1 to 160 characters")
    return value


def _validate_result(result):
    if not isinstance(result, dict):
        raise ValueError("result must be an object")
    if result.get("schema_version", "1.0") != "1.0":
        raise ValueError("unsupported result schema version")
    if result.get("result_id") is not None:
        _identifier(result["result_id"], "result_id")
    if result.get("status") is not None:
        _identifier(result["status"], "result status")
    if result.get("acquisition") is not None and not isinstance(result["acquisition"], dict):
        raise ValueError("acquisition must be an object")
    acquisition = result.get("acquisition") or {}
    if "source_position_m" in acquisition:
        position = acquisition["source_position_m"]
        if not isinstance(position, list) or len(position) != 3 or any(
            isinstance(x, bool) or not isinstance(x, (int, float)) or not np.isfinite(x) for x in position):
            raise ValueError("source_position_m must be three finite numbers")
    if "coordinate_frame_id" in acquisition:
        frame = acquisition["coordinate_frame_id"]
        if not isinstance(frame, str) or not 1 <= len(frame) <= 160:
            raise ValueError("coordinate_frame_id must be a string of 1 to 160 characters")
    for key, limit in (("surfaces", 128), ("observations", 32)):
        items = result.get(key, [])
        if not isinstance(items, list) or len(items) > limit or any(not isinstance(x, dict) for x in items):
            raise ValueError(f"{key} must be a bounded array of objects")
    surface_ids, track_ids = set(), set()
    for surface in result.get("surfaces", []):
        try:
            n = np.asarray(surface["normal"], dtype=float)
            d = float(surface["offset_m"])
        except (KeyError, ValueError, TypeError) as exc:
            raise ValueError("invalid plane geometry") from exc
        if n.shape != (3,) or not np.all(np.isfinite(n)) or not np.isfinite(d) or abs(np.linalg.norm(n) - 1) > 1e-5:
            raise ValueError("plane normal must be finite and unit length; offset must be finite")
        sid = _identifier(surface.get("surface_id"), "surface_id")
        track = _identifier(surface.get("track_id", sid), "track_id")
        if sid in surface_ids or track in track_ids:
            raise ValueError("surface IDs and effective track IDs must be unique within a result")
        surface_ids.add(sid); track_ids.add(track)
        support = surface.get("support", [])
        if not isinstance(support, list) or len(support) > 32 or any(not isinstance(e, dict) or not isinstance(e.get("capture_id"), str) for e in support):
            raise ValueError("invalid surface support")
    if any(not isinstance(o.get("capture_id"), str) for o in result.get("observations", [])):
        raise ValueError("observation capture_id must be a string")


def _previous_tracks(previous, comparison):
    surfaces = previous.get("surfaces", [])
    if comparison is None:
        return {s["surface_id"]: s.get("track_id", s["surface_id"]) for s in surfaces}
    if not isinstance(comparison, dict) or comparison.get("schema_version") != "1.0" or comparison.get("status") != "comparable":
        raise ValueError("previous_comparison must be a comparable v1 comparison")
    expected = _identifier(previous.get("result_id"), "previous result_id for track carry")
    if comparison.get("current_result_id") != expected:
        raise ValueError("previous_comparison does not belong to the previous result")
    entries = comparison.get("current_tracks")
    if not isinstance(entries, list) or len(entries) > 128:
        raise ValueError("previous_comparison current_tracks must be a bounded array")
    tracks, used = {}, set()
    for entry in entries:
        if not isinstance(entry, dict) or set(entry) != {"surface_id", "track_id"}:
            raise ValueError("current_tracks entries require exactly surface_id and track_id")
        sid = _identifier(entry["surface_id"], "carried surface_id")
        track = _identifier(entry["track_id"], "carried track_id")
        if sid in tracks or track in used:
            raise ValueError("carried surface IDs and track IDs must be unique")
        tracks[sid] = track; used.add(track)
    if set(tracks) != {s["surface_id"] for s in surfaces}:
        raise ValueError("previous_comparison current_tracks must cover exactly the previous surfaces")
    if any("track_id" in s and s["track_id"] != tracks[s["surface_id"]] for s in surfaces):
        raise ValueError("previous surface track_id conflicts with previous_comparison")
    return tracks


def _current_tracks(previous, current, assigned, reserved):
    """Births get fresh comparison-bound labels; ended tracks are not revived."""
    used = set(reserved) | set(assigned.values())
    tracks = []
    for surface in current.get("surfaces", []):
        sid = surface["surface_id"]
        track = assigned.get(sid)
        if track is None:
            identity = [previous.get("result_id"), current.get("result_id"), sid,
                        np.asarray(surface["normal"], float).tolist(), float(surface["offset_m"])]
            nonce = 0
            while True:
                encoded = json.dumps([identity, nonce], sort_keys=True, allow_nan=False).encode()
                track = "track-birth-" + hashlib.sha256(encoded).hexdigest()[:32]
                if track not in used: break
                nonce += 1
            used.add(track)
        tracks.append({"surface_id": sid, "track_id": track})
    return tracks


def compare_results(previous, current, *, previous_comparison=None, maximum_angle_deg=10., maximum_offset_m=.3):
    """Associate supported planes in one calibrated frame for frontend tracks.

    The association thresholds are display continuity gates, not significance
    tests. Establishing a causal scene change additionally requires controlled
    repeated acquisition; a changed fit alone cannot establish it.
    """
    _validate_result(previous)
    _validate_result(current)
    prior_tracks = _previous_tracks(previous, previous_comparison)
    if not 0 < maximum_angle_deg < 90 or not 0 < maximum_offset_m < 10:
        raise ValueError("invalid surface continuity gates")
    out = {"schema_version": "1.0", "previous_result_id": previous.get("result_id"),
           "current_result_id": current.get("result_id"), "status": "comparable",
           "correspondences": [], "newly_supported_surface_ids": [],
           "current_tracks": [],
           "unconfirmed_previous_surface_ids": [], "new_capture_ids": [],
           "physical_scene_change_established": False,
           "interpretation": "Changes describe inference and acoustic support; missing echoes do not establish absence.",
           "tracking_semantics": "Declared display continuity, not authenticated acquisition evidence or persistent physical object identity; missing surfaces end continuity.",
           "tracking_state_source": "previous_comparison" if previous_comparison is not None else "previous_surface_labels",
           "association_gates": {"angle_deg": maximum_angle_deg, "offset_m": maximum_offset_m}}
    a, b = previous.get("acquisition"), current.get("acquisition")
    required_calibration = ("coordinate_frame_id", "source_position_m", "sound_speed_m_s", "source_clock_scale", "probe")
    calibration_keys = required_calibration + ("effective_speed_m_s",)
    if not a or not b or any(a.get(k) is None for k in required_calibration) or not a.get("coordinate_frame_id") or any(a.get(k) != b.get(k) for k in calibration_keys):
        out.update(status="incomparable", diagnostics=[{"code": "calibration_changed_or_missing",
            "message": "Use the same surveyed coordinate frame, source and probe, or reprocess both sessions."}])
        out["current_tracks"] = _current_tracks(previous, current, {}, prior_tracks.values())
        return out
    before = previous.get("surfaces", [])
    after = current.get("surfaces", [])
    reference = np.asarray(a["source_position_m"], float)
    cost = np.full((len(before), len(after)), 1e6)
    differences = {}
    for i, left in enumerate(before):
        for j, right in enumerate(after):
            n1, n2 = np.asarray(left["normal"], float), np.asarray(right["normal"], float)
            dot = np.dot(n1, n2) / (np.linalg.norm(n1) * np.linalg.norm(n2))
            angle = float(np.degrees(np.arccos(np.clip(abs(dot), 0, 1))))
            sign = 1 if dot >= 0 else -1
            # Compare signed plane offsets at a physical reference, not at the
            # arbitrary coordinate origin when normals differ between fits.
            offset = float(sign * (right["offset_m"] - n2 @ reference)
                           - (left["offset_m"] - n1 @ reference))
            differences[i, j] = (angle, offset)
            if angle <= maximum_angle_deg and abs(offset) <= maximum_offset_m:
                cost[i, j] = angle / maximum_angle_deg + abs(offset) / maximum_offset_m
    matched_before, matched_after = set(), set()
    assigned = {}
    if before and after:
        rows, cols = linear_sum_assignment(cost)
        for i, j in zip(rows, cols):
            if cost[i, j] >= 1e6:
                continue
            left, right = before[i], after[j]
            old_support = {e["capture_id"] for e in left.get("support", [])}
            new_support = {e["capture_id"] for e in right.get("support", [])}
            angle, offset = differences[i, j]
            track = prior_tracks[left["surface_id"]]
            assigned[right["surface_id"]] = track
            out["correspondences"].append({"track_id": track,
                "previous_surface_id": left["surface_id"], "current_surface_id": right["surface_id"],
                "normal_change_deg": angle, "offset_change_m": offset,
                "offset_reference_point_m": reference.tolist(),
                "offset_semantics": "signed_plane_offset_change_at_shared_source_reference",
                "additional_support_count": len(new_support - old_support),
                "additional_support_capture_ids": sorted(new_support - old_support),
                "lost_support_capture_ids": sorted(old_support - new_support)})
            matched_before.add(i); matched_after.add(j)
    out["newly_supported_surface_ids"] = [p["surface_id"] for j,p in enumerate(after) if j not in matched_after]
    out["unconfirmed_previous_surface_ids"] = [p["surface_id"] for i,p in enumerate(before) if i not in matched_before]
    old_captures = {o["capture_id"] for o in previous.get("observations", [])}
    new_captures = {o["capture_id"] for o in current.get("observations", [])}
    out["new_capture_ids"] = sorted(new_captures - old_captures)
    out["ambiguity_reduced"] = previous.get("status") == "ambiguous" and current.get("status") in ("ok", "partial") and bool(after)
    out["status_transition"] = [previous.get("status"), current.get("status")]
    out["current_tracks"] = _current_tracks(previous, current, assigned, prior_tracks.values())
    return out
