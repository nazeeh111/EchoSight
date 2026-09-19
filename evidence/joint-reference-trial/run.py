"""Bounded existing-data experiment. No generation or production imports."""
from pathlib import Path
import argparse
import hashlib
import json
import platform
import time
import numpy as np
import scipy
from scipy.linalg import solve_triangular
from scipy.optimize import least_squares

P = Path(__file__).resolve().parent
ROOT = P.parents[1]
OLD = ROOT / 'work/source-calibration-mismatch'
RAW = OLD / 'run-v2/raw'
SEEDS = (2821, 2833)
PATTERNS = ('single', 'dual_same_phase', 'dual_opposite_phase')
TRAIN = np.r_[np.arange(8), np.arange(12, 20)]
HELD = np.r_[np.arange(8, 12), np.arange(20, 24)]


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read(path):
    return json.loads(path.read_text())


def save(path, obj):
    path.write_text(json.dumps(obj, indent=2, allow_nan=False) + '\n')


def input_hashes():
    paths = [OLD / 'run-v2/freeze.json', OLD / 'run-v2/results.json',
             OLD / 'run-v2/input-manifests.json', OLD / 'V2-PROTOCOL.md',
             OLD / 'run_v2.py', OLD / 'joint_information.py',
             OLD / 'core/echosight/calibration.py']
    for pattern in PATTERNS:
        for seed in SEEDS:
            for plane in ('x', 'y'):
                folder = RAW / f'{pattern}-{seed}-{plane}'
                manifest = read(folder / 'manifest.json')
                for name, digest in manifest['raw'].items():
                    assert sha(folder / name) == digest, (folder, name)
                assert sha(folder / 'truth.json') == manifest['truth_sha256']
                assert len(manifest['raw']) == 12
                paths.extend(folder / name for name in manifest['raw'])
                paths.extend(folder / name for name in ('session.json', 'reference.json',
                             'observations.json', 'manifest.json', 'truth.json', 'calibration.json'))
    return {str(path.relative_to(ROOT)): sha(path) for path in sorted(paths)}


def source_hashes():
    return {name: sha(P / name) for name in ('PROTOCOL.md', 'run.py')}


def load_pair(pattern, seed):
    sessions, references, rows, admissions = [], [], [], []
    for plane in ('x', 'y'):
        folder = RAW / f'{pattern}-{seed}-{plane}'
        session, reference, result = [read(folder / name) for name in
                                     ('session.json', 'reference.json', 'observations.json')]
        sessions.append(session)
        references.append(reference)
        train, held = reference['training_capture_ids'], reference['validation_capture_ids']
        assert train == [f'capture-{i:02d}' for i in range(8)]
        assert held == [f'capture-{i:02d}' for i in range(8, 12)]
        assert reference['source_search_radius_m'] == .15
        assert reference['effective_speed_bounds_m_s'] == [300., 380.]
        captures = {c['capture_id']: c for c in session['captures']}
        observations = {o['capture_id']: o for o in result['observations']}
        assert len(captures) == len(observations) == 12
        s, n = np.array(session['source_position_m']), np.array(reference['normal'])
        q = s + 2 * (reference['offset_m'] - n @ s) * n
        for cid in train + held:
            capture, observation = captures[cid], observations[cid]
            r = np.array(capture['receiver_position_m'])
            length = np.linalg.norm(r-q) - np.linalg.norm(r-s)
            low, high = max(0., (length-.3)/380.), (length+.3)/300.
            candidates = [c for c in observation.get('candidates', []) if low <= c['delay_s'] <= high]
            valid = observation['status'] == 'ok' and len(candidates) == 1
            assert observation['recording_sha256'] == sha(folder / capture['recording_path'])
            admissions.append(dict(reference=plane, capture_id=cid,
                partition='training' if cid in train else 'validation',
                observation_status=observation['status'], eligible_candidates=len(candidates),
                window_s=[low, high], accepted=valid,
                candidate_id=candidates[0]['candidate_id'] if valid else None))
            rows.append((capture, observation, candidates[0] if valid else None))
        assert result.get('source_declaration_consistency', {}).get('status') != 'contradictory'
    for i in range(12):
        for key in ('receiver_position_m', 'receiver_position_std_m', 'receiver_pose_group_id'):
            assert rows[i][0][key] == rows[i+12][0][key]
    assert sessions[0]['source_position_m'] == sessions[1]['source_position_m']
    for key in ('recording_sha256', 'waveform_sha256'):
        hashes = [r[1].get(key) for r in rows]
        assert None not in hashes and len(set(hashes)) == 24
    pair = dict(pattern=pattern, seed=seed, sessions=sessions,
                references=references, rows=rows, admission=admissions,
                admitted=all(a['accepted'] for a in admissions))
    return pair


def initial(pair):
    session = pair['sessions'][0]
    v = session.get('effective_speed_m_s', session['sound_speed_m_s']/session['source_clock_scale'])
    return np.r_[session['source_position_m'], np.log(np.clip(v, 300.+1e-6, 380.-1e-6))]


def model(pair, theta):
    """Prediction and analytic Jacobians for source/log-speed, receiver and planes."""
    source, speed = theta[:3], np.exp(theta[3])
    f, H, D, G = np.zeros(24), np.zeros((24, 4)), np.zeros((24, 36)), np.zeros((24, 6))
    for j, ref in enumerate(pair['references']):
        n, d = np.array(ref['normal']), ref['offset_m']
        axis = np.eye(3)[np.argmin(abs(n))]
        u = np.cross(n, axis); u /= np.linalg.norm(u)
        w = np.cross(n, u)
        M = np.eye(3) - 2*np.outer(n, n)
        q = M @ source + 2*d*n
        for i in range(12):
            k = j*12+i
            r = np.array(pair['rows'][k][0]['receiver_position_m'])
            uq, us = q-r, source-r
            lq, ls = np.linalg.norm(uq), np.linalg.norm(us)
            uq, us = uq/lq, us/ls
            f[k] = (lq-ls)/speed
            H[k, :3] = (M @ uq-us)/speed
            H[k, 3] = -f[k]
            D[k, i*3:i*3+3] = (us-uq)/speed
            G[k, j*3] = 2*(uq @ n)/speed
            for aidx, a in enumerate((u, w), 1):
                G[k, j*3+aidx] = 2*uq @ (-(a @ source)*n + (d-n @ source)*a)/speed
    return f, H, D, G


def covariance(pair, theta):
    f, H, D, G = model(pair, theta)
    timing = []
    for capture, obs, candidate in pair['rows']:
        assert candidate is not None
        timing.append(candidate['delay_std_s']**2 + obs['direct_std_s']**2 +
                      (candidate['delay_s']*obs['clock']['alpha_std']/obs['clock']['alpha'])**2)
    T = np.diag(timing)
    R = np.diag(np.repeat([pair['rows'][i][0]['receiver_position_std_m']**2 for i in range(12)], 3))
    Q = np.diag([v for ref in pair['references'] for v in
                 (ref['offset_std_m']**2, ref['normal_std_rad']**2, ref['normal_std_rad']**2)])
    receiver, reference = D @ R @ D.T, G @ Q @ G.T
    return T+receiver+reference, T, receiver, reference


def finite_jac(fn, x):
    columns = []
    for i in range(len(x)):
        step = 1e-5 * max(1., abs(x[i]))
        delta = np.zeros(len(x)); delta[i] = step
        columns.append((fn(x+delta)-fn(x-delta))/(2*step))
    return np.column_stack(columns)


def precheck():
    import copy
    results = []
    for seed in SEEDS:
        pair = load_pair('single', seed)
        theta = initial(pair)
        f, H, D, G = model(pair, theta)
        hn = finite_jac(lambda t: model(pair, t)[0], theta)
        def perturb_receiver(x):
            p = copy.deepcopy(pair)
            for j in range(2):
                for i in range(12):
                    p['rows'][j*12+i][0]['receiver_position_m'] = (
                        np.array(pair['rows'][j*12+i][0]['receiver_position_m'])+x[3*i:3*i+3]).tolist()
            return model(p, theta)[0]
        def perturb_reference(x):
            p = copy.deepcopy(pair)
            for j, ref in enumerate(p['references']):
                n = np.array(ref['normal']); axis = np.eye(3)[np.argmin(abs(n))]
                u = np.cross(n, axis); u /= np.linalg.norm(u); w = np.cross(n, u)
                n = n+x[3*j+1]*u+x[3*j+2]*w; n /= np.linalg.norm(n)
                ref['normal'] = n.tolist(); ref['offset_m'] += x[3*j]
            return model(p, theta)[0]
        dn = finite_jac(perturb_receiver, np.zeros(36))
        gn = finite_jac(perturb_reference, np.zeros(6))
        errors = dict(source_log_speed=float(np.max(abs(H-hn))),
                      receiver=float(np.max(abs(D-dn))),
                      reference=float(np.max(abs(G-gn))))
        assert max(errors.values()) < 2e-10, errors
        C, T, R, Q = covariance(pair, theta)
        assert np.linalg.eigvalsh(C).min() > 0
        assert np.max(abs(R[:12, 12:])) > 0
        assert np.max(abs(C[np.ix_(HELD, TRAIN)])) > 0
        W = np.linalg.inv(C[np.ix_(TRAIN, TRAIN)])
        K = np.linalg.solve(H[TRAIN].T @ W @ H[TRAIN], H[TRAIN].T @ W)
        B = np.zeros((8, 24)); B[:, HELD] = np.eye(8); B[:, TRAIN] = -H[HELD] @ K
        covp = K @ C[np.ix_(TRAIN, TRAIN)] @ K.T
        direct = B @ C @ B.T
        expanded = C[np.ix_(HELD, HELD)] + H[HELD] @ covp @ H[HELD].T
        cross = C[np.ix_(HELD, TRAIN)] @ K.T @ H[HELD].T
        expanded -= cross+cross.T
        assert np.max(abs(direct-expanded)) < 1e-18
        results.append(dict(seed=seed, jacobian_max_abs_errors=errors,
                            held_covariance_expansion_max_abs_error=float(np.max(abs(direct-expanded))),
                            covariance_min_eigenvalue=float(np.linalg.eigvalsh(C).min())))
    return dict(no_optimizer_executed=True, rows=results)


def scalar_pair_extrema(A, T, inflation):
    """Exact scalar extrema for arbitrary per-pair correlation, estimator fixed."""
    addition = np.zeros(A.shape[0])
    for i in range(12):
        scale = inflation if i < 8 else 1.
        addition += abs(2*A[:, i]*A[:, i+12]*np.sqrt(T[i, i]*T[i+12, i+12])*scale)
    return addition


def fit_pair(pair):
    t0 = initial(pair)
    C0 = covariance(pair, t0)[0]
    L = np.linalg.cholesky(C0[np.ix_(TRAIN, TRAIN)])
    W = np.linalg.solve(L.T, np.linalg.solve(L, np.eye(16)))
    observed = np.array([r[2]['delay_s'] for r in pair['rows']])
    lo, hi = np.r_[t0[:3]-.15, np.log(300.)], np.r_[t0[:3]+.15, np.log(380.)]
    def residual(t):
        return solve_triangular(L, model(pair, t)[0][TRAIN]-observed[TRAIN], lower=True)
    start = time.perf_counter()
    fit = least_squares(residual, t0, jac=lambda t: solve_triangular(L, model(pair, t)[1][TRAIN], lower=True),
        bounds=(lo, hi), max_nfev=300, xtol=1e-11, ftol=1e-11, gtol=1e-11)
    elapsed = time.perf_counter()-start
    theta = fit.x
    prediction, H, D, G = model(pair, theta)
    C, T, R, Q = covariance(pair, theta)
    r = prediction-observed
    A = solve_triangular(L, H[TRAIN], lower=True)
    singular = np.linalg.svd(A, compute_uv=False)
    K = np.linalg.solve(H[TRAIN].T @ W @ H[TRAIN], H[TRAIN].T @ W)
    inflation = max(1., float(residual(theta) @ residual(theta)/12))
    Cstar = C.copy()
    Cstar[np.ix_(TRAIN, TRAIN)] += (inflation-1)*(T+R)[np.ix_(TRAIN, TRAIN)]
    cov = K @ Cstar[np.ix_(TRAIN, TRAIN)] @ K.T
    B = np.zeros((8, 24)); B[:, HELD] = np.eye(8); B[:, TRAIN] = -H[HELD] @ K
    held_cov = B @ Cstar @ B.T
    assert min(np.linalg.eigvalsh(held_cov)) > 0
    transform = np.diag([1., 1., 1., np.exp(theta[3])])
    pcov = transform @ cov @ transform
    parameter_map = np.zeros((4, 24)); parameter_map[:, TRAIN] = transform @ K
    pextra = scalar_pair_extrema(parameter_map, T, inflation)
    hextra = scalar_pair_extrema(B, T, inflation)
    hminimum = np.diag(held_cov)-hextra
    assert min(hminimum) > 0
    reports = []
    nominal = model(pair, t0)[0]
    for j, ref in enumerate(('x', 'y')):
        train, held, local = np.arange(12*j, 12*j+8), np.arange(12*j+8, 12*j+12), slice(4*j, 4*j+4)
        ztrain = r[train]/np.sqrt(np.diag(T+R)[train])
        zheld = r[held]/np.sqrt(np.diag(held_cov)[local])
        zrobust = r[held]/np.sqrt(hminimum[local])
        metrics = dict(training_normalized_rms=float(np.sqrt(np.mean(ztrain*ztrain))),
            validation_normalized_rms=float(np.sqrt(np.mean(zheld*zheld))),
            validation_max_abs_z=float(max(abs(zheld))),
            validation_nominal_rms_s=float(np.sqrt(np.mean((nominal[held]-observed[held])**2))),
            validation_fitted_rms_s=float(np.sqrt(np.mean(r[held]**2))),
            validation_max_abs_residual_s=float(max(abs(r[held]))))
        gates = dict(training_normalized_rms=metrics['training_normalized_rms'] <= 2.5,
            validation_normalized_rms=metrics['validation_normalized_rms'] <= 2.5,
            validation_max_abs_z=metrics['validation_max_abs_z'] <= 3.5,
            validation_fitted_rms_s=metrics['validation_fitted_rms_s'] <= .0001,
            validation_max_abs_residual_s=metrics['validation_max_abs_residual_s'] <= .0002)
        reports.append(dict(reference=ref, metrics=metrics, gates=gates, passed=all(gates.values()),
            pair_correlation_sensitivity=dict(maximum_normalized_rms=float(np.sqrt(np.mean(zrobust*zrobust))),
                                             maximum_abs_z=float(max(abs(zrobust))))))
    bound_gates = dict(optimizer_success=bool(fit.success),
        singular_ratio=float(singular[-1]/singular[0]) >= 1e-4,
        euclidean_radius=float(np.linalg.norm(theta[:3]-t0[:3])) < .98*.15,
        parameter_bound_margin=bool(min(theta-lo) >= 1e-6 and min(hi-theta) >= 1e-6))
    records = [dict(pair['admission'][i], observed_delay_s=float(observed[i]), predicted_delay_s=float(prediction[i]),
                    nominal_prediction_s=float(nominal[i]), residual_s=float(r[i])) for i in range(24)]
    return dict(seed=pair['seed'], passed=all(bound_gates.values()) and all(r['passed'] for r in reports),
        source_position_m=theta[:3].tolist(), effective_speed_m_s=float(np.exp(theta[3])),
        parameter_covariance=pcov.tolist(), parameter_std=np.sqrt(np.diag(pcov)).tolist(),
        pair_correlation_worst_parameter_std=np.sqrt(np.diag(pcov)+pextra).tolist(),
        held_residual_std_s=np.sqrt(np.diag(held_cov)).tolist(),
        pair_correlation_min_held_std_s=np.sqrt(hminimum).tolist(),
        pair_correlation_max_held_std_s=np.sqrt(np.diag(held_cov)+hextra).tolist(),
        optimizer=dict(success=bool(fit.success), nfev=fit.nfev, njev=fit.njev, message=fit.message,
                       cost=float(fit.cost), optimality=float(fit.optimality), runtime_s=elapsed),
        bound_gates=bound_gates, information_singular_values=singular.tolist(),
        training_noise_inflation=inflation, references=reports, records=records,
        matrices={k:v.tolist() for k,v in dict(nominal_covariance=C0, timing=T, receiver=R,
            reference=Q, fitted_covariance=C, inflated_covariance=Cstar, H=H, K=K,
            held_residual_covariance=held_cov).items()})


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('action', choices=('precheck', 'freeze', 'run'))
    parser.add_argument('--approved-freeze')
    args = parser.parse_args()
    if args.action == 'precheck':
        output = precheck(); save(P/'precheck.json', output); print(json.dumps(output)); return
    if args.action == 'freeze':
        assert not (P/'freeze.json').exists(), 'Preserve existing freeze'
        checks = precheck(); save(P/'precheck.json', checks)
        save(P/'freeze.json', dict(before_nonlinear_fitting=True, time_unix=time.time(),
            source_hashes=source_hashes(), input_hashes=input_hashes(),
            precheck_sha256=sha(P/'precheck.json'),
            environment=dict(python=platform.python_version(), numpy=np.__version__, scipy=scipy.__version__)))
        print('Frozen', sha(P/'freeze.json')); return
    freeze = read(P/'freeze.json')
    assert args.approved_freeze == sha(P/'freeze.json'), 'Coordinator must approve the exact freeze'
    assert source_hashes() == freeze['source_hashes']
    assert input_hashes() == freeze['input_hashes']
    assert not (P/'results.json').exists(), 'Preserve existing results'
    pairs = [load_pair(pattern, seed) for pattern in PATTERNS for seed in SEEDS]
    admissions = [dict(pattern=p['pattern'], seed=p['seed'], admitted=p['admitted'], records=p['admission']) for p in pairs]
    save(P/'admission.json', admissions)
    rows = []
    for pair in pairs[:2]:
        if pair['admitted']:
            row = fit_pair(pair)
        else:
            row = dict(seed=pair['seed'], passed=False, rejection='reference_path_unidentified')
        rows.append(row)
        save(P/f"fit-{pair['seed']}.json", row)
        print(pair['seed'], row['passed'], flush=True)
    # The fit records above are saved before any generating truth is decoded.
    evaluation = []
    for row in rows:
        if 'source_position_m' not in row:
            continue
        truth = read(RAW/f"single-{row['seed']}-x/truth.json")
        evaluation.append(dict(seed=row['seed'], generating_primary_m=truth['primary_m'],
            source_error_m=float(np.linalg.norm(np.array(row['source_position_m'])-truth['primary_m'])),
            effective_speed_error_m_s=row['effective_speed_m_s']-truth['effective_speed_m_s']))
    assert source_hashes() == freeze['source_hashes']
    assert input_hashes() == freeze['input_hashes']
    output = dict(freeze_sha256=sha(P/'freeze.json'), all_single_controls_passed=all(r['passed'] for r in rows),
        branch_decision='bounded_development_pass_only' if all(r['passed'] for r in rows) else 'closed_failed_original_gates',
        fits=rows, admissions=admissions, postfit_truth_evaluation=evaluation,
        limits=['two exposed development cases', 'conditional local covariance; no empirical coverage',
                'unknown paired timing correlation; fixed-estimator sensitivity only',
                'no room mapping, hardware qualification or runtime promotion'])
    save(P/'results.json', output)


if __name__ == '__main__':
    main()
