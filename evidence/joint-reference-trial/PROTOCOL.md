# Frozen joint-reference development trial

Question: does fitting two independently surveyed reference planes resolve the
documented single-source orthogonal-transfer failure on the two existing V2
controls? This is an exposed development experiment, not a new held-out family,
room-mapping result, device qualification or production feature.

## Inputs and admission

Use only `work/source-calibration-mismatch/run-v2/raw/`, seeds 2821 and 2833,
patterns single, dual_same_phase, dual_opposite_phase, references x and y. Hash
all 144 original WAVs and all supplied sessions, references, observations,
manifests and truth files before fitting. Verify raw hashes against the original
manifests and observation hashes. Preserve the original V2 results and original
one-reference transfer failures by hash; do not recompute or replace them.
Truth is unavailable to admission, fitting, covariance and acceptance; read it
only after saved fit results for descriptive source/speed errors.

For every pair, retain the original per-reference 8 training IDs 00–07 and four
held IDs 08–11. Use recorded observation status and exactly one candidate within
the original nominal path window: [max(0,(excess−2 radius)/380),
(excess+2 radius)/300]. No path labels, exclusions or alternative candidates.
Require unique raw and waveform hashes across all 24 records, consistent paired
receiver surveys/uncertainties and no contradictory native source declarations.
Run admission on all four dual pairs, reporting each missing/ambiguous record;
never fit a dual pair. Unexpected dual admission is reported without searching
or expanding scope.

## One fixed estimator

Fit only the 16 declared training delays. Initialize at the supplied source and
nominal effective speed (343 m/s here). Parameters are source x/y/z and log
effective speed, where effective speed is physical sound speed divided by source
clock scale. Physical speed and source clock are not separately estimated.
Use the existing image-source reflection prediction. Retain the original source
cube ±0.15 m, 300–380 m/s speed bounds, and final Euclidean source displacement
less than 0.98×0.15 m plus the original 1e-6 parameter-bound margin. No prior is
inferred from the search radius. Use one SciPy least_squares run per single
seed, max_nfev=300 and xtol=ftol=gtol=1e-11, no restarts or tuning.

The objective is generalized least squares with covariance frozen at the
supplied nominal point. Whiten by the Cholesky factor of the full 16×16 training
covariance. It includes timing, paired receiver and reference survey errors;
using fixed weights avoids optimizing an unstated parameter-dependent variance
objective. All covariance reported below is recomputed at the fitted point.

For 24 observations let C=T+D R Dᵀ+G Q Gᵀ. T is diagonal with the original
candidate delay variance + direct-delay variance + (delay alpha_std/alpha)².
R has the 12 supplied isotropic receiver variances, with each receiver error
reused across x/y observations. Q assumes independent x/y reference surveys, each
with one offset and two tangent-rotation variances shared across its 12 stops.
No source pose prior is added. Analytic source, receiver, log-speed and reference
Jacobians are checked against centered finite differences before fitting.

Let W=C_tt(nominal)^−1, H the fitted-point prediction Jacobian, and
K=(H_tᵀ W H_t)^−1 H_tᵀ W. This is the explicitly local Gauss–Newton sensitivity
of the frozen-weight estimator; nonlinear curvature is not certified. Set
inflation=max(1, r_tᵀ W r_t/(16−4)). As in the prior implementation, inflate
the training timing/receiver noise contribution only; retain shared reference
survey covariance unchanged. C_tt*=inflation (T+D R Dᵀ)_tt+(G Q Gᵀ)_tt,
C_hh and C_ht remain unchanged. Parameter covariance is K C_tt* Kᵀ.
Held residual covariance is
C_hh + H_h K C_tt* Kᵀ H_hᵀ − C_ht Kᵀ H_hᵀ − H_h K C_th.
Save all components, K, H and residual covariance so the shared terms are
independently inspectable. There is no global residual-based reduction of noise.

## Unchanged decisions, paired-noise sensitivity and stop rule

For each reference separately: training normalized RMS uses its original
diagonal timing-plus-receiver standard deviations (reference error is handled
as shared covariance); held normalized residuals use the square roots of the
full held residual covariance diagonal above. Require training normalized RMS
≤2.5, held normalized RMS ≤2.5, held maximum |z| ≤3.5, held absolute RMS ≤100 µs
and maximum absolute residual ≤200 µs. Retain optimizer success, source/speed
bound checks and whitened training Jacobian singular ratio ≥1e-4. Both references
must pass. Always report all residuals and nominal-versus-fitted held RMS.

Paired x/y clocks and additive noise were reused by the renderer. Nominal T is
diagonal, but this is not established timing independence. Keep the estimator
fixed and propagate pair correlations ρ_i∈[−1,+1] through the parameter and held
residual sandwich covariances, retaining receiver/reference terms and training
inflation. Report scalar worst-case standard deviations and normalized metrics
using each held residual's minimum possible variance. These scalar extrema need
not occur simultaneously and do not estimate correlation or establish coverage.
Primary acceptance uses the unchanged declared nominal gates; sensitivity is
reported alongside it, never used to rescue a failed gate.

Run the two predeclared single-source fits in seed order and retain both as the
one fixed trial. If either fails any original gate, close this scientific branch
with no follow-up tuning, new seeds, families or promotion. A dual admission
failure remains an admission rejection, not proof of physical distributed-source
detection. Even two passes establish only these two exposed synthetic cases;
they do not establish calibrated confidence, room mapping or physical accuracy.

## Execution boundary

Write this protocol, runner and finite-difference precheck; freeze their hashes
and all inputs before nonlinear fitting. Send the freeze to the coordinator and
wait for requirement review. `freeze` and `precheck` never call an optimizer.
Only `run --approved-freeze <exact freeze SHA256>` executes the two fits. No
production file, original data, runtime or scientific gate is changed. Save
results and a concise evidence report with environment and reproducible commands.
