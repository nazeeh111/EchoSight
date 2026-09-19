# Two-reference source calibration: bounded development result

Both existing V2 single-source controls pass every frozen original acceptance gate when the two reference arrangements are fitted jointly. All four dual-source pairs fail candidate admission before fitting. This resolves the documented single-source transfer failure on these two exposed development cases only. It does not establish physical source qualification, calibrated uncertainty coverage or improved room mapping. No runtime code changed.

## Results

| Seed | Reference | Training normalized RMS | Held normalized RMS | Held max abs z | Held RMS (µs) | Held max abs (µs) |
|---|---|---:|---:|---:|---:|---:|
| 2821 | x | 0.09824 | 0.10298 | 0.14365 | 7.083 | 10.054 |
| 2821 | y | 0.08884 | 0.07996 | 0.11530 | 5.559 | 8.293 |
| 2833 | x | 0.20128 | 0.08747 | 0.16135 | 5.911 | 10.904 |
| 2833 | y | 0.06754 | 0.14810 | 0.20406 | 10.571 | 14.809 |

Unchanged limits: training/held normalized RMS ≤2.5, held maximum |z| ≤3.5, held absolute RMS ≤100 µs and maximum absolute residual ≤200 µs. Both optimizer runs also pass the source-radius, speed-bound and singular-value checks. Each used seven function/Jacobian evaluations, one nominal initialization and no restart. Timing/receiver training-noise inflation remained 1.0 in both cases.

| Seed | Fitted source xyz (m) | Effective speed (m/s) | Postfit source error (mm) | Speed error (m/s) |
|---|---|---:|---:|---:|
| 2821 | 1.54181921, 1.48357728, 1.31030007 | 346.44680131 | 4.024 | 0.446801 |
| 2833 | 1.54217296, 1.48043070, 1.31111109 | 346.53832869 | 2.478 | 0.538329 |

Generating truth was decoded only after the fitted results had been saved. These source errors are descriptive synthetic results, not an added acceptance threshold. Effective speed includes the source clock convention; physical sound speed and source clock rate are not separated.

Both same-phase dual pairs retain missing candidates and ambiguous y-reference paths. Both opposite-phase dual pairs have exactly two eligible y-reference candidates at all 12 stops. Every failed record is retained in admission.json; no candidate was selected from an ambiguous record and no dual-source optimizer ran. This is not a universal distributed-source detector.

The original one-reference outcomes remain unchanged. In particular, seed 2833 x-fit transfer to all 12 y records remains a failure (229.479 µs RMS / 282.680 µs maximum). The joint table above uses the predeclared four held records per reference, while the original transfer used all 12 y records; those statistics describe different tests. Original V1/V2 failures and their exact inputs remain preserved.

## Uncertainty and paired draws

Full covariance retains receiver-position errors shared across each x/y pair, plane-survey errors shared across each reference, and training/held cross terms. Independence between the two reference surveys is a supplied covariance assumption. The fit uses nominal frozen covariance weights; reported uncertainty is recomputed at the fitted point using the local Gauss–Newton sensitivity and a sandwich covariance. No search-radius prior is invented.

| Seed | Source xyz SD (cm) | Effective-speed SD (m/s) | Worst paired-correlation xyz SD (cm) | Worst speed SD (m/s) |
|---|---|---:|---|---:|
| 2821 | 1.686, 2.471, 1.872 | 3.879 | 2.190, 2.898, 2.555 | 4.913 |
| 2833 | 1.689, 2.468, 1.872 | 3.889 | 2.193, 2.895, 2.555 | 4.926 |

The renderer reused clocks and additive-noise draws across paired reference recordings. The fixed-estimator sensitivity permits each timing pair correlation anywhere from −1 to +1 while retaining survey terms. Each scalar extremum is calculated separately; they need not occur simultaneously. Under minimum scalar held variances, the largest held |z| is 0.230713 and largest held normalized RMS is 0.165118, so the sensitivity does not threaten these observed decisions. It does not cover arbitrary across-stop bias, nonlinear-model error or physical hardware. Two cases cannot establish confidence coverage.

## Exact evidence and reproduction

Freeze SHA-256: `1b59eb563ba72e29eebf1244a3eb59272e9d8c97f42eaa147d5bac5970e2b941`. The coordinator checked this exact protocol/runner/precheck/input freeze while no fit artifacts existed, then authorized the two fits. The runner and protocol were not changed after freezing. All 144 original WAV hashes match the original manifests and observation recording hashes. freeze.json records every raw/input hash plus the original V2 result/protocol/runtime hashes. Those hashes were verified before and after fitting.

Prefit checks compare analytic source/log-speed, receiver and reference Jacobians with centered finite differences (maximum discrepancy 4.78e-12). Direct and expanded held residual covariance agree below 2.49e-24; covariance positivity and nonzero shared terms are checked. Full fitted covariance components, H, K, residuals, selected candidate IDs, partitions and gate results are retained in results.json.

Environment: Python 3.12.14, NumPy 2.3.5, SciPy 1.18.1. No network, new recordings, generation, processing replay, runtime imports or production edits were used.

This small package requires the original local `work/source-calibration-mismatch/` tree, including the retained 144 V2 WAVs and full observations matching freeze.json. The prior compact evidence archive excludes those WAVs and signed-response arrays; it is not sufficient for this strict byte-verification runner by itself. No raw duplication or silent regeneration is provided. To reproduce in a clean experiment directory under `work/`, copy this protocol, runner and freeze there; preserve the original source-calibration-mismatch tree. Do not overwrite retained outputs. From the repository root:

```sh
.venv/bin/python work/<fresh-trial-directory>/run.py precheck
.venv/bin/python work/<fresh-trial-directory>/run.py run --approved-freeze 1b59eb563ba72e29eebf1244a3eb59272e9d8c97f42eaa147d5bac5970e2b941
```

`run` verifies frozen source and input bytes and refuses to replace an existing results.json. Numerical values can vary slightly across installations. Local trial fits took approximately 9.4 ms and 5.4 ms excluding I/O and integrity checks; these two measurements are not a performance benchmark.

## Decision and integration implication

The bounded branch passes: a second reference supplies enough information to remove the exposed valid single-source failure without weakening gates. Preserve this as development evidence. A production multi-reference interface, distributed-source qualification and room-mapping accuracy are not established or promoted. Any later integration needs a concrete benefit to the mapping path and evidence that its calibration assumptions hold; this result alone does not justify a new dataset search, broader feature scaffolding or a physical-accuracy claim.
