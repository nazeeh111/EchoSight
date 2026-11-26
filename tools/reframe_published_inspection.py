"""Re-render the original public EchoSight explorer without reconstructing its volume."""

import argparse
import base64
import hashlib
import html
import json
from pathlib import Path
import re

from echosight.nlos_inspection import render_inspection

PUBLISHED_INDEX_SHA256 = "8d508f98d6270337c742bb6fb8af9ac39bf107a27193f717c5ffbef90b398476"


def reframe(directory):
    """Read the pinned legacy page and preserve its exact source-derived display assets."""
    page_bytes = (directory / "index.html").read_bytes()
    if hashlib.sha256(page_bytes).hexdigest() != PUBLISHED_INDEX_SHA256:
        raise ValueError("Expected the public index from gh-pages 6a99be15")
    original = page_bytes.decode("utf-8")
    diagnostic_bytes = (directory / "threshold-diagnostics.json").read_bytes()
    diagnostic_hash = hashlib.sha256(diagnostic_bytes).hexdigest()

    def match(regex):
        return re.search(regex, original, re.DOTALL)[1]

    diagnostic = json.loads(diagnostic_bytes)
    if diagnostic != json.loads(match(r"const diagnostic=(\{.*?\});\n")):
        raise ValueError("Diagnostic sidecar differs from the pinned page")
    depths = json.loads(match(r"depths=(\[\[.*?\]\]);\n"))
    finite = [value for row in depths for value in row if value is not None]
    images = [
        base64.b64decode(value, validate=True)
        for value in re.findall(r'src="data:image/png;base64,([A-Za-z0-9+/=]+)"', original)
    ]
    return render_inspection(
        axial=json.loads(match(r"const spec=(\{.*?\}), depths=")),
        frames=base64.b64decode(match(r'atob\("([A-Za-z0-9+/=]+)"\)'), validate=True),
        depths=depths, diagnostic=diagnostic, diagnostic_hash=diagnostic_hash,
        images=images, legend=match(r'class="legend" style="background:([^"]+)"'),
        source_hash=match(r"Input SHA-256</p><code>([a-f0-9]{64})</code>"),
        results={"finite_depth_pixels": len(finite), "depth_min_m": min(finite), "depth_max_m": max(finite)},
        limits=[html.unescape(value) for value in re.findall(r"<li>(.*?)</li>", match(r"Interpretation limits</h2><ul>(.*?)</ul>"))],
        hosted=True,
    )


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("published_snapshot", type=Path)
    parser.add_argument("output_html", type=Path)
    args = parser.parse_args()
    page = reframe(args.published_snapshot)
    with args.output_html.open("x", encoding="utf-8") as output:
        output.write(page)


if __name__ == "__main__":
    main()
