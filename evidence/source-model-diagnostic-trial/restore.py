"""Restore the preserved experimental tree without overwriting different bytes.

Use in a clean full Git checkout. Raw fixtures are generated only by the separate
run scripts. This helper does not perform fitting or change acceptance criteria.
"""
import argparse
import hashlib
import json
from pathlib import Path

archive = Path(__file__).resolve().parent
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--repository', type=Path, default=archive.parents[1])
args = parser.parse_args()
root = args.repository.resolve()
if not (root / '.git').exists():
    raise ValueError('Destination must be a full Git checkout containing the historical commits')
manifest = json.loads((archive / 'MANIFEST.json').read_text())
target = root / 'work' / 'source-model-diagnostic'
# Check every source and existing destination before writing any files.
items = []
for name, expected in manifest['files'].items():
    relative = Path(name)
    if relative.is_absolute() or '..' in relative.parts:
        raise ValueError('Unsafe archive path')
    raw = (archive / relative).read_bytes()
    if hashlib.sha256(raw).hexdigest() != expected:
        raise ValueError(f'Archive hash mismatch: {name}')
    destination = target / relative
    if destination.exists() and destination.read_bytes() != raw:
        raise FileExistsError(f'Preserve existing experiment and use a clean checkout: {destination}')
    items.append((destination, raw))
for destination, raw in items:
    if not destination.exists():
        destination.parent.mkdir(parents=True, exist_ok=True)
        with destination.open('xb') as output:
            output.write(raw)
print(json.dumps({'restored_files': len(items), 'target': str(target),
                  'frozen_content_sha256': manifest['content_sha256'],
                  'raw_generated': False, 'fitting_executed': False}))
