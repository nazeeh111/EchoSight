"""Check a wheel installation with its venv Python -I, outside source imports.

Uses only temporary synthetic inputs. No network, device or measured-data run.
"""
import contextlib
import io
import json
from pathlib import Path
import subprocess
import sys
import tempfile

import echosight
from echosight.cli import main
from echosight.webui import read_asset, ui_directory


def check():
    prefix = Path(sys.prefix).resolve()
    package = Path(echosight.__file__).resolve()
    if not package.is_relative_to(prefix):
        raise RuntimeError('Run with the installed venv Python -I, not source imports')
    assets = ui_directory()
    if not assets.is_relative_to(prefix):
        raise RuntimeError('UI assets must come from the installation')
    for name in ('results.html', 'workspace.js', 'comparison.js', 'workspace-data.js', 'result-view.js',
                 'assets/results/no-result.json', 'assets/room-corrected.glb',
                 'vendor/three.module.js', 'vendor/three.core.js',
                 'vendor/addons/controls/OrbitControls.js', 'vendor/THREE-LICENSE.txt', 'MODEL.md'):
        data, _, _ = read_asset(assets, '/ui/' + name)
        if not data:
            raise RuntimeError('Empty installed asset: ' + name)
    with tempfile.TemporaryDirectory(prefix='echosight-installed-') as temporary:
        root = Path(temporary)
        def run(*arguments, expected=0):
            output = io.StringIO()
            with contextlib.redirect_stdout(output), contextlib.redirect_stderr(output):
                code = main(list(map(str, arguments)))
            if code != expected:
                raise RuntimeError(f'CLI {arguments[0]} failed ({code}): {output.getvalue()}')
        run('probe', root / 'probe')
        before_probe = (root / 'probe/probe.wav').read_bytes()
        run('probe', root / 'probe', expected=2)
        assert (root / 'probe/probe.wav').read_bytes() == before_probe
        run('simulate', root / 'input', '--scenario', 'null', '--captures', '4')
        run('process', root / 'input/session.json', '--output', root / 'result.json', '--method', 'baseline')
        run('export', root / 'input/session.json', '--output', root / 'archive.zip')
        run('replay', root / 'archive.zip', '--store', root / 'store', '--output', root / 'replay.json')
        run('inspect', root / 'replay.json')
        run('compare', root / 'result.json', root / 'replay.json', '--output', root / 'comparison.json')
        original = (root / 'result.json').read_bytes()
        run('compare', root / 'result.json', root / 'replay.json', '--output', root / 'result.json', expected=2)
        assert (root / 'result.json').read_bytes() == original
        for name in ('result.json', 'replay.json'):
            result = json.loads((root / name).read_bytes())
            assert result['status'] == 'no_result' and result['surfaces'] == []
            assert len(result['observations']) == 4
        # Check the actual fixed worker entry under -I without a 6 GiB run.
        # This deliberately wrong-shape synthetic MAT must stop before migration.
        import numpy as np
        from scipy.io import savemat
        source = root / 'wrong-shape.mat'
        savemat(source, {'data_origin': np.zeros((1, 1, 8), dtype=np.float64)})
        with source.open('rb') as stream:
            worker = subprocess.run([sys.executable, '-I', str(package.with_name('_nlos_worker.py')),
                                     str(stream.fileno()), str(root), 'synthetic-negative-check'],
                                    pass_fds=(stream.fileno(),), stdin=subprocess.DEVNULL,
                                    capture_output=True, timeout=15)
        if worker.returncode == 0 or b'Pinned input did not contain the declared float64 cube' not in worker.stderr:
            raise RuntimeError('Isolated installed NLOS worker did not reach its input validation: ' + worker.stderr.decode(errors='replace'))
        assert not (root / 'volume.npy').exists()
    print(json.dumps({'status': 'passed', 'installed_package': str(package), 'installed_ui': str(assets),
                      'checks': ['packaged_assets', 'synthetic_cli_roundtrip', 'input_preservation',
                                 'isolated_worker_wrong_shape_rejection'],
                      'physical_or_full_measured_validation': False}, indent=2))


if __name__ == '__main__':
    check()
