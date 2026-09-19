"""Waveform-level checks: constants below describe injected paths, not fitted labels."""
import json
from pathlib import Path
import tempfile
import unittest
import numpy as np
from scipy.io import wavfile
from echosight.signals import generate_probe, process_recording
from echosight.simulation import simulate_session


def waveform(alpha=1.0, warp=0.0):
    x, probe = generate_probe()
    fs = probe['sample_rate_hz']
    t = np.arange(len(x)) / fs
    u = np.arange(int((t[-1] * alpha + .3) * fs)) / fs
    source_t = (u - .073) / alpha
    source_t += warp * np.sin(2*np.pi*source_t / 1.1)
    y = .45 * np.interp(source_t, t, x, left=0, right=0)
    y += .21 * np.interp(source_t - .012345, t, x, left=0, right=0)
    y += .14 * np.interp(source_t - .026789, t, x, left=0, right=0)
    y += np.random.default_rng(23).normal(0, .0003, len(y))
    return y, fs, probe


class SignalTests(unittest.TestCase):
    def test_unlabeled_echoes_and_relative_clock_from_samples(self):
        y, fs, probe = waveform(alpha=1.0012)
        result = process_recording(y, fs, probe, 'r1')
        self.assertEqual(result['status'], 'ok', result)
        self.assertLess(abs(result['clock']['alpha'] - 1.0012), 25e-6)
        delays = [p['delay_s'] for p in result['candidates']]
        for expected in [.012345, .026789]:
            self.assertLess(min(abs(d-expected) for d in delays), .00008)
        self.assertEqual(len(delays), 2, delays)
        self.assertGreater(result['direct_std_s'], 0)

    def test_different_nominal_receiver_rate_and_negative_drift(self):
        y, fs, probe = waveform(alpha=.9991)
        rate=44100
        resampled=np.interp(np.arange(round(len(y)*rate/fs))/rate,np.arange(len(y))/fs,y)
        result=process_recording(resampled,rate,probe,'r2')
        self.assertEqual(result['status'],'ok',result)
        self.assertLess(abs(result['clock']['alpha']-.9991),25e-6)
        for expected in [.012345,.026789]:
            self.assertLess(min(abs(p['delay_s']-expected) for p in result['candidates']),.00008)

    def test_receiver_rate_must_support_probe_band(self):
        y,fs,probe=waveform()
        rate=16000
        resampled=np.interp(np.arange(round(len(y)*rate/fs))/rate,np.arange(len(y))/fs,y)
        result=process_recording(resampled,rate,probe,'r1')
        self.assertEqual(result['status'],'rejected')
        self.assertEqual(result['diagnostics'][0]['code'],'receiver_band_unsupported')

    def test_missing_repetition_rejects_interrupted_capture(self):
        y,fs,probe=waveform()
        # Remove the entire fourth probe and its echo response, simulating an interruption.
        first=round((probe['pilot_start_samples'][3]/fs+.073-.01)*fs)
        y[first:first+round(.15*fs)]=0
        result=process_recording(y,fs,probe,'r1')
        self.assertEqual(result['status'],'rejected',result)

    def test_earliest_direct_is_used_when_echo_is_louder(self):
        x,probe=generate_probe();fs=probe['sample_rate_hz'];t=np.arange(len(x))/fs
        u=np.arange(len(x)+round(.25*fs))/fs
        y=.15*np.interp(u-.06,t,x,left=0,right=0)+.5*np.interp(u-.08,t,x,left=0,right=0)
        result=process_recording(y,fs,probe,'r1')
        self.assertEqual(result['status'],'ok',result)
        self.assertLess(abs(result['candidates'][0]['delay_s']-.02),.00008)
        self.assertGreater(result['candidates'][0]['amplitude'],2)
        self.assertEqual(len(result['candidates']),1)
        self.assertLess(abs(result['direct_arrival_receiver_s']-.16),.00008)

    def test_nonaffine_warp_is_rejected(self):
        y, fs, probe = waveform(warp=.0015)
        result = process_recording(y, fs, probe, 'r1')
        self.assertEqual(result['status'], 'rejected')
        self.assertTrue(any(d['code'] == 'nonaffine_clock_or_motion' for d in result['diagnostics']), result)

    def test_empty_clipping_and_noise_rejected(self):
        _, probe = generate_probe()
        for y in [np.zeros(100), np.ones(100000), np.random.default_rng(4).normal(0,.02,90000)]:
            self.assertEqual(process_recording(y,48000,probe,'r1')['status'],'rejected')
        with self.assertRaises(ValueError):
            process_recording(np.array([np.nan]),48000,probe,'r1')

    def test_cancelled_processing(self):
        y, fs, probe = waveform()
        result = process_recording(y,fs,probe,'r1',cancel=lambda:True)
        self.assertEqual(result['status'],'rejected')
        self.assertEqual(result['diagnostics'][0]['code'],'cancelled')

    def test_simulated_lossless_recordings_have_separate_truth(self):
        with tempfile.TemporaryDirectory() as directory:
            manifest = simulate_session(directory, 'room', seed=3)
            session = json.loads(Path(manifest).read_text())
            truth = json.loads((Path(directory)/'truth.json').read_text())
            self.assertNotIn('surfaces', session)
            self.assertNotIn('truth', session)
            self.assertEqual(len(truth['surfaces']),6)
            capture = session['captures'][0]
            fs, pcm = wavfile.read(Path(directory)/capture['recording_path'])
            self.assertEqual(pcm.dtype,np.int16)
            result=process_recording(pcm.astype(float)/32768,fs,session['probe'],capture['capture_id'])
            self.assertEqual(result['status'],'ok',result)
            self.assertGreaterEqual(len(result['candidates']),4)

    def test_probe_rejects_unreasonable_allocation(self):
        for config in [{'sample_rate_hz':1_000_000_000},{'repetitions':100000},{'duration_s':100000}]:
            with self.assertRaises(ValueError):
                generate_probe(config)

if __name__ == '__main__':
    unittest.main()
