"""Evaluation-only matching; no fit imports these ground-truth helpers."""
from __future__ import annotations
import numpy as np
from scipy.optimize import linear_sum_assignment


def score_surfaces(result, truth, maximum_normal_error_deg=5., maximum_offset_error_m=.15):
    predicted = result.get('surfaces', [])
    expected = truth.get('surfaces', [])
    errors = np.zeros((len(predicted), len(expected), 2))
    for i, p in enumerate(predicted):
        pn = np.asarray(p['normal'], float)
        for j, t in enumerate(expected):
            tn = np.asarray(t['normal'], float)
            dot = float(np.dot(pn, tn) / (np.linalg.norm(pn) * np.linalg.norm(tn)))
            sign = 1 if dot >= 0 else -1
            errors[i,j] = [np.degrees(np.arccos(np.clip(abs(dot), 0, 1))),
                           abs(float(p['offset_m']) - sign * float(t['offset_m']))]
    matches = []
    if predicted and expected:
        valid = ((errors[:,:,0] <= maximum_normal_error_deg) &
                 (errors[:,:,1] <= maximum_offset_error_m))
        # Maximum admissible cardinality precedes residual minimization.
        scale = max(len(predicted), len(expected)) + 1
        cost = (~valid).astype(float)*scale + np.minimum(errors[:,:,0]/maximum_normal_error_deg + errors[:,:,1]/maximum_offset_error_m, 2)/2
        rows, cols = linear_sum_assignment(cost)
        for i,j in zip(rows, cols):
            if not valid[i,j]:
                continue
            unc = predicted[i].get('uncertainty', {})
            offset_std = unc.get('offset_std_m')
            normal_std = unc.get('normal_std_deg')
            if normal_std is None and 'normal_angular_std_rad' in unc:
                normal_std = float(np.degrees(unc['normal_angular_std_rad']))
            matches.append({'predicted_id': predicted[i].get('surface_id', str(i)),
                            'truth_id': expected[j].get('surface_id', str(j)),
                            'normal_error_deg': float(errors[i,j,0]),
                            'offset_error_m': float(errors[i,j,1]),
                            'horizontal': abs(float(expected[j]['normal'][2])) >= .9,
                            'offset_95pct_covered': None if offset_std is None else bool(errors[i,j,1] <= 1.96*offset_std),
                            'normal_95pct_covered': None if normal_std is None else bool(errors[i,j,0] <= 1.96*normal_std)})
    return {'predicted_count': len(predicted), 'truth_count': len(expected),
            'matched_count': len(matches), 'false_surfaces': len(predicted)-len(matches),
            'missed_surfaces': len(expected)-len(matches),
            'horizontal_matched': sum(m['horizontal'] for m in matches),
            'precision': len(matches)/len(predicted) if predicted else None,
            'recall': len(matches)/len(expected) if expected else None,
            'matches': matches}


def acceptance_failures(scenario, result, metrics, runtime_seconds, acceptance):
    requirements = acceptance['requirements'][scenario]
    failures = []
    checks = [('minimum_matched_surfaces', metrics['matched_count'], lambda a,b:a>=b),
              ('minimum_horizontal_surfaces', metrics['horizontal_matched'], lambda a,b:a>=b),
              ('maximum_false_surfaces', metrics['false_surfaces'], lambda a,b:a<=b),
              ('maximum_definitive_surfaces', metrics['predicted_count'], lambda a,b:a<=b),
              ('maximum_runtime_seconds', runtime_seconds, lambda a,b:a<=b)]
    for name, value, test in checks:
        if name in requirements and not test(value, requirements[name]):
            failures.append(f'{name}: observed {value}, required {requirements[name]}')
    if 'allowed_status' in requirements and result['status'] not in requirements['allowed_status']:
        failures.append(f"status: observed {result['status']}, required {requirements['allowed_status']}")
    if requirements.get('require_diagnostics') and not result.get('diagnostics'):
        failures.append('required diagnostics missing')
    if requirements.get('forbid_closed_room_claim') and result.get('enclosure_status') == 'closed':
        failures.append('unsupported closed-room claim')
    return failures
