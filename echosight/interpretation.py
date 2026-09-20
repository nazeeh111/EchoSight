"""Supplied reference-profile comparisons and contextual appearance mixtures.

Probabilities are conditional model/view weights, not calibrated physical truth.
No semantic profile, optical measurement, or measurement precision is invented.
"""
from collections import Counter
import copy
import hashlib
import json
import math
import re
import numpy as np
from .material_features import FEATURE_VERSION, extract_surface_features

_HASH = re.compile(r'[0-9a-f]{64}\Z')
_ID = re.compile(r'[A-Za-z0-9][A-Za-z0-9_.:-]{0,159}\Z')
MAX_PROFILES = 32
MAX_VIEWS = 64
MAX_SURFACES = 32
MATERIAL_SEMANTICS = 'equal_mixture_over_usable_views_conditional_on_reference_library_not_physical_confidence'
APPEARANCE_SEMANTICS = 'supplied_contextual_srgb_prediction_not_optical_measurement_or_acoustic_false_color'


def _object(value, required, optional=()):
    if not isinstance(value, dict) or set(value) - set(required) - set(optional) or not set(required) <= set(value):
        raise ValueError('invalid interpretation object fields')


def _number(value, low, high, *, positive=False):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError('interpretation value must be a JSON number')
    try:
        value = float(value)
    except (OverflowError, ValueError):
        raise ValueError('interpretation number is out of range') from None
    if not math.isfinite(value) or not low <= value <= high or (positive and value <= 0):
        raise ValueError('interpretation number is out of range')
    return value


def _text(value, maximum=160, *, identifier=False):
    if not isinstance(value, str) or not 1 <= len(value) <= maximum or (identifier and not _ID.fullmatch(value)):
        raise ValueError('invalid interpretation text')
    return value


def _array(value, minimum, maximum):
    if not isinstance(value, list) or not minimum <= len(value) <= maximum:
        raise ValueError('invalid interpretation array size')
    return value


def _hashes(value):
    values = _array(value, 1, MAX_VIEWS)
    if any(not isinstance(v, str) or not _HASH.fullmatch(v) for v in values) or len(set(values)) != len(values):
        raise ValueError('invalid or duplicated reference hashes')
    return list(values)


def _provenance(value):
    _object(value, ('kind', 'note'))
    if value['kind'] not in ('measured', 'simulated', 'supplied'):
        raise ValueError('invalid reference provenance kind')
    return dict(kind=value['kind'], note=_text(value['note'], 2048))


def _appearance(value):
    _object(value, ('provenance', 'colors'))
    colors = []
    for color in _array(value['colors'], 0, 32):
        _object(color, ('color_srgb', 'probability'))
        rgb = color['color_srgb']
        if not isinstance(rgb, str) or re.fullmatch(r'#[0-9A-Fa-f]{6}', rgb) is None:
            raise ValueError('invalid contextual sRGB color')
        colors.append(dict(color_srgb=rgb.upper(), probability=_number(color['probability'], 0, 1)))
    if len({c['color_srgb'] for c in colors}) != len(colors):
        raise ValueError('duplicate contextual colors')
    if math.fsum(c['probability'] for c in colors) > 1 + 1e-12:
        raise ValueError('appearance probabilities exceed one')
    # Correct only floating summation excess within the stated tolerance.
    total = math.fsum(c['probability'] for c in colors)
    if total > 1:
        for color in colors:
            color['probability'] /= total
    return dict(provenance=_provenance(value['provenance']), colors=colors)


def _profile(value):
    required = ('material_id', 'label', 'feature_version', 'probe_sha256', 'route_id',
                'incidence_angle_range_deg', 'mean_db', 'predictive_covariance_db2', 'prior_weight',
                'training_recording_sha256', 'training_waveform_sha256', 'provenance')
    _object(value, required, ('appearance', 'reference_summary'))
    out = {k: _text(value[k], identifier=True) for k in ('material_id', 'feature_version', 'route_id')}
    out['label'] = _text(value['label'], 160)
    out['probe_sha256'] = _hashes([value['probe_sha256']])[0]
    angle = [_number(x, 0, 90) for x in _array(value['incidence_angle_range_deg'], 2, 2)]
    if angle[0] > angle[1]:
        raise ValueError('reference angle domain is reversed')
    out['incidence_angle_range_deg'] = angle
    out['mean_db'] = [_number(x, -500, 500) for x in _array(value['mean_db'], 4, 4)]
    cov = np.array([[_number(x, -1e6, 1e6) for x in _array(row, 4, 4)]
                    for row in _array(value['predictive_covariance_db2'], 4, 4)])
    if not np.allclose(cov, cov.T, rtol=1e-10, atol=1e-12):
        raise ValueError('predictive covariance must be symmetric')
    cov = (cov + cov.T) / 2
    try:
        np.linalg.cholesky(cov)
    except np.linalg.LinAlgError:
        raise ValueError('predictive covariance must be positive definite; no automatic floor') from None
    out['predictive_covariance_db2'] = cov.tolist()
    out['prior_weight'] = _number(value['prior_weight'], 0, 1e12, positive=True)
    out['training_recording_sha256'] = _hashes(value['training_recording_sha256'])
    out['training_waveform_sha256'] = _hashes(value['training_waveform_sha256'])
    if len(out['training_recording_sha256']) != len(out['training_waveform_sha256']):
        raise ValueError('reference byte and waveform hash counts differ')
    out['provenance'] = _provenance(value['provenance'])
    if 'appearance' in value:
        out['appearance'] = _appearance(value['appearance'])
    if 'reference_summary' in value:
        r = value['reference_summary']
        _object(r, ('source_result_id', 'sample_count', 'regularization_std_db', 'qualification', 'spreading_model', 'capture_ids'))
        if type(r['sample_count']) is not int or not 5 <= r['sample_count'] <= MAX_VIEWS:
            raise ValueError('invalid reference sample count')
        if r['sample_count'] != len(out['training_recording_sha256']):
            raise ValueError('reference sample and identity counts differ')
        if r['qualification'] != 'not_evaluated' or r['spreading_model'] != 'spherical_pressure_inverse_distance':
            raise ValueError('unsupported reference qualification or spreading model')
        ids = [_text(x) for x in _array(r['capture_ids'], r['sample_count'], r['sample_count'])]
        out['reference_summary'] = dict(source_result_id=_text(r['source_result_id']), sample_count=r['sample_count'],
            regularization_std_db=_number(r['regularization_std_db'], 0, 100), qualification=r['qualification'],
            spreading_model=r['spreading_model'], capture_ids=ids)
    return out


def validate_context(context):
    """Return a bounded canonical deep copy; invalid public inputs raise ValueError."""
    if context is None:
        return None
    _object(context, ('schema_version', 'route_id', 'profiles', 'maximum_squared_distance', 'minimum_views'))
    if context['schema_version'] != '1.0':
        raise ValueError('unsupported interpretation context version')
    if type(context['minimum_views']) is not int or not 1 <= context['minimum_views'] <= MAX_VIEWS:
        raise ValueError('minimum_views must be an integer from 1 to 64')
    profiles = [_profile(p) for p in _array(context['profiles'], 0, MAX_PROFILES)]
    if len({p['material_id'] for p in profiles}) != len(profiles):
        raise ValueError('duplicate material profile identity')
    out = dict(schema_version='1.0', route_id=_text(context['route_id'], identifier=True), profiles=profiles,
               maximum_squared_distance=_number(context['maximum_squared_distance'], 0, 1e9, positive=True),
               minimum_views=context['minimum_views'])
    if len(json.dumps(out, allow_nan=False).encode()) > 1048576:
        raise ValueError('interpretation context exceeds one MiB')
    return out


def context_fingerprint(context):
    canonical = validate_context(context)
    if canonical is None:
        return None
    return hashlib.sha256(json.dumps(canonical, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()).hexdigest()


def _rejected(row, code):
    row['status'] = 'unknown'
    row.setdefault('diagnostic_codes', []).append(code)


def _independent_rows(rows):
    rows = copy.deepcopy(rows)
    for key in ('recording_sha256', 'waveform_sha256'):
        counts = Counter(r.get(key) for r in rows if r.get(key))
        for row in rows:
            if counts.get(row.get(key), 0) > 1:
                _rejected(row, 'duplicate_query_' + key)
    return rows


def _cancelled(cancel):
    return cancel is not None and bool(cancel())


def interpret_scene(result, context, cancel=None):
    """Compute a separate interpretation; never mutate acoustic geometry/evidence."""
    context = validate_context(context)
    out = dict(schema_version='1.0', context_id=context_fingerprint(context), source_result_id=result.get('result_id'),
               status='not_configured' if context is None else 'complete', surface_interpretations=[])
    def cancelled_result():
        return dict(out, status='cancelled', surface_interpretations=[])
    if _cancelled(cancel) or result.get('status') == 'cancelled':
        return cancelled_result()
    if context is None:
        return out
    surfaces = result.get('surfaces', [])
    if not isinstance(surfaces, list) or len(surfaces) > MAX_SURFACES:
        raise ValueError('interpretation surface resource limit')
    if not surfaces:
        return dict(out, status='no_geometry')
    profiles = context['profiles']
    reference_bytes = {h for p in profiles for h in p['training_recording_sha256']}
    reference_waves = {h for p in profiles for h in p['training_waveform_sha256']}
    for surface in surfaces:
        if _cancelled(cancel):
            return cancelled_result()
        rows = extract_surface_features(result, surface, cancel=cancel)
        if not isinstance(rows, list) or len(rows) > MAX_VIEWS:
            raise ValueError('interpretation support resource limit')
        rows = _independent_rows(rows)
        mass = np.zeros(len(profiles)); valid = 0
        for row in rows:
            if _cancelled(cancel) or 'cancelled' in row.get('diagnostic_codes', []):
                return cancelled_result()
            if row.get('status') != 'ok':
                continue
            if row.get('recording_sha256') in reference_bytes or row.get('waveform_sha256') in reference_waves:
                _rejected(row, 'reference_query_overlap'); continue
            try:
                _hashes([row.get('recording_sha256')]); _hashes([row.get('waveform_sha256')])
                x = np.array([_number(v, -500, 500) for v in _array(row.get('feature_db'), 4, 4)])
                angle = _number(row.get('incidence_angle_deg'), 0, 90)
            except ValueError:
                _rejected(row, 'invalid_feature_or_identity'); continue
            logs = []; indices = []; distances = []
            for k, p in enumerate(profiles):
                if (p['route_id'] != context['route_id'] or p['feature_version'] != row.get('feature_version') or
                    p['probe_sha256'] != row.get('probe_sha256') or not p['incidence_angle_range_deg'][0] <= angle <= p['incidence_angle_range_deg'][1]):
                    continue
                L = np.linalg.cholesky(p['predictive_covariance_db2'])
                with np.errstate(over='ignore', invalid='ignore'):
                    z = np.linalg.solve(L, x - np.array(p['mean_db'])); d = float(z @ z)
                if not math.isfinite(d):
                    row.setdefault('diagnostic_codes', []).append('reference_distance_out_of_numeric_range')
                    continue
                distances.append(dict(material_id=p['material_id'], squared_distance=d))
                if d > context['maximum_squared_distance']:
                    continue
                logs.append(math.log(p['prior_weight']) - .5 * (d + 2 * np.log(np.diag(L)).sum() + 4 * math.log(2 * math.pi)))
                indices.append(k)
            row['profile_distances'] = distances
            if not indices:
                _rejected(row, 'out_of_reference_domain' if distances else 'no_compatible_reference_profile'); continue
            weights = np.exp(np.array(logs) - max(logs)); weights /= weights.sum()
            row['material_probabilities'] = [dict(material_id=profiles[k]['material_id'], probability=float(w)) for k, w in zip(indices, weights)]
            for k, w in zip(indices, weights):
                mass[k] += w
            valid += 1
        total = len(rows)
        enough = valid >= context['minimum_views']
        mass = mass / valid if enough else np.zeros(len(profiles))
        probabilities = [dict(material_id=p['material_id'], label=p['label'], probability=float(w)) for p, w in zip(profiles, mass) if w > 0]
        coverage = valid / total if total else 0.
        material = dict(status='estimated' if enough else 'unknown', probabilities=probabilities,
            total_views=total, valid_views=valid, required_views=context['minimum_views'],
            evidence_coverage=coverage, unassigned_view_weight=1 - coverage, semantics=MATERIAL_SEMANTICS,
            diagnostic_codes=[] if enough else ['insufficient_independent_material_views'])
        color_terms = {}
        for p, weight in zip(profiles, mass):
            for color in p.get('appearance', {}).get('colors', []):
                color_terms.setdefault(color['color_srgb'], []).append(float(weight) * color['probability'])
        colors = [dict(color_srgb=rgb, probability=math.fsum(terms))
                  for rgb, terms in sorted(color_terms.items()) if math.fsum(terms) > 0]
        assigned_color_mass = math.fsum(c['probability'] for c in colors)
        if assigned_color_mass > 1:
            if assigned_color_mass > 1 + 1e-12:
                raise ValueError('contextual color mixture exceeds probability mass')
            # Repair only positive roundoff above one. Genuine missing palette
            # mass is never normalized away, including tiny deficits below one.
            for color in colors:
                color['probability'] /= assigned_color_mass
            assigned_color_mass = math.fsum(c['probability'] for c in colors)
        appearance = dict(status='estimated' if colors else 'unknown', colors=colors,
            unassigned_probability=max(0., 1 - assigned_color_mass), semantics=APPEARANCE_SEMANTICS)
        out['surface_interpretations'].append(dict(surface_id=surface['surface_id'], material=material, appearance=appearance, feature_records=rows))
    return cancelled_result() if _cancelled(cancel) else out


def build_material_profile(result, surface_id, *, material_id, label, route_id, prior_weight=1,
                           regularization_std_db=0, appearance=None, provenance):
    """Fit a labeled empirical predictive profile, without held-out qualification."""
    _number(regularization_std_db, 0, 100)
    if result.get('status') not in ('ok', 'partial'):
        raise ValueError('material reference requires current definitive geometry')
    matches = [s for s in result.get('surfaces', []) if s.get('surface_id') == surface_id]
    if len(matches) != 1:
        raise ValueError('material reference surface is missing or ambiguous')
    rows = _independent_rows(extract_surface_features(result, matches[0]))
    rows = [r for r in rows if r.get('status') == 'ok']
    if not 5 <= len(rows) <= MAX_VIEWS:
        raise ValueError('material reference requires at least five independent valid views')
    probes = {r.get('probe_sha256') for r in rows}; versions = {r.get('feature_version') for r in rows}
    if len(probes) != 1 or versions != {FEATURE_VERSION}:
        raise ValueError('material reference feature definitions differ')
    vectors = np.array([[_number(v, -500, 500) for v in _array(r.get('feature_db'), 4, 4)] for r in rows])
    angles = [_number(r.get('incidence_angle_deg'), 0, 90) for r in rows]
    covariance = np.cov(vectors, rowvar=False, ddof=1) + np.eye(4) * regularization_std_db ** 2
    profile = dict(material_id=material_id, label=label, route_id=route_id, feature_version=FEATURE_VERSION,
        probe_sha256=next(iter(probes)), incidence_angle_range_deg=[min(angles), max(angles)],
        mean_db=vectors.mean(axis=0).tolist(), predictive_covariance_db2=covariance.tolist(), prior_weight=prior_weight,
        training_recording_sha256=[r.get('recording_sha256') for r in rows], training_waveform_sha256=[r.get('waveform_sha256') for r in rows],
        provenance=provenance, reference_summary=dict(source_result_id=result.get('result_id'), sample_count=len(rows),
        regularization_std_db=regularization_std_db, qualification='not_evaluated', spreading_model='spherical_pressure_inverse_distance',
        capture_ids=[r.get('capture_id') for r in rows]))
    if appearance is not None:
        profile['appearance'] = appearance
    return _profile(profile)
