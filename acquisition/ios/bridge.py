"""Inject a supplied synthetic recording through Swift export and backend import.

No AVAudioEngine, microphone, simulator, signing or installation is involved.
Run with the repository Python environment after its normal editable setup.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import zipfile

import numpy as np

from echosight.acquisition import read_capture_package
from echosight.signals import process_recording
from echosight.simulation import simulate_session
from echosight.storage import load_session, read_recording


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--session', type=Path, help='Synthetic session JSON; otherwise generate seed 1 room fixture')
    args = parser.parse_args()
    native = Path(__file__).resolve().parent
    output = native / 'build' / 'bridge'
    output.mkdir(parents=True, exist_ok=True)
    session_path = args.session or simulate_session(output / 'synthetic-input', seed=1)
    session = load_session(session_path)
    capture = session['captures'][0]
    if capture.get('provenance') != 'simulated':
        raise ValueError('This injected software bridge requires an explicitly simulated capture')
    original, rate = read_recording(capture['recording_path'])
    if rate != 48000 or len(original) > 48000 * 20:
        raise ValueError('The deterministic Swift waveform fixture requires 48 kHz and at most 20 seconds')
    delivered = np.asarray(original, dtype='<f4')
    if not np.array_equal(delivered.astype(float), original):
        raise ValueError('Supplied samples cannot be represented exactly as Float32; do not silently quantize')
    raw = output / 'supplied.f32le'
    raw.write_bytes(delivered.tobytes())
    result = subprocess.run([str(native / 'test-core.sh'), str(raw)], capture_output=True, text=True)
    (output / 'native-tests.log').write_text(result.stdout + result.stderr)
    result.check_returncode()
    package = native / 'build' / 'fixtures' / 'waveform.echosight.zip'
    data = package.read_bytes()
    imported, imported_rate, evidence = read_capture_package(data, 64 * 1024 * 1024)
    assert imported_rate == rate and np.array_equal(imported, original)
    assert evidence['acquisition']['processing_eligible'] is True
    with zipfile.ZipFile(package) as archive:
        assert set(archive.namelist()) == {'recording.wav', 'manifest.json'}
        assert archive.testzip() is None
        manifest = json.loads(archive.read('manifest.json'))
        assert hashlib.sha256(archive.read('recording.wav')).hexdigest() == manifest['recording_sha256']
    before = process_recording(original, rate, session['probe'], capture['capture_id'])
    after = process_recording(imported, imported_rate, session['probe'], capture['capture_id'])
    assert before == after, 'Export/import changed deterministic acoustic observations'
    assert before['status'] != 'rejected' and before['candidates'], 'Bridge must exercise actual echo extraction'
    controls = {}
    for name, eligible in [('exact', True), ('gap', False), ('overlap', False), ('host-regression', False), ('host-inconsistent', False)]:
        _, _, control = read_capture_package((native / 'build' / 'fixtures' / f'{name}.echosight.zip').read_bytes(), 64 * 1024 * 1024)
        actual = control['acquisition']['processing_eligible']
        assert actual is eligible
        controls[name] = actual
    report = dict(schema_version='1.0', verification='injected_software_buffers', physical_validation=False,
                  supplied_session=str(Path(session_path).resolve()), native_package=str(package),
                  frame_count=len(original), sample_rate_hz=rate, sample_values_identical=True,
                  observation_objects_identical=True, extracted_candidate_count=len(after['candidates']),
                  processing_eligible=True, control_processing_eligibility=controls,
                  package_sha256=hashlib.sha256(data).hexdigest())
    (output / 'report.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()
