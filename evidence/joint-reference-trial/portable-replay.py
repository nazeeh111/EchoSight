"""Derived-observation mathematical replay; does not verify or process raw audio."""
from pathlib import Path
import argparse
import hashlib
import importlib.util
import json
import numpy as np

P = Path(__file__).resolve().parent


def read(name):
    return json.loads((P/name).read_text())


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    manifest = read('portable-manifest.json')
    for name, digest in manifest['required_sha256'].items():
        assert hashlib.sha256((P/name).read_bytes()).hexdigest() == digest, name
    spec = importlib.util.spec_from_file_location('frozen_joint_trial', P/'run.py')
    runner = importlib.util.module_from_spec(spec); spec.loader.exec_module(runner)
    inputs = read('portable-inputs.json')
    frozen = read('freeze.json')
    for path, digest in inputs['original_input_sha256'].items():
        assert frozen['input_hashes'][path] == digest, path
    admissions = read('admission.json')
    fits = []
    for pair in inputs['pairs']:
        admission = next(a for a in admissions if a['pattern'] == pair['pattern'] and a['seed'] == pair['seed'])
        assert admission['admitted'] and pair['pattern'] == 'single'
        pair['admission'] = admission['records']; pair['admitted'] = True
        for i, (capture, observation, candidate) in enumerate(pair['rows']):
            assert candidate['candidate_id'] == pair['admission'][i]['candidate_id']
            ref = ('x', 'y')[i//12]
            path = f"work/source-calibration-mismatch/run-v2/raw/single-{pair['seed']}-{ref}/{capture['capture_id']}.wav"
            assert observation['recording_sha256'] == frozen['input_hashes'][path]
        fits.append(runner.fit_pair(pair))
    # Truth and expected fitted values are never passed to the estimator.
    expected = read('results.json')['fits']
    metrics = []
    numeric = ('source_position_m', 'effective_speed_m_s', 'parameter_covariance',
        'parameter_std', 'pair_correlation_worst_parameter_std', 'held_residual_std_s',
        'pair_correlation_min_held_std_s', 'pair_correlation_max_held_std_s',
        'information_singular_values', 'training_noise_inflation')
    for actual, saved in zip(fits, expected, strict=True):
        assert actual['seed'] == saved['seed']
        assert actual['passed'] == saved['passed'] and actual['bound_gates'] == saved['bound_gates']
        for key in numeric:
            np.testing.assert_allclose(actual[key], saved[key], rtol=1e-7, atol=1e-10, err_msg=key)
        for key in saved['matrices']:
            np.testing.assert_allclose(actual['matrices'][key], saved['matrices'][key], rtol=1e-7, atol=1e-12)
        for a, b in zip(actual['references'], saved['references'], strict=True):
            assert a['gates'] == b['gates'] and a['passed'] == b['passed']
            for field in ('metrics', 'pair_correlation_sensitivity'):
                for key in b[field]:
                    np.testing.assert_allclose(a[field][key], b[field][key], rtol=1e-7, atol=1e-10)
        for a, b in zip(actual['records'], saved['records'], strict=True):
            assert a['candidate_id'] == b['candidate_id'] and a['partition'] == b['partition']
            np.testing.assert_allclose(a['residual_s'], b['residual_s'], rtol=1e-7, atol=1e-10)
        metrics.append(dict(seed=actual['seed'], passed=actual['passed'],
            source_max_abs_difference_m=float(np.max(abs(np.array(actual['source_position_m'])-saved['source_position_m']))),
            speed_abs_difference_m_s=abs(actual['effective_speed_m_s']-saved['effective_speed_m_s'])))
    output = dict(scope=__doc__, comparisons_passed=True, raw_verified=False, rows=metrics)
    if args.output:
        args.output.write_text(json.dumps(output, indent=2)+'\n')
    print(json.dumps(output, indent=2))


if __name__ == '__main__':
    main()
