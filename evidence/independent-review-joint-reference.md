# Independent review of the frozen two-reference development trial

No material P1/P2 scientific or protocol-conformance defect was found in this bounded trial. The two saved single-source fits pass the frozen original gates, and the four dual-source pairs remain admission rejections. The conclusion `bounded_development_pass_only` follows. This is evidence that joint use of the supplied reference surveys resolves the exposed valid-control failure on these two cases; it is not room mapping, physical source qualification, demonstrated confidence coverage or grounds for production promotion by itself.

## Scope and integrity

Reviewed `docs/CHARTER.md`, `docs/CHARTER_ADDENDUM.md`, the previous review's bounded next-experiment specification, and the joint protocol, runner, precheck, admissions, fitted results and report. Compared the relevant candidate selection, partitions and numerical gates directly with the retained original `core/echosight/calibration.py`. This was a fresh scientific review of this trial, not a repeat of the prior source-calibration archive review or an assembled-backend review.

Verified freeze SHA-256 `1b59eb563ba72e29eebf1244a3eb59272e9d8c97f42eaa147d5bac5970e2b941`, protocol/runner/precheck hashes and all 223 frozen input hashes, including 144 original V2 WAVs. Independently checked those WAV hashes against the existing manifests and observation recording hashes. Both standalone fit files agree exactly with their copies inside results.json. All six pair admissions retain all 24 original records, the supplied receiver surveys, and the exact original per-reference eight training/four held capture partitions. All raw and waveform hashes within each pair are distinct. This confirms preserved bytes and the executable freeze boundary, not an external timestamp attestation or an independent observation of the fits' execution history.

The runner contains exactly one fixed-weight nonlinear solve per admitted single seed, in seed order, with nominal initialization, the declared bounds and tolerances, and no restarts. Only the 16 training delays enter its objective; held rows enter subsequent validation. Generating truth is hashed as bytes during integrity checking, but decoded only after both saved fit records. Admission, model, covariance and acceptance do not consume generating truth. Post-fit descriptive truth errors were independently recalculated and agree.

## Independently checked mathematics

For the image source `q = s + 2(d − n·s)n`, define `u_q = (q−r)/|q−r|`, `u_s = (s−r)/|s−r|`, and `f = (|q−r| − |s−r|)/v`. The source derivative is `(u_q − 2n(n·u_q) − u_s)/v`, the receiver derivative is `(u_s − u_q)/v`, and the log-speed derivative is `−f`. Reference derivatives are `2(u_q·n)/v` for offset and `2[(d−n·s)(u_q·a) − (s·a)(u_q·n)]/v` for each unit tangent direction `a`. The reported physical-parameter covariance correctly transforms log-effective-speed sensitivity by multiplying that coordinate by fitted effective speed. Effective speed remains distance per source-buffer second; physical propagation speed and source-clock scale are not separately identified.

A separate implementation of prediction and derivatives, without importing the trial runner, agrees with centered finite differences at both nominal and fitted points for both seeds. The largest discrepancy is below 3.13×10⁻¹². The independent covariance reconstruction uses 12 receiver-position nuisance vectors shared across each x/y pair and six reference nuisance coordinates shared across their respective captures. It reproduces every saved nominal/fitted component, the fixed-weight estimator sensitivity K, parameter covariance and held residual covariance. No source prior was inferred from the 15 cm search bound.

K was recalculated using a Cholesky-whitened singular-value decomposition rather than the runner's normal-equation solve. Held covariance was independently expanded as

`C_hh + H_h K C_tt* Kᵀ H_hᵀ − C_ht Kᵀ H_hᵀ − H_h K C_th`.

It agrees with direct propagation through the full 24-observation covariance. Receiver cross-reference terms are nonzero (maximum approximately 7.35×10⁻¹¹ s²), as are training/held reference terms (approximately 3.21×10⁻¹⁰ s²). Omitting the shared cross terms would overstate individual held variances by approximately 7.1–14.5% here. The retained implementation correctly subtracts them. Both reported noise inflation factors are 1, so the rule's greater-than-one branch is inspected algebraically but is not exercised by these saved cases.

For unknown paired timing correlation, independently enumerated all 4,096 assignments of the 12 pair correlations to −1 or +1 with the fitted estimator held fixed. This reproduces every reported scalar maximum parameter variance and minimum/maximum held variance. Each scalar endpoint is exact for the declared pairwise correlation family and marginal timing variances; the collection of extrema need not be jointly attainable. The normalized RMS obtained from all scalar minimum variances is a conservative envelope, not necessarily the attained maximum for one correlation assignment. The report explains this distinction. This calculation does not cover arbitrary across-stop dependence, systematic timing bias or nonlinear model mismatch.

## Frozen gate and numerical results

| Seed | Reference | Training normalized RMS | Held normalized RMS | Held maximum abs z | Held RMS µs | Held maximum abs µs |
|---|---|---:|---:|---:|---:|---:|
| 2821 | x | 0.09824 | 0.10298 | 0.14365 | 7.083 | 10.054 |
| 2821 | y | 0.08884 | 0.07996 | 0.11530 | 5.559 | 8.293 |
| 2833 | x | 0.20128 | 0.08747 | 0.16135 | 5.911 | 10.904 |
| 2833 | y | 0.06754 | 0.14810 | 0.20406 | 10.571 | 14.809 |

All residuals, nominal predictions, normalized metrics and gate decisions reproduce. Gates remain training/held normalized RMS ≤2.5, maximum held |z| ≤3.5, held RMS ≤100 µs and maximum absolute held residual ≤200 µs. The source-radius and bound margins pass. Whitened Jacobian minimum/maximum singular-value ratios are approximately 0.09741 and 0.09739 against the frozen 0.0001 threshold. The saved optimizer success and seven evaluations per fit are source-reported execution facts; independently recalculated objectives and near-zero gradients support the reported stationary solutions. No optimizer was rerun during review.

Nominal source-axis standard deviations are approximately 1.69/2.47/1.87 cm, with speed standard deviations 3.879 and 3.889 m/s. Worst scalar paired-correlation values are approximately 2.19/2.90/2.56 cm and 4.913/4.926 m/s. Under the minimum held scalar variances, maximum reported |z| is 0.230713 and the largest normalized RMS envelope is 0.165118. Sensitivity is reported alongside nominal decisions and never rescues a failing gate.

Both same-phase dual pairs retain missing and ambiguous paths; both opposite-phase pairs retain two eligible y-reference paths at every stop. No dual fit runs and no ambiguous path is selected. Those rejections establish only the frozen admission outcome on these particular surrogates. The original one-reference failure is still preserved. The report correctly distinguishes its all-12-record transfer metric from the joint experiment's four held records per reference; they must not be presented as an equal-partition improvement ratio.

## Conclusion, limits and reproduction

The prescribed bounded experiment is complete and its limited pass conclusion is supported. There is no requested scientific repair or justification to repeat these fits, tune to these exposed answers, relax gates or generate new families. Preserve the result as development evidence and return to the charter's consequential recording-to-3D gaps. Any later production integration needs an explicit mapping benefit and appropriate independent evidence for its assumptions.

This review checked saved mathematics and fixed decisions, not global nonlinear identifiability, empirical uncertainty coverage, a new measured dataset, an actual distributed speaker, iPhone hardware, complete mapping behavior or final repository packaging/commit identity. The conditional covariance is explicitly a local Gauss–Newton approximation; neither it nor two small post-fit truth errors establish calibrated confidence. The trial's reference planes are supplied calibration information, not acoustically inferred room surfaces.

Independent code and detailed numeric evidence are `work/review-joint-reference/check.py`, `check.json` and `check.log`. Reproduce from the repository root with `.venv/bin/python work/review-joint-reference/check.py`; it reads the retained trial and original inputs, runs no optimizer or simulator, and writes only its own check.json. The executed check exited successfully. The largest absolute saved-array comparison discrepancy was below 9.95×10⁻¹³ (arrays have different units; this aggregate is only a computational agreement check). Every individual comparison and derivative error is retained in the JSON. No runtime files, tests, trial files, HEAD or index were changed by this review.

Coordinator packaging note: exact independent checker and outputs are preserved in [joint-reference-review](joint-reference-review/README.md).
