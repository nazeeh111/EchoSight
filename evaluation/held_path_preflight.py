"""Check an ideal echo catalog against an exactly-one-candidate validation gate.

Evaluation only. Supply every required path before collecting evaluation audio.
Passing establishes compatibility of the declared catalog with the gate, not
echo audibility, detector resolution, calibration accuracy or measured success.
"""
import argparse
import hashlib
import json
import math
from pathlib import Path


def _number(value, name):
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
        raise ValueError(f'{name} must be a finite number')
    return value


def _identifiers(values, name):
    if not isinstance(values, list) or not values or any(not isinstance(v, str) or not v.strip() for v in values):
        raise ValueError(f'{name} must be a nonempty list of identifiers')
    if len(set(values)) != len(values):
        raise ValueError(f'{name} must contain distinct identifiers')
    return set(values)


def check_plan(plan):
    """Reject ideal candidate collisions without modifying acceptance criteria.

    Each catalog must contain exactly the declared path identifiers. Completeness
    is relative to that declaration; this cannot detect omitted physical paths.
    Exact ideal delays act as both predictions and candidate arrivals. Inclusive
    windows match the original transfer evaluator's ``abs(error) <= window``.
    """
    window = _number(plan['candidate_window_s'], 'candidate_window_s')
    if window <= 0:
        raise ValueError('candidate_window_s must be positive')
    required = _identifiers(plan['required_path_ids'], 'required_path_ids')
    captures = plan['captures']
    if not isinstance(captures, list) or not captures:
        raise ValueError('captures must be a nonempty list')
    _identifiers([c['capture_id'] for c in captures], 'capture identifiers')
    rows = []
    for capture in captures:
        paths = capture['paths']
        if not isinstance(paths, list):
            raise ValueError('paths must be a list')
        if _identifiers([p['path_id'] for p in paths], 'path identifiers') != required:
            raise ValueError('every capture must contain exactly the required paths')
        delays = {}
        for path in paths:
            delay = _number(path['excess_delay_s'], 'excess_delay_s')
            if delay <= 0:
                raise ValueError('reflection excess_delay_s must be positive')
            delays[path['path_id']] = delay
        associations = [dict(path_id=key, eligible_path_ids=[other for other, arrival in delays.items()
                        if abs(arrival - prediction) <= window]) for key, prediction in delays.items()]
        pairs = [dict(path_ids=[a, b], separation_s=abs(delays[a] - delays[b]))
                 for i, a in enumerate(delays) for b in list(delays)[i + 1:]]
        unique = sum(len(row['eligible_path_ids']) == 1 for row in associations)
        rows.append(dict(capture_id=capture['capture_id'], expected=len(delays), unique=unique,
                         ideal_gate_pass=unique == len(delays), associations=associations,
                         conflicting_pairs=[pair for pair in pairs if pair['separation_s'] <= window],
                         minimum_pair_separation_s=min((p['separation_s'] for p in pairs), default=None),
                         all_windows_disjoint=all(p['separation_s'] > 2 * window for p in pairs)))
    return dict(candidate_window_s=window, expected=sum(r['expected'] for r in rows),
                unique=sum(r['unique'] for r in rows), ideal_gate_pass=all(r['ideal_gate_pass'] for r in rows),
                captures=rows,
                scope='Ideal declared catalog only; no audio processing or acceptance rescore. A pass does not qualify real extraction or physical accuracy.')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('plan', type=Path)
    parser.add_argument('--output', type=Path, required=True, help='New output file; existing files are preserved')
    args = parser.parse_args()
    raw = args.plan.read_bytes()
    result = check_plan(json.loads(raw))
    result['plan_sha256'] = hashlib.sha256(raw).hexdigest()
    with args.output.open('x') as stream:
        json.dump(result, stream, indent=2, allow_nan=False)
        stream.write('\n')
    print(json.dumps({key: result[key] for key in ('ideal_gate_pass', 'unique', 'expected')}))
    return 0 if result['ideal_gate_pass'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
