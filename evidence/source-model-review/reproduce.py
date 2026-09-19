"""Reproduce the independent review's small analytic/raw probes, never classifier fits."""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import types
import numpy as np
from scipy.signal import correlate, fftconvolve
from scipy.optimize import lsq_linear

COMMIT = 'de8442b2dd088c036d2b92eaeaf29a1273785795'
SIGNALS_SHA = '2fdc6c5d48f8e55efc1650eb52a9ffbc6880e4efa767dbd449900fc38859747f'
SNAPSHOT_SHA = 'b5de1137125e098c6e546463abb18495585fdbcc48b2c3ed5b7fe3b2c896e417'
HERE = Path(__file__).resolve().parent


def module_from_bytes(name, payload, filename):
    module = types.ModuleType(name)
    module.__file__ = str(filename)
    exec(compile(payload, str(filename), 'exec'), module.__dict__)
    return module


def load_sources(snapshot, core):
    manifest = json.loads((snapshot / 'MANIFEST.json').read_text())
    if manifest['content_sha256'] != SNAPSHOT_SHA:
        raise ValueError('Different frozen source-model snapshot')
    for name, expected in manifest['files'].items():
        relative = Path(name)
        if relative.is_absolute() or '..' in relative.parts:
            raise ValueError('Unsafe snapshot path')
        if hashlib.sha256((snapshot / relative).read_bytes()).hexdigest() != expected:
            raise ValueError(f'Changed snapshot file: {name}')
    if core is None:
        # Read the historical object without checking out or modifying any files.
        result = subprocess.run(['git', 'show', f'{COMMIT}:echosight/signals.py'],
                                cwd=HERE.parents[1], capture_output=True, check=True)
        raw = result.stdout
        source = f'git:{COMMIT}:echosight/signals.py'
    else:
        source = core / 'echosight/signals.py'
        raw = source.read_bytes()
    if hashlib.sha256(raw).hexdigest() != SIGNALS_SHA:
        raise ValueError('Processing source differs from immutable de8442b')
    signals = module_from_bytes('review_immutable_signals', raw, source)
    waveform = module_from_bytes('review_immutable_waveform',
                                 (snapshot / 'waveform_v3.py').read_bytes(),
                                 snapshot / 'waveform_v3.py')
    return manifest, signals, waveform


def raw_probe(manifest, signals, w):
    probe, config = signals.generate_probe(dict(high_hz=14000., repetitions=7, period_s=.22))
    fs = 48000
    h = np.zeros(1200)
    h[576], h[595] = .45, .18
    clean = fftconvolve(probe, h)

    def render(alpha):
        t = np.arange(len(clean) + 6000) / fs
        return np.interp((t - .05) / alpha, np.arange(len(clean)) / fs, clean, left=0, right=0)

    def normalize(observation, shift=0):
        response = observation['response']
        values = np.asarray(response['values'])
        axis = response['start_delay_s'] + np.arange(len(values)) / response['sample_rate_hz'] + shift
        scale = float(np.interp(0, axis, values))
        return np.interp(w.TIME, axis, values) / scale, scale, float(axis[np.argmax(abs(values))])

    observations = [signals.process_recording(y, fs, config, 'capture-00') for y in
                    [render(1.0002), np.r_[np.zeros(3), render(1.0002)], render(1.0006)]]
    if any(o['status'] != 'ok' for o in observations):
        raise AssertionError('Independent raw probe unexpectedly rejected')
    nominal, translated, clocked = observations
    a, scale0, peak0 = normalize(nominal)
    b, scale1, peak1 = normalize(translated)
    c, scale2, peak2 = normalize(nominal, 3 / fs)
    d, scale3, peak3 = normalize(clocked)
    raw = dict(statuses=[o['status'] for o in observations], direct_std_s=nominal['direct_std_s'],
               nominal_normalizer=scale0, translated_normalizer=scale1,
               axis_shift_normalizer=scale2, clock_changed_normalizer=scale3,
               normalized_translation_max_abs=float(np.max(abs(a-b))),
               axis_only_shift_normalized_max_abs=float(np.max(abs(a-c))),
               clock_change_normalized_max_abs=float(np.max(abs(a-d))),
               intercept_translation_s=translated['clock']['intercept_s']-nominal['clock']['intercept_s'],
               expected_translation_s=3/fs, nominal_alpha=nominal['clock']['alpha'],
               changed_alpha=clocked['clock']['alpha'], nominal_discrete_peak_tau_s=peak0,
               translated_discrete_peak_tau_s=peak1, axis_shift_discrete_peak_tau_s=peak2,
               clock_changed_discrete_peak_tau_s=peak3)
    kernel = np.exp(-(w.TIME/.00011)**2)
    delay = 1/fs
    shifted = np.interp(w.TIME-delay, w.TIME, kernel, left=0, right=0)
    y = 2.6*kernel-1.6*shifted
    y /= np.interp(0, w.TIME, y)
    amplitudes = compare_profile(w, kernel, y, delay, tolerance=1e-14)
    amplitude_result = dict(clipped_profile_mse=amplitudes['clipped_mse'],
                           bounded_profile_mse=amplitudes['bounded_mse'],
                           clipped_gains=amplitudes['clipped_gains'], bounded_gains=amplitudes['bounded_gains'],
                           clipped_shift_s=amplitudes['clipped_alignment_s'],
                           bounded_shift_s=amplitudes['bounded_alignment_s'],
                           mse_ratio=amplitudes['clipped_mse']/amplitudes['bounded_mse'])
    result = dict(snapshot_content_sha256=manifest['content_sha256'],
                  all_manifest_files_verified=len(manifest['files']), core_signals_sha256=SIGNALS_SHA,
                  raw_representation=raw, amplitude_profile=amplitude_result,
                  scope='Independent analytic/raw probes; no source classifier or held-out scene fits')
    return result, probe, config, a


def compare_profile(w, kernel, y, delay, tolerance=1e-13):
    record = dict(source=np.zeros(3), receiver=np.array([1.,0.,0.]), y=y)
    parameters = np.array([0.,0.,0.,delay/1e-4])
    residual, gains, alignment = w.residual_profiles(parameters, 'secondary', [record], kernel, np.zeros(3), 343.)
    actual = float(np.mean(residual**2))
    answers = []
    for shift in w.SHIFTS:
        A = np.column_stack([np.interp(w.TIME-shift, w.TIME, kernel, left=0, right=0),
                             np.interp(w.TIME-shift-delay, w.TIME, kernel, left=0, right=0)])
        fit = lsq_linear(A, y, bounds=([0,-2],[2,2]), tol=tolerance, lsmr_tol=tolerance)
        answers.append((float(np.mean((y-A@fit.x)**2)), fit.x.tolist(), float(shift)))
    exact = min(answers, key=lambda x:x[0])
    return dict(delay_s=delay, clipped_mse=actual, bounded_mse=exact[0], absolute_excess=actual-exact[0],
                clipped_gains=gains[0].tolist(), bounded_gains=exact[1],
                clipped_alignment_s=float(alignment[0]), bounded_alignment_s=exact[2])


def gain_probe(w, probe, config, y):
    pulse = probe[config['pilot_start_samples'][0]:config['pilot_start_samples'][0]+1920]
    k = correlate(pulse, pulse, mode='full')
    kt = (np.arange(len(k))-len(pulse)+1)/48000
    kernel = np.interp(w.TIME, kt, k/k.max())
    rows = [compare_profile(w, kernel, y, ticks/48000) for ticks in range(-24,25)]
    return dict(count=len(rows), suboptimal_count=sum(r['absolute_excess']>1e-12 for r in rows),
                worst=max(rows,key=lambda r:r['absolute_excess']), rows=rows)


def gain_algebra():
    A = np.array([[1.,.8],[0.,.6]])
    y = A@np.array([3.,-1.])
    gains = np.clip(np.linalg.lstsq(A,y,rcond=None)[0],[0,-2],[2,2])
    fit = lsq_linear(A,y,bounds=([0,-2],[2,2]),tol=1e-13)
    return dict(unconstrained_gains=[3.,-1.], clipped_gains=gains.tolist(),
                correct_bounded_gains=fit.x.tolist(), clipped_sse=float(np.sum((y-A@gains)**2)),
                bounded_sse=float(np.sum((y-A@fit.x)**2)),
                scope='Algebraic counterexample to componentwiseclipping as boundedleast-squares; not a physicalclassifierfalsepositive')


def same_numeric(actual, expected):
    if isinstance(expected,dict):
        return actual.keys()==expected.keys() and all(same_numeric(actual[k],v) for k,v in expected.items())
    if isinstance(expected,list):
        return len(actual)==len(expected) and all(same_numeric(a,b) for a,b in zip(actual,expected))
    if isinstance(expected,(int,float)) and not isinstance(expected,bool):
        return bool(np.isclose(actual,expected,rtol=1e-9,atol=1e-10))
    return actual==expected


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--snapshot',type=Path,default=HERE.parent/'source-model-diagnostic-trial')
    parser.add_argument('--core',type=Path,help='Optional immutable de8442b checkout/archive; otherwise read its Git object')
    parser.add_argument('--output',type=Path,default=HERE.parents[1]/'work/source-model-review-reproduction')
    args = parser.parse_args()
    manifest, signals, waveform = load_sources(args.snapshot.resolve(), args.core.resolve() if args.core else None)
    raw, probe, config, normalized = raw_probe(manifest,signals,waveform)
    results = {'results.json':raw,'gain-results.json':gain_probe(waveform,probe,config,normalized),
               'gain-algebra.json':gain_algebra()}
    args.output.mkdir(parents=True,exist_ok=True)
    matches = {}
    for name, result in results.items():
        expected = json.loads((HERE/name).read_text())
        matches[name] = same_numeric(result,expected)
        (args.output/name).write_text(json.dumps(result,indent=2,allow_nan=False)+'\n')
    verification = dict(passed=all(matches.values()),reference_matches=matches,
                        numerical_tolerance=dict(relative=1e-9,absolute=1e-10),
                        core_commit=COMMIT,core_signals_sha256=SIGNALS_SHA,
                        snapshot_content_sha256=SNAPSHOT_SHA,manifest_files_verified=len(manifest['files']),
                        helper_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                        classifier_fits=0,heldout_cases_generated=0)
    (args.output/'verification.json').write_text(json.dumps(verification,indent=2)+'\n')
    print(json.dumps(verification,indent=2))
    raise SystemExit(0 if verification['passed'] else 1)


if __name__=='__main__':
    main()
