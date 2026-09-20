# Frozen calibration-to-room transfer: independent actual-result review

**Runtime:** `5d6423486be5fd448a4d7b42fbbaee264eb07c9c`  
**Freeze SHA256:** `a995d28014c4c055003d34db193f5657a08d185a281d09ff1d7e667e5405da40`

**Decision:** preserve the actual failed transfer/promotion outcome. The joint mapper reconstructed six matched planes with no unmatched planes in both instances, but only 19/24 held predictions were uniquely validated. A separate post-hoc oracle reveals that the frozen exact-one-candidate gate rejects even exact truth at the selected held positions. Detector screening explains additional missing candidate structure, but detector-only repair cannot make the exact oracle satisfy this gate.

No renderer, raw signal pipeline, mapper or calibration fitter was rerun. No production or frozen artifact was changed. All new writes are in this review directory.

## Consequential finding: the gate rejects perfect truth

**P2 evaluation-design limitation.** With exact true planes, source, effective speed, receiver positions and a complete catalog containing all six exact physical echo arrivals, the frozen ±200 µs/exactly-one rule validates **20/24**, in both seeds:

| Held capture | True pair | Separation | Oracle consequence |
| --- | --- | ---: | --- |
| capture-14 | wall-1-0 / wall-1-1 | 173.021453 µs | Each prediction sees two peaks; both fail |
| capture-15 | wall-0-0 / wall-1-1 | 196.986783 µs | Each prediction sees two peaks; both fail |

This is not simply overlap of the window intervals: each true candidate is within 200 µs of **both** exact predictions. The candidates are individually distinct, but the gate forbids choosing a unique association. The cap12 floor/ceiling pair is 226.570051 µs apart and does not have this ideal-gate failure.

`oracle_feasibility.py` independently checked all 24 paths from saved true walls and poses against the saved physical path arrivals. Their exact predictions agree within 1e-14 s. The four listed failures remain explicit. As sensitivity diagnostics, true planes with the saved joint calibration and actual positions also yield 20/24 in both seeds. Using the surveyed positions yields 20/24 for 2821 and 21/24 for 2833 because one window edge moves. These are diagnostic variants, never replacements for actual results.

This establishes that the gate is unsuitable as a necessary condition for exact reconstruction at these selected positions. It does **not** prove that no biased output could ever pass: small prediction shifts can move a neighboring candidate across a window edge. Do not tune errors, poses or thresholds to exploit that boundary. Do not revise or rescue the frozen result. Any future experiment would need separately approved, prospectively checked acceptance geometry; this review does not authorize one.

## Actual five failed validations per seed

The saved candidate catalogs contain 20 peaks across the four held captures. The actual scorer reports only 19 unique validations because a retained cap14 candidate is eligible for two surfaces and both rows correctly become nonunique. The five failures are three missing rows plus two reused-candidate rows, not five rejected recordings.

`diagnose_saved.py` inspects the retained signed median response arrays and reproduces only their peak-screen conditions. It invokes no importer, raw extractor or mapper.

| Actual failure | Saved-response evidence | Consequence |
| --- | --- | --- |
| cap12 ceiling, both seeds | Separate local maximum passes height/prominence; height 2.605/2.639 times cutoff, but a retained neighbor is 229.2 µs away | Removed by the 17-sample spacing rule |
| cap12 far x-wall, both seeds | Local maximum is 0.991/0.962 times the relative-height threshold | Just below the fixed 7%-of-maximum rule |
| cap14 two y-wall validations | Two strong local maxima, separated 166.7/187.5 µs in sampled peak centers; one is discarded | The remaining candidate serves both predictions, so both validations fail |
| cap15 far y-wall, both seeds | Separate local maximum, 4.779/4.795 times cutoff, with retained neighbor 187.5 µs away | Removed by spacing; the remaining neighboring peak cannot establish this path |

At 48 kHz the declared 350 µs minimum becomes 17 samples, or 354.166667 µs, through rounding. The retained member of the cap14 pair changes across seeds: near y-wall in 2821, far y-wall in 2833. Both local maxima exceed the height and prominence screens. The absolute threshold is governed by relative peak height, not the repeat-noise term, in all inspected failures.

These are limitations of the current conservative detector policy on visible response structure. They are not evidence of a fundamental absence of acoustic information or an implementation exception. Local maxima alone do not validate independent physical echoes: sidelobes/interference are visible too, and the saved median cannot reconstruct per-repeat admission. Removing a screen is not established as a safe improvement; known clutter/null regressions from prior approaches remain relevant. Crucially, even perfect recovery of these missing peaks leaves the oracle gate problem above.

The evaluation specialist independently matched physical delays and found the joint predicted-minus-physical error on the ten failed rows to be only −36.216 to +31.685 µs. That separate result is consistent with the saved-response diagnosis and does not convert any failed validation to a pass.

## Calibration mathematics and interpretation

The original saved joint source coordinates, effective speed and every element of the full 4×4 source/speed covariance are copied unchanged into the two joint mapping acquisition snapshots. Their covariance matrices remain positive definite; source-x/speed correlations are about 0.931 and source-y/speed correlations about 0.901. The frozen inference implementation explicitly adds `J Σ Jᵀ` using that full matrix. Cross terms were not discarded, and independent speed/source priors were not added on top.

This is covariance conditional on the supplied point-source/first-order model and path assignments. It does not represent missing-peak, alternative-association or detector-model uncertainty. Inflating that covariance would neither restore removed candidates nor alter the frozen absolute acceptance windows.

Source continuity is the declared synthetic V2 point-source/FIR/effective-speed identity, verified separately by the acquisition/integration lanes. It is not authenticated physical hardware/route continuity. The effective speed remains metres per source-buffer second; the trial does not identify physical sound speed separately from source-clock scale. Independence of mapping survey/noise and calibration errors is a construction assumption, not a guarantee for a shared physical survey frame.

The two held extraction artifacts correctly remain cancelled, retain four observations each and contain no fitted surfaces. Their observations support prediction checks; the cancelled artifacts are not completed maps.

## What can and cannot be claimed

Recorded joint six-plane mean anchored errors are 2.528 mm and 2.324 mm, compared with nominal 10.777/15.700 mm and preselected x-reference 6.667/23.913 mm. These describe improved geometric point estimates in two exposed synthetic cases. They do not satisfy the complete frozen gain criterion. The reported held RMS values use only unique subsets; do not describe them as 24-path RMS or compare unequal subsets as qualifying gains.

All 20 jobs accepted their 12 mapping observations, direct-only controls produced no definitive planes, and joint mapper recall exceeded first-echo recall. Those findings establish the recorded admission/control and geometry behavior, not withheld closure, physical room completeness or general calibration transfer. Support hulls remain reflection-support geometry rather than physical room edges.

The promotion attempt remains closed with `transfer_pass=false` and `promotion_criteria_pass=false`. The oracle limitation means the failed gate cannot, by itself, establish that joint calibration lacks physical utility. Conversely, descriptive geometric improvements cannot overrule the frozen failure or justify promoting a public calibration feature.

## Executable evidence and binding

- `diagnose_saved.py`, `diagnostic.json`, `run.log`: saved-response screen analysis, original-fit covariance equality, cancelled-held boundary and exact input SHA256 values.
- `oracle_feasibility.py`, `oracle-feasibility.json`, `oracle-run.log`: all-24-path post-hoc ideal feasibility and declared calibration/pose variants, with input hashes.
- Both scripts run with the existing review Python environment from repository root. Neither invokes acquisition processing or inverse reconstruction.

The aggregate scorer was independently recomputed by the evaluation lane; raw hashes/source continuity and runtime applicability have separate assigned audits. This review does not duplicate those audits or claim a full-suite run. No new production defect was demonstrated by the saved peak screening; the consequential new finding is the ideal-truth rejection in the frozen evaluation design.
