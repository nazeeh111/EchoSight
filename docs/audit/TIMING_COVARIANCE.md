# Joint timing covariance experiment

Status: isolated diagnostic, not a production confidence model. A naive inverse Hessian has been rejected. Whole-repetition bootstrap captures important shared uncertainty but seven repetitions do not establish nominal 95% coverage. No main signal or inference code changed in this experiment.

## Accounting convention

For each echo, `delta_j = (u_j - u_direct) / alpha`. Direct arrival, echo arrivals and relative clock rate are estimated from the same waveform. The derivatives are `+1/alpha`, `-1/alpha` and `-delta_j/alpha`; their cross-covariances need not vanish. An empirical direct kernel is another estimated nuisance quantity shared by all paths. Independent amplitude fits do not make these timing errors independent.

The proposed `candidate_delay_covariance` block has explicit ordered `candidate_ids`, a matrix in source-buffer seconds squared, and flags declaring that direct reference, empirical kernel, relative rate and amplitude nuisance are included. It excludes acoustic-center poses, physical sound speed, absolute source-clock scale, independently surveyed reference-plane uncertainty and model bias. Geometry consumers must map candidate IDs into this matrix, use its complete timing submatrix, and **skip** the old individual delay variances, `direct_std_s` term and `alpha_std` rank-one term. They still add pose/source/effective-speed covariance. Calibration selects one reference echo per independent recording, so it uses the corresponding diagonal exactly once.

The isolated consumers verify this accounting numerically, including reversed matrix ordering. Legacy calibration variance is `sigma_echo² + sigma_direct² + (delta * sigma_alpha / alpha)²`. Symmetry and positive-semidefiniteness checks use covariance-scale-relative tolerances, not a fixed tolerance that would accidentally admit negative eigenvalues at small time units. Candidate ID mismatch, duplicate IDs, unsupported component flags, nonfinite matrices and incorrect dimensions fail validation. Cancellation and unstable path assignment return no covariance. These tests plus signal/joint-estimator tests pass: **24 tests**.

## Estimator and limits

The diagnostic resamples entire pulse-and-echo repetition blocks in the original recording. Every draw reruns relative-clock fitting, direct-reference selection, empirical-kernel estimation, amplitudes and joint delays. This retains within-block colored noise and inter-path covariance rather than pretending the matched-filter samples are independent. Candidate association is frozen around the original estimated delays; fewer than 90% stable draws gives an explicit unstable result. Draw count is bounded to 15–63; the study uses 31.

Matched filtering itself creates colored noise: for white input noise, response covariance is proportional to the emitted pulse autocorrelation. A Hessian computed with independent response samples and a fixed independently known kernel is therefore not the covariance of this estimator. Additionally, the actual estimator has fractional interpolation, finite optimization tolerance and path-selection nonlinearities. The experiments below do not identify colored noise as the sole source of Hessian failure.

The bootstrap output separates estimated noise covariance from optional declared resolution floors: `C = C_bootstrap + floor² (I + 11ᵀ)`, with `floor = max(0.5 / source_rate, 0.5 / bandwidth)`. The first floor term is independent per echo; the second is the shared direct-reference floor. This preserves the existing conservative timing allowance without counting it twice. **Those floors are heuristics, not a calibrated probability distribution for transducer, diffraction or propagation-model bias.** The block is labeled `coverage_status: development_unqualified`.

Missing dependence remains explicit: simultaneous phones may share source jitter/noise, but independent per-recording bootstraps do not estimate cross-capture covariance. Repeated fixed waveform bias is invisible to resampling. Seven repetitions provide little information about tail probability. Subsample block transfer also interpolates samples. These limitations prevent calling the result full physical uncertainty even though its within-capture component accounting is complete.

## Executed evidence

Forty independent generated recordings per family, each with seven repetitions and 31 bootstrap draws, compare predicted component intervals with injected delays and the empirical mean. The latter separates repeatability from deterministic bias. All 200 recordings yielded estimates in these controls; this is not a measured-device coverage study.

| Family | Bootstrap centered coverage, two paths | Naive Hessian centered coverage | Bootstrap coverage against true delay |
|---|---:|---:|---:|
| White noise, integer-aligned isolated paths | 97.5% / 92.5% | 100% / 100% | 97.5% / 87.5% |
| Colored noise, fractional overlapping paths | 77.5% / 82.5% | 0% / 0% | 77.5% / 57.5% |
| White noise, fractional overlap and repeated timing jitter | 95% / 92.5% | 15% / 5% | 95% / 90% |
| White noise, fractional overlapping paths | 80% / 90% | 0% / 0% | 80% / 60% |
| Colored noise, integer-aligned isolated paths | 95% / 95% | 92.5% / 100% | 95% / 97.5% |

The colored/fractional case's empirical timing variance is approximately `1e-11 s²`; the naive Hessian predicts only `4–6e-14 s²`. The bootstrap captures the variance scale and substantial off-diagonal dependence, but its plug-in normal intervals still under-cover. The white/fractional ablation also fails, while colored/integer behavior is much better: it would be incorrect to attribute the failure solely to colored noise. Declared floors cover all tested true delays, but this does not validate those floors under wrong physical models.

Full cases: [main Monte Carlo](../../evidence/audit-physics/covariance-development.json) and [alignment/noise ablation](../../evidence/audit-physics/covariance-ablation.json). Exact diagnostic code and tests: [covariance experiment](../../evidence/audit-physics/covariance-experiment/). The scripts run in the isolated `work/physics-joint-trial` snapshot alongside the earlier joint-fit modules. No thresholds were adjusted to obtain these coverage figures. The inverse-Hessian branch is closed; bootstrap remains a labeled diagnostic pending enough independent repeats, improved estimator stability and separate model-bias evidence.
