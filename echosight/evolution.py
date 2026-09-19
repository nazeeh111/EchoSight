"""Explain changes in acoustic inference without claiming physical disappearance."""
from __future__ import annotations

import numpy as np
from scipy.optimize import linear_sum_assignment


def _validate_result(result):
    if not isinstance(result, dict):
        raise ValueError("result must be an object")
    if result.get("schema_version", "1.0") != "1.0":
        raise ValueError("unsupported result schema version")
    if result.get("acquisition") is not None and not isinstance(result["acquisition"], dict):
        raise ValueError("acquisition must be an object")
    for key, limit in (("surfaces", 128), ("observations", 32)):
        items = result.get(key, [])
        if not isinstance(items, list) or len(items) > limit or any(not isinstance(x, dict) for x in items):
            raise ValueError(f"{key} must be a bounded array of objects")
    for surface in result.get("surfaces", []):
        try:
            n = np.asarray(surface["normal"], dtype=float)
            d = float(surface["offset_m"])
        except (KeyError, ValueError, TypeError) as exc:
            raise ValueError("invalid plane geometry") from exc
        if n.shape != (3,) or not np.all(np.isfinite(n)) or not np.isfinite(d) or abs(np.linalg.norm(n) - 1) > 1e-5:
            raise ValueError("plane normal must be finite and unit length; offset must be finite")
        if not isinstance(surface.get("surface_id"), str):
            raise ValueError("surface_id must be a string")
        support = surface.get("support", [])
        if not isinstance(support, list) or len(support) > 32 or any(not isinstance(e, dict) or not isinstance(e.get("capture_id"), str) for e in support):
            raise ValueError("invalid surface support")
    if any(not isinstance(o.get("capture_id"), str) for o in result.get("observations", [])):
        raise ValueError("observation capture_id must be a string")


def compare_results(previous, current, *, maximum_angle_deg=10., maximum_offset_m=.3):
    """Associate supported planes in one calibrated frame for frontend tracks.

    The association thresholds are display continuity gates, not significance
    tests. Establishing a causal scene change additionally requires controlled
    repeated acquisition; a changed fit alone cannot establish it.
    """
    _validate_result(previous)
    _validate_result(current)
    if not 0 < maximum_angle_deg < 90 or not 0 < maximum_offset_m < 10:
        raise ValueError("invalid surface continuity gates")
    out = {"schema_version": "1.0", "previous_result_id": previous.get("result_id"),
           "current_result_id": current.get("result_id"), "status": "comparable",
           "correspondences": [], "newly_supported_surface_ids": [],
           "unconfirmed_previous_surface_ids": [], "new_capture_ids": [],
           "physical_scene_change_established": False,
           "interpretation": "Changes describe inference and acoustic support; missing echoes do not establish absence.",
           "association_gates": {"angle_deg": maximum_angle_deg, "offset_m": maximum_offset_m}}
    a, b = previous.get("acquisition"), current.get("acquisition")
    calibration_keys = ("coordinate_frame_id", "source_position_m", "sound_speed_m_s", "source_clock_scale", "probe")
    if not a or not b or not a.get("coordinate_frame_id") or any(a.get(k) != b.get(k) for k in calibration_keys):
        out.update(status="incomparable", diagnostics=[{"code": "calibration_changed_or_missing",
            "message": "Use the same surveyed coordinate frame, source and probe, or reprocess both sessions."}])
        return out
    before = previous.get("surfaces", [])
    after = current.get("surfaces", [])
    cost = np.full((len(before), len(after)), 1e6)
    differences = {}
    for i, left in enumerate(before):
        for j, right in enumerate(after):
            n1, n2 = np.asarray(left["normal"], float), np.asarray(right["normal"], float)
            dot = np.dot(n1, n2) / (np.linalg.norm(n1) * np.linalg.norm(n2))
            angle = float(np.degrees(np.arccos(np.clip(abs(dot), 0, 1))))
            offset = float(right["offset_m"] * (1 if dot >= 0 else -1) - left["offset_m"])
            differences[i, j] = (angle, offset)
            if angle <= maximum_angle_deg and abs(offset) <= maximum_offset_m:
                cost[i, j] = angle / maximum_angle_deg + abs(offset) / maximum_offset_m
    matched_before, matched_after = set(), set()
    if before and after:
        rows, cols = linear_sum_assignment(cost)
        for i, j in zip(rows, cols):
            if cost[i, j] >= 1e6:
                continue
            left, right = before[i], after[j]
            old_support = {e["capture_id"] for e in left.get("support", [])}
            new_support = {e["capture_id"] for e in right.get("support", [])}
            angle, offset = differences[i, j]
            out["correspondences"].append({"track_id": left.get("track_id", left["surface_id"]),
                "previous_surface_id": left["surface_id"], "current_surface_id": right["surface_id"],
                "normal_change_deg": angle, "offset_change_m": offset,
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
    return out
