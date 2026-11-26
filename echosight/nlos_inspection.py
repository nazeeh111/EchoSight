"""Render the offline and hosted measured display from the same saved evidence."""

import base64
import hashlib
from html import escape
from pathlib import Path
import json
import re

_ASSETS = Path(__file__).with_name("inspection")
_THUMBNAIL = "data:image/png;base64,"


def render_inspection(*, axial, frames, depths, diagnostic, diagnostic_hash,
                      images, legend, results, source_hash, limits, hosted=False):
    """Wrap source-bound arrays and projections without regenerating their values."""
    frame_count, rows, columns = axial["shape"]
    if (rows, columns) != (55, 55) or frame_count != axial["frame_count"]:
        raise ValueError("The measured inspector expects the native 55 × 55 grid")
    if len(frames) != frame_count * rows * columns:
        raise ValueError("Axial bytes do not match the saved shape")
    if hashlib.sha256(frames).hexdigest() != axial["sha256"]:
        raise ValueError("Unexpected axial display hash")

    payload = {"spec": axial, "frames": base64.b64encode(frames).decode("ascii"),
               "depths": depths, "diagnostic": diagnostic}
    # Escape the HTML raw-text delimiter without changing decoded data.
    embedded = json.dumps(payload, allow_nan=False, separators=(",", ":")).replace("<", r"\u003c")
    first_bin = axial["first_volume_index_zero_based"] + 1
    last_bin = first_bin + frame_count - 1
    spacing = axial["depth_bin_spacing_m"]
    if not frames:
        raise ValueError("No native frames fall inside the saved depth window")
    # Start at the first strongest quantized sample in the saved window.
    initial_frame, initial_pixel = divmod(frames.index(max(frames)), rows * columns)
    initial_row, initial_column = divmod(initial_pixel, columns)
    lo, hi = results["depth_min_m"], results["depth_max_m"]
    depth_range = "No crossings" if lo is None else f"{lo:.6f}–{hi:.6f} m"
    notice = (
        "NOTICE.md" if hosted else
        "https://github.com/nazeeh111/EchoSight/blob/backend/implementation/echosight/LICENSE_SCOPE.txt"
    )
    fields = {
        "STYLE": (_ASSETS / "style.css").read_text(encoding="utf-8"),
        "SCRIPT": (_ASSETS / "viewer.js").read_text(encoding="utf-8"),
        "PAYLOAD": embedded, "FRAMECOUNT": frame_count,
        "MAXFRAME": max(0, frame_count - 1), "MIDFRAME": initial_frame,
        "FIRSTBIN": first_bin, "LASTBIN": last_bin,
        "INITIALBIN": first_bin + initial_frame,
        "INITIALX": initial_column, "INITIALY": initial_row,
        "START": f"{first_bin * spacing:.3f}", "END": f"{last_bin * spacing:.3f}",
        "SHAPE": " × ".join(map(str, diagnostic["volume_shape"])),
        "SPACING": f"{spacing * 1000:.3f}",
        "IMAGE0": _THUMBNAIL + base64.b64encode(images[0]).decode("ascii"),
        "IMAGE1": _THUMBNAIL + base64.b64encode(images[1]).decode("ascii"),
        "LEGEND": escape(legend, quote=True), "DEPTHRANGE": depth_range,
        "COUNT": results["finite_depth_pixels"], "HASH": escape(source_hash),
        "SLICEHASH": axial["sha256"], "DIAGNOSTICHASH": diagnostic_hash,
        "LIMITS": "".join(f"<li>{escape(item)}</li>" for item in limits),
        "NOTICEURL": notice,
    }
    template = (_ASSETS / "template.html").read_text(encoding="utf-8")
    return re.sub(r"\{\{([A-Z0-9]+)\}\}", lambda match: str(fields[match[1]]), template)
