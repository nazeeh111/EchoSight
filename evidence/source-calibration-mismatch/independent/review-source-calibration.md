# Independent scientific review: source-calibration mismatch

The completed evidence justifies one bounded, development-only joint-reference fit on the **existing** recordings. It does not establish joint-calibration accuracy or source qualification. I found no P1/P2 error in the preserved V1/V2 conclusions or the conditional local information calculation. The original single-source transfer failure remains a real limitation, not a distributed-source detection success.

## Exact scope and integrity

Reviewed the two frozen protocols, `run.py`, `run_v2.py`, `joint_information.py`, preserved session/reference/observation/calibration outputs, transfer calculations, V1/V2 reports, and pinned `echosight/calibration.py`/its processing path at commit `3745665352f59bc88e432b1f703054ab29398ce1`. No live runtime code or parallel repair was reviewed or changed.

Archive SHA-256 is `2da45a689274cd1375e074c2da81edbd8e09d814ac6a803af98e10a03eb4aa1d`. I independently verified all 166 payload hashes, exact member coverage, and the aggregate content hash. The archive has 167 members including its manifest. All archived observations equal their retained full originals after the explicitly declared transformation: removing each signed response array and retaining its independently verified JSON-content hash. All other observation/calibration fields remain identical. All 288 retained raw WAV hashes match their manifests. WAVs are not included in the compact archive.

Both freeze manifests match the protocols/runners and every pinned runtime Python file; runtime bytes also match the stated Git commit. V1's preserved snapshot still contains byte-identical protocol, runner, freeze, results and summary. V2 changes the arrangement and seeds in a separately frozen experiment; it does not retroactively discard the failed V1 controls or alter its detector/calibration gates. This checks internal preservation and executable freeze checks, not an independent external timestamp attestation.

Exact diagnostic source SHA-256: `c85ba2dc494de93cdda86d405f9aa364a1e783f62d8d4c5dc231236579dd63dd`. V1 freeze hash is `24c2bdf8804000e8e0158030f29919d8306776f8438f8361ee185ebed7be179c`; V2 is `91df03d959f036f5bcad7671f04090d22633b56001d7fdb51c83be281d5b101a`.

## Preserved outcomes and equal-input checks

V1 has 12 rejections, including every single-emitter control. V2 has six proposals and six rejections: all four single-emitter controls and both opposite-phase x-reference cases propose calibration. The opposite-phase y-reference cases retain two eligible candidates at all 12 stops, so transfer is ambiguous; the evaluator selects neither path. In-phase cases remain rejected. These outcomes are conditional on this isolated-reference renderer and the fixed 24 cm coherent two-emitter surrogate, not measured hardware.

I independently replayed three existing V2 raw cases through the pinned unmodified calibration: `single-2833-x`, `dual_opposite_phase-2821-x`, and `dual_opposite_phase-2821-y`. Status, diagnostics and input-result identity reproduced exactly. Proposed source, speed, covariance and training/held metrics reproduced to the stated numerical checks in the probe. No observation was substituted and no new raw family was generated.

The 8/4 training/held capture partitions remain fixed in every case. Each x/y pair uses identical supplied receiver positions and uncertainty. The renderer applies the same fixed source centers, gains, filters and probe to the two reference arrangements; calibration receives source priors and surveyed reference geometry, not generating source truth or echo labels. Truth is read only by external evaluation. The frozen candidate window and exactly-one eligible candidate rule agree with the pinned implementation.

Freshly applying the replayed seed 2833 x proposal to its stored y observations independently reproduces the valid-control transfer failure, with every residual retained. Recomputing all unique transfer residual metrics preserves the single-source contrast: seed 2821 has 50.895 µs RMS / 71.613 µs maximum and passes the frozen absolute gates; seed 2833 has 229.479 / 282.680 µs and fails. A reject-only transfer rule therefore fails a valid single-source control. The large one-reference parameter uncertainty explains why low same-reference residuals do not imply an accurate transferable source position.

## Independent mathematics

For a unit reference normal n, offset d, reflection M = I − 2nnᵀ, image q = Ms + 2dn, and delay f = (|q−r|−|s−r|)/v, let u_q = (q−r)/|q−r| and u_s = (s−r)/|s−r|. I independently implemented the analytic derivatives:

- source: (M u_q − u_s)/v;
- receiver: (u_s − u_q)/v;
- speed: −f/v;
- plane offset: 2(u_q·n)/v;
- a unit tangent rotation direction a: 2 u_q·[−(a·s)n + (d−n·s)a]/v.

They agree with fresh finite differences at the supplied nominal point for both seeds: maximum errors below 1.3×10⁻¹², including every receiver coordinate and all six reference nuisance coordinates. The speed variable is effective propagation speed per source-buffer second, consistent with the original clock convention. No physical sound-speed/source-clock separation is inferred.

I assembled observation covariance independently as timing diagonal + D C_receiver Dᵀ + G C_reference Gᵀ. A receiver's three-position error is reused across both reference arrangements, rather than duplicated as independent. Each reference's offset/rotation error is shared across its captures; the two reference surveys are explicitly assumed independent. No source prior is manufactured from the bounded search radius. Receiver cross-reference covariance and reference off-diagonal covariance are nonzero and retained.

Cholesky whitening followed by an SVD inversion reproduces the published information covariance. A separate calculation introducing all 42 survey nuisance parameters and eliminating them by a Schur complement agrees to below 6×10⁻¹⁵ relative covariance error. This verifies that the improvement is not caused by averaging two correlated fitted source estimates or by double-counting independent receiver priors. Adding the reference reduces the parameter covariance by a positive-semidefinite amount in both cases.

At this nominal point, joint source-axis standard deviations are approximately 1.65/2.51/1.84 cm with effective-speed SD 3.85 m/s. Separation-axis uncertainty from x-only is 21.6–21.7 cm and from y-only 23.5–23.7 cm. The reduction is substantial actual local geometric information under the stated point-source/error model. A 40,000-draw linear Gaussian check per seed reproduces the conditional covariance within 1% matrix-relative error. This checks linear algebra only; it is not nonlinear calibration accuracy or empirical coverage of raw timing errors.

## Consequential limit: paired random draws and held residual covariance

The renderer resets its random generator to the same seed for each reference arrangement. I verified that paired x/y records have exactly the same generating alpha and offset, and source inspection shows the same additive-noise draws are also reused. This is a legitimate paired simulation design, but the reports' references to independent clocks/noise should be qualified: independence applies across receiver stops, not to paired reference recordings. The prospective information calculation assumes diagonal timing covariance. It has not estimated cross-reference timing-error correlation from these two seeds.

This does not erase the information result. Keeping the nominal GLS estimator fixed, I propagated possible timing correlation between each reused x/y pair with a sandwich covariance, rather than refitting optimal weights for the assumed correlation. Taking each scalar parameter's worst variance over arbitrary pair correlations from −1 to +1 increases joint separation-axis SD only to approximately 2.952 cm, and speed SD to 4.87 m/s. Receiver/reference terms remain unchanged. This bounded sensitivity is restricted to pairwise timing correlation with the stated marginal variances; it does not cover systematic source-model error, arbitrary across-stop timing bias or physical hardware.

A future held residual check must also retain training/held covariance from each common reference survey. If K maps training residuals to fitted parameter error, the held residual covariance is

`C_hh + H_h K C_tt Kᵀ H_hᵀ − C_ht Kᵀ H_hᵀ − H_h K C_th`.

Simply adding held variance to fitted parameter covariance would ignore those shared terms. The present information diagnostic correctly labels its held prediction numbers as **parameter-only**; they cannot substitute for the complete held residual variance. The current one-reference implementation already accounts for its corresponding shared-reference sensitivity. This is a concrete requirement for the proposed joint experiment, not a defect in an unimplemented feature.

## Smallest justified next experiment

Freeze one joint source/effective-speed estimator and its covariance/validation rules before execution. Use the already generated V2 x/y pairs, unchanged nominal initialization, 15 cm source radius, 300–380 speed bounds, supplied surveys, timing data and capture partition. Fit only the 16 declared training observations and evaluate both original four-stop held sets without refitting, exclusions or path selection. Preserve each reference's existing normalized/absolute acceptance gates and the failed one-plane transfer separately. Retain complete shared receiver/reference covariance and distinguish uncertainty at the actual fitted point from this nominal-point information prediction.

Only two joint point-source fits are necessary, one per existing single-source seed. Run the same admission boundary on all existing dual pairs: their ambiguous/missing reference candidates remain rejections before fitting. There is no justification for a new raw family, new placement/phase/seed search, relaxed gate, oracle echo selection or production feature at this stage. If either valid single-source joint control still fails its frozen held gates, stop this development branch and report that failure. Even a pass would establish only bounded development behavior; it would not qualify a distributed physical source or establish calibrated confidence coverage from two seeds.

## Artifacts and limits

`work/review-source-calibration.py`, `.json`, and `.log` retain the archive/freeze/raw integrity checks, fresh Jacobians, independently assembled covariance, nuisance elimination, linear Gaussian check and fixed-estimator timing sensitivity. `work/review-source-calibration-replay.py`, `.json`, and `.log` retain the three actual raw replays. Exact copies and reproduction instructions are archived under `evidence/source-calibration-mismatch/independent/`.

No full suite, new raw experiment, joint nonlinear fit, hardware test, uncertainty-coverage experiment, production feature or runtime edit was performed. Conclusions distinguish verified computation from the prospective experiment it motivates.
