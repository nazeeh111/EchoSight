"""Raw regression for accepted wrong-lobe pilot trains; truth stays in tests."""
import unittest
import numpy as np
from scipy.signal import fftconvolve
from echosight.signals import generate_probe, process_recording


def clock_lobe_recording(room=False, alpha=1.0014913832594845):
    """Minimal analytic replay of an exposed development clock/offset condition."""
    emitted, probe = generate_probe(dict(high_hz=14000., repetitions=7, period_s=.35))
    rate = probe['sample_rate_hz']
    paths = [(0.003722953701022745, .55)]
    if room:
        # Geometric path lengths are encoded only as fixture arrival times.
        paths += [(0.008092890500787314, 0.1771106596282645),
                  (0.02555123282390936, 0.05609659560350149),
                  (0.0131593626838156, 0.10892147357991626),
                  (0.015249320821033806, 0.093993509069382),
                  (0.00916142646444512, 0.1564534934004483),
                  (0.009061245366753683, 0.15818324268679085)]
    impulse = np.zeros(round(.16 * rate))
    for delay, amplitude in paths:
        center = delay * rate
        indices = np.arange(int(np.floor(center)) - 24, int(np.floor(center)) + 25)
        weights = np.sinc(indices - center) * np.hanning(49)
        weights /= weights.sum()
        impulse[indices] += amplitude * weights
    wave = fftconvolve(fftconvolve(emitted, [.82, .13, -.045, .025]), impulse)
    wave = fftconvolve(wave, [.94, .045, -.018, .006])[:len(wave)]
    times = np.arange(len(wave) + round(.12 * rate)) / rate
    clean = np.interp((times - .034994865040894337) / alpha,
                      np.arange(len(wave)) / rate, wave, left=0, right=0)
    samples = .45 * (clean + np.random.default_rng(9441).normal(0, .00012, len(clean)))
    samples = np.rint(samples * 32767).astype('<i2').astype(float) / 32768
    return samples, rate, probe


class ClockRefinementTests(unittest.TestCase):
    def test_accepted_direct_only_lobe_bias_does_not_create_an_echo(self):
        samples, rate, probe = clock_lobe_recording()
        result = process_recording(samples, rate, probe, 'direct-only')
        self.assertEqual(result['status'], 'ok', result)
        self.assertLess(abs(result['clock']['alpha'] - 1.0014913832594845), 5e-6)
        self.assertTrue(result['clock']['acquisition_template_rate_refined'])
        self.assertEqual(result['candidates'], [])

    def test_same_clock_bias_with_room_paths(self):
        samples, rate, probe = clock_lobe_recording(room=True)
        result = process_recording(samples, rate, probe, 'room')
        self.assertEqual(result['status'], 'ok', result)
        self.assertLess(abs(result['clock']['alpha'] - 1.0014913832594845), 5e-6)
        # These independent arrivals are separated. The 100-us floor/ceiling
        # pair is deliberately not asserted as two recoverable candidates.
        for delay in [.004369936799764569, .009436408982792856, .01152636712001106]:
            self.assertLess(min(abs(c['delay_s'] - delay) for c in result['candidates']), 20e-6)

    def test_small_accepted_rate_does_not_take_extra_retry(self):
        samples, rate, probe = clock_lobe_recording(alpha=1.0005)
        result = process_recording(samples, rate, probe, 'small-rate')
        self.assertEqual(result['status'], 'ok', result)
        self.assertFalse(result['clock']['acquisition_template_rate_refined'])
        self.assertLess(abs(result['clock']['alpha'] - 1.0005), 5e-6)
        self.assertEqual(result['candidates'], [])

    def test_cancellation_and_recording_limit_still_apply(self):
        samples, rate, probe = clock_lobe_recording()
        before = process_recording(samples, rate, probe, 'cancel', cancel=lambda: True)
        self.assertEqual(before['diagnostics'][0]['code'], 'cancelled')
        calls = 0
        def cancel_during_correction():
            nonlocal calls
            calls += 1
            return calls >= 2
        during = process_recording(samples, rate, probe, 'cancel-later', cancel=cancel_during_correction)
        self.assertEqual(during['status'], 'rejected')
        self.assertEqual(during['diagnostics'][0]['code'], 'cancelled')
        with self.assertRaisesRegex(ValueError, '30 second'):
            process_recording(np.zeros(rate * 30 + 1), rate, probe, 'too-long')


if __name__ == '__main__':
    unittest.main()
