"""Optional, read-only packaged UI assets. Store data is never an asset directory."""
from __future__ import annotations
import base64
import hashlib
import mimetypes
from pathlib import Path
import re
import sys
from urllib.parse import unquote

MAX_ASSET_BYTES = 32 * 1024 * 1024
ALLOWED_SUFFIXES = {'.html', '.css', '.js', '.mjs', '.json', '.png', '.svg', '.glb', '.wav', '.md', '.txt'}

def ui_directory():
    """Support source checkouts and wheel data installed under the active prefix."""
    for path in (Path(__file__).resolve().parent.parent / 'demo', Path(sys.prefix) / 'share' / 'echosight' / 'demo'):
        if (path / 'results.html').is_file() and (path / 'workspace.js').is_file():
            return path.resolve()
    raise ValueError('UI assets unavailable; use a source checkout or reinstall the complete EchoSight wheel')

def read_asset(directory, route):
    if not route.startswith('/ui/'):
        raise KeyError('UI asset not found')
    relative = unquote(route[4:], errors='strict') or 'index.html'
    parts = Path(relative).parts
    if ('\\' in relative or '\0' in relative or Path(relative).is_absolute()
            or any(part.startswith('.') or part == '__pycache__' for part in parts)):
        raise KeyError('UI asset not found')
    path = (directory / relative).resolve()
    if (not path.is_relative_to(directory) or not path.is_file() or path.suffix.lower() not in ALLOWED_SUFFIXES
            or any(part.startswith('.') or part == '__pycache__' for part in path.relative_to(directory).parts)):
        raise KeyError('UI asset not found')
    with path.open('rb') as stream:
        data = stream.read(MAX_ASSET_BYTES + 1)
    if len(data) > MAX_ASSET_BYTES:
        raise OverflowError('UI asset exceeds size limit')
    content_type = {'.js': 'text/javascript', '.mjs': 'text/javascript', '.glb': 'model/gltf-binary'}.get(path.suffix.lower())
    content_type = content_type or mimetypes.guess_type(str(path))[0] or 'application/octet-stream'
    hashes = []
    if path.suffix.lower() == '.html':
        for script in re.findall(rb'<script\b[^>]*type=["\']importmap["\'][^>]*>(.*?)</script>', data, re.DOTALL):
            hashes.append("'sha256-" + base64.b64encode(hashlib.sha256(script).digest()).decode('ascii') + "'")
    policy = ("default-src 'self'; script-src 'self' " + ' '.join(hashes) +
              "; style-src 'self'; img-src 'self' data: blob:; connect-src 'self'; "
              "object-src 'none'; base-uri 'none'; frame-ancestors 'none'; form-action 'self'")
    return data, content_type, {'Content-Security-Policy': policy}
