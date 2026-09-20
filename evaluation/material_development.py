"""Controlled raw-recording material demonstration, not physical material data.

Known labels describe supplied synthetic reference filters. Query scene truth is
written separately and is never an input to geometry or interpretation.
"""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path

import numpy as np
from scipy.io import wavfile
from scipy.signal import fftconvolve

from evaluation.path_interpretations import impulse, mirror, probe

SETTINGS = {
    'schema_version': '1.0', 'source_m': [1.5, 1.5, 1.3],
    'room_size_m': [5.5, 4.8, 3.2], 'effective_speed_m_s': 343.,
    'probe': {'sample_rate_hz': 48000, 'duration_s': .04, 'low_hz': 2000.,
              'high_hz': 14000., 'repetitions': 7, 'period_s': .35,
              'lead_s': .1, 'tail_s': .18, 'max_echo_delay_s': .08},
    'positions_m': [[.7,.75,.4],[4.6,.85,.55],[.85,3.9,.65],[4.75,3.75,.35],
                    [.9,.9,2.65],[4.65,.65,2.5],[.65,3.85,2.45],[4.5,3.95,2.7],
                    [2.55,.7,1.2],[3.,4.1,1.8],[.75,2.5,1.55],[4.6,2.2,1.1]],
    'filters': {'flat_reflector': [.65], 'lowpass_reflector': [.28,.24,.17,.08,.03]},
    'seeds': {'reference_flat': 73101, 'reference_lowpass': 73102, 'room': 73103, 'null': 73104},
    'source_fir': [.82,.13,-.045,.025], 'receiver_fir': [.94,.045,-.018,.006],
    'noise_std': .00012, 'direct_amplitude': .55, 'recording_scale': .45,
    'clock_ppm_bounds': [-150.,150.], 'offset_s_bounds': [.04,.08],
    'profile_regularization_std_db': 1., 'minimum_views': 3, 'maximum_squared_distance': 16.,
    'route_id': 'synthetic-material-reference-chain-v1',
}


def _save(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, allow_nan=False) + '\n')


def _sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def render_case(folder, case):
    """Render one immutable session using independently specified amplitude paths."""
    folder = Path(folder)
    folder.mkdir(parents=True, exist_ok=False)
    cfg = SETTINGS
    source = np.array(cfg['source_m'])
    receivers = np.array(cfg['positions_m'])
    rng = np.random.default_rng(cfg['seeds'][case])
    fs = cfg['probe']['sample_rate_hz']
    emitted, specification = probe(cfg['probe'])
    emitted = fftconvolve(emitted, cfg['source_fir'])
    if case.startswith('reference_'):
        material = 'flat_reflector' if case == 'reference_flat' else 'lowpass_reflector'
        planes = [{'surface_id': 'reference', 'normal': [1.,0.,0.], 'offset_m': 0., 'material_id': material}]
    elif case == 'room':
        planes = [{'surface_id': f'wall-{axis}-{side}', 'normal': np.eye(3)[axis].tolist(),
                   'offset_m': float(side * cfg['room_size_m'][axis]),
                   'material_id': 'flat_reflector' if (axis + side) % 2 == 0 else 'lowpass_reflector'}
                  for axis in range(3) for side in (0,1)]
    elif case == 'null':
        planes = []
    else:
        raise ValueError('Unknown controlled development case')
    session = {'schema_version': '1.0', 'session_id': 'material-' + case,
               'coordinate_frame_id': 'controlled-material-frame', 'source_position_m': source.tolist(),
               'source_position_std_m': .003, 'sound_speed_m_s': cfg['effective_speed_m_s'],
               'sound_speed_std_m_s': .3, 'source_clock_scale': 1., 'source_clock_std_ppm': 40.,
               'probe': specification, 'captures': []}
    truth = {'case': case, 'seed': cfg['seeds'][case], 'surfaces': planes, 'captures': [],
             'physical_validation': False, 'material_semantics': 'supplied synthetic reference filters, not measured building materials'}
    for i, receiver in enumerate(receivers):
        direct = float(np.linalg.norm(receiver - source))
        paths = [{'delay_s': direct / cfg['effective_speed_m_s'], 'amplitude': cfg['direct_amplitude'],
                  'fir_offsets_samples': [0], 'fir_coefficients': [1.]}]
        for plane in planes:
            reflected = mirror(source, receiver, np.array(plane['normal']), plane['offset_m'])
            if reflected is None:
                raise ValueError('Invalid controlled reflection geometry')
            length, _ = reflected
            taps = cfg['filters'][plane['material_id']]
            paths.append({'delay_s': length / cfg['effective_speed_m_s'],
                          'amplitude': cfg['direct_amplitude'] * direct / length,
                          'fir_offsets_samples': list(range(len(taps))), 'fir_coefficients': taps})
        wave = fftconvolve(emitted, impulse(paths, fs))
        wave = fftconvolve(wave, cfg['receiver_fir'])[:len(wave)]
        alpha = 1 + rng.uniform(*cfg['clock_ppm_bounds']) * 1e-6
        offset = rng.uniform(*cfg['offset_s_bounds'])
        times = np.arange(len(wave) + round(.12 * fs)) / fs
        clean = np.interp((times-offset)/alpha, np.arange(len(wave))/fs, wave, left=0, right=0)
        samples = cfg['recording_scale'] * (clean + rng.normal(0, cfg['noise_std'], len(clean)))
        if np.max(abs(samples)) >= .95:
            raise ValueError('Overload; do not normalize or replace the seed')
        name = f'capture-{i:02d}.wav'
        wavfile.write(folder/name, fs, np.rint(samples*32767).astype('<i2'))
        session['captures'].append({'capture_id': f'capture-{i:02d}', 'receiver_position_m': receiver.tolist(),
            'receiver_position_std_m': .003, 'recording_path': name, 'sha256': _sha(folder/name),
            'sample_rate_hz': fs, 'provenance': 'simulated'})
        truth['captures'].append({'capture_id': f'capture-{i:02d}', 'alpha': float(alpha),
                                 'offset_s': float(offset), 'paths': paths})
    _save(folder/'session.json', session)
    _save(folder/'truth.json', truth)
    _save(folder/'manifest.json', {'files': {p.name: _sha(p) for p in sorted(folder.iterdir())},
                                  'source_sha256': _sha(__file__), 'settings': cfg})
    return folder/'session.json'


def render(output):
    output = Path(output)
    output.mkdir(parents=True, exist_ok=False)
    _save(output/'settings.json', SETTINGS)
    for case in SETTINGS['seeds']:
        render_case(output/case, case)
    return output


def run_demo(output):
    """Generate independent references/query, then run the actual public pipeline."""
    from echosight.interpretation import build_material_profile
    from echosight.pipeline import process_session, save_result
    from echosight.storage import load_session
    from evaluation.metrics import score_surfaces
    root = render(output)
    profiles = []
    for case, material, color in [('reference_flat', 'flat_reflector', '#E6E6E6'),
                                  ('reference_lowpass', 'lowpass_reflector', '#426B8A')]:
        result = process_session(root/case/'session.json')
        save_result(result, root/(case+'-result.json'))
        if len(result['surfaces']) != 1:
            raise ValueError('The reference has no unique inferred plane; preserve this failed run')
        profile = build_material_profile(result, result['surfaces'][0]['surface_id'],
            material_id=material, label='Synthetic '+material, route_id=SETTINGS['route_id'],
            regularization_std_db=SETTINGS['profile_regularization_std_db'],
            provenance={'kind': 'simulated', 'note': 'Controlled inverse-distance reference filter; not measured building material.'},
            appearance={'provenance': {'kind': 'supplied', 'note': 'Demonstration palette prior, not optical measurement.'},
                        'colors': [{'color_srgb': color, 'probability': .8}]})
        _save(root/(material+'-profile.json'), profile)
        profiles.append(profile)
    context = {'schema_version': '1.0', 'route_id': SETTINGS['route_id'], 'profiles': profiles,
               'maximum_squared_distance': SETTINGS['maximum_squared_distance'], 'minimum_views': SETTINGS['minimum_views']}
    _save(root/'context.json', context)
    results = {}
    for case, target in [('room', 'room-result'), ('null', 'null-result'),
                          ('reference_flat', 'reused-reference-result')]:
        session = load_session(root/case/'session.json')
        session['interpretation_context'] = context
        # Keep relative raw paths in the portable session; original manifests stay intact.
        portable = json.loads((root/case/'session.json').read_text())
        portable['interpretation_context'] = context
        _save(root/case/'with-context.json', portable)
        results[target] = process_session(session)
        save_result(results[target], root/(target+'.json'))
    wrong_context = json.loads(json.dumps(context))
    for profile in wrong_context['profiles']:
        profile['mean_db'] = [x+60 for x in profile['mean_db']]
        profile['provenance'] = {'kind': 'supplied', 'note': 'Deliberately incompatible profile mean, negative control.'}
    _save(root/'out-of-domain-context.json', wrong_context)
    session = load_session(root/'room/session.json')
    session['interpretation_context'] = wrong_context
    results['out-of-domain-result'] = process_session(session)
    save_result(results['out-of-domain-result'], root/'out-of-domain-result.json')

    # All queries are saved before evaluation reads generating geometry/material labels.
    truth = json.loads((root/'room/truth.json').read_text())
    room = results['room-result']
    geometry = score_surfaces(room, truth, maximum_normal_error_deg=5., maximum_offset_error_m=.10)
    expected = {m['predicted_id']: next(t['material_id'] for t in truth['surfaces'] if t['surface_id']==m['truth_id'])
                for m in geometry['matches']}
    materials = []
    for row in room['interpretation']['surface_interpretations']:
        probabilities = row['material']['probabilities']
        estimate = max(probabilities, key=lambda p: p['probability'])['material_id'] if probabilities else None
        materials.append({'surface_id': row['surface_id'], 'expected_material_id': expected.get(row['surface_id']),
                          'estimated_material_id': estimate, 'correct': estimate==expected.get(row['surface_id']) if estimate else None,
                          'material': row['material'], 'appearance': row['appearance']})
    estimated = [r for r in materials if r['estimated_material_id'] is not None]
    reference_geometry = json.loads((root/'reference_flat-result.json').read_text())['surfaces']
    reused = results['reused-reference-result']
    reused_unknown = (reused['surfaces'] == reference_geometry and len(reference_geometry) == 1
        and len(reused['interpretation']['surface_interpretations']) == 1 and all(
        r['material']['status']=='unknown' and not r['material']['probabilities']
        for r in reused['interpretation']['surface_interpretations']))
    outlier_unknown = all(r['material']['status']=='unknown' and not r['material']['probabilities']
        for r in results['out-of-domain-result']['interpretation']['surface_interpretations'])
    preserved = all(_sha(root/case/name)==digest
        for case in SETTINGS['seeds']
        for name,digest in json.loads((root/case/'manifest.json').read_text())['files'].items())
    checks = {'six_room_planes': geometry['matched_count']==6 and geometry['false_surfaces']==0 and geometry['horizontal_matched']==2,
              'both_reference_classes_demonstrated': {r['estimated_material_id'] for r in estimated}==set(SETTINGS['filters']),
              'no_wrong_material_estimates_in_controlled_case': all(r['correct'] for r in estimated),
              'null_has_no_geometry_or_materials': not results['null-result']['surfaces'] and not results['null-result']['interpretation']['surface_interpretations'],
              'reused_reference_is_unknown': reused_unknown, 'out_of_domain_is_unknown': outlier_unknown,
              'context_does_not_change_geometry': room['surfaces']==results['out-of-domain-result']['surfaces'],
              'original_inputs_preserved': preserved}
    summary = {'schema_version': '1.0', 'status': 'passed' if all(checks.values()) else 'failed', 'checks': checks,
               'geometry': geometry, 'materials': materials, 'unknown_material_surfaces': len(materials)-len(estimated),
               'physical_validation': False, 'source_sha256': _sha(__file__),
               'evidence_scope': 'Controlled synthetic material profiles and supplied contextual palettes; no real material/color accuracy or generalization claim.',
               'results': {name: {'result_id': r['result_id'], 'runtime_s': r['runtime_s']} for name,r in results.items()}}
    _save(root/'summary.json', summary)
    return summary


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--render-only', action='store_true', help='write controlled recordings without processing')
    args = parser.parse_args()
    if args.render_only:
        render(args.output)
    else:
        report = run_demo(args.output)
        print(json.dumps({'status': report['status'], 'checks': report['checks'],
                          'unknown_material_surfaces': report['unknown_material_surfaces']}, indent=2))
        raise SystemExit(0 if report['status']=='passed' else 2)
