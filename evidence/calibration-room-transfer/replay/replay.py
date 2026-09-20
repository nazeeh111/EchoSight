"""Re-evaluate saved output projections. No audio, calibration or inference executes."""
import argparse
import hashlib
import importlib.util
import json
import math
from pathlib import Path

HERE = Path(__file__).resolve().parent

def read(path):
    return json.loads(Path(path).read_text())

def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def compare(got, expected, path='$'):
    if isinstance(expected, dict):
        assert isinstance(got, dict) and got.keys() == expected.keys(), path
        for key in expected:
            compare(got[key], expected[key], f'{path}.{key}')
    elif isinstance(expected, list):
        assert isinstance(got, list) and len(got) == len(expected), path
        for i, (a, b) in enumerate(zip(got, expected)):
            compare(a, b, f'{path}[{i}]')
    elif isinstance(expected, float):
        assert not isinstance(got, bool) and math.isclose(got, expected, rel_tol=1e-10, abs_tol=1e-12), (path, got, expected)
    else:
        assert type(got) is type(expected) and got == expected, (path, got, expected)

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--repo', type=Path, required=True, help='Repository checkout with evaluation/metrics.py and declared NumPy/SciPy dependencies')
    parser.add_argument('--output', type=Path, required=True, help='New output path; existing files are never overwritten')
    args = parser.parse_args()
    if args.output.exists():
        raise FileExistsError(args.output)
    manifest = read(HERE / 'manifest.json')
    for name, digest in manifest['package_sha256'].items():
        assert sha(HERE / name) == digest, f'Package changed: {name}'
    for name, digest in manifest['repo_sha256'].items():
        assert sha(args.repo / name) == digest, f'Required evaluation source changed: {name}'
    spec = importlib.util.spec_from_file_location('frozen_gates', HERE / 'frozen_gates.py')
    gates = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(gates)
    gates.P = HERE
    gates.ROOT = args.repo.resolve()
    gates.read = read
    gates.cfg = lambda: read(HERE / 'settings.json')
    captured = []
    gates.save = lambda path, value: captured.append(value)
    gates.summarize()
    assert len(captured) == 1
    got = captured[0]
    # Expected result is read only after all gate arithmetic is complete.
    compare(got, read(HERE / 'expected-results.json'))
    labels = []
    for row in got['rows']:
        held = row['withheld']
        if held is not None:
            labels.append({'seed': row['seed'], 'method': row['method'], 'complete': held['complete'],
                          'unique_only_rms_s': held['rms_s'], 'unique_only_max_abs_s': held['max_abs_s'],
                          'complete_rms_s': held['rms_s'] if held['complete'] else None,
                          'complete_max_abs_s': held['max_abs_s'] if held['complete'] else None})
    output = {'comparison_passed': True, 'rows_compared': len(got['rows']),
              'tolerance': {'relative': 1e-10, 'absolute': 1e-12, 'gates_and_ids': 'exact'},
              'scope': 'Saved-output evaluation replay only; no raw audio processing, calibration fitting, geometry fitting or fresh timing measurements.',
              'manifest_sha256': sha(HERE / 'manifest.json'), 'results': got, 'withheld_error_labels': labels}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open('x') as stream:
        json.dump(output, stream, indent=2, allow_nan=False)
        stream.write('\n')
    print(json.dumps({'comparison_passed': True, 'rows_compared': len(got['rows']),
                      'transfer_pass': got['transfer_pass'], 'promotion_criteria_pass': got['promotion_criteria_pass'],
                      'output': str(args.output)}))

if __name__ == '__main__':
    main()
