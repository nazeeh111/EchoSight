# Independent transfer evaluation audit

The frozen promotion attempt fails. Independent scoring reproduces every anchored geometry row, held-path classification/residual, admission result, timing comparison, benefit comparison and final decision from all 20 saved fits. No mapper, calibration fitter, renderer or frozen scoring function is imported or rerun. All 20 outputs were present and loaded before this audit read evaluation truth.

## Results

| Seed | Method | Matched / false | Unique held / 24 | Six-wall mean anchor error (mm) | Recorded processing (s) |
|---|---|---:|---:|---:|---:|
| 2821 | nominal_mapper | 6 / 0 | 17 | 10.777 | 0.919 |
| 2821 | one_x_mapper | 6 / 0 | 19 | 6.667 | 0.881 |
| 2821 | joint_mapper | 6 / 0 | 19 | 2.528 | 0.878 |
| 2821 | joint_grid | 6 / 0 | 19 | 2.528 | 0.903 |
| 2821 | joint_first_echo | 0 / 0 | 0 | unavailable | 0.896 |
| 2833 | nominal_mapper | 6 / 0 | 19 | 15.700 | 0.876 |
| 2833 | one_x_mapper | 6 / 0 | 17 | 23.913 | 0.939 |
| 2833 | joint_mapper | 6 / 0 | 19 | 2.324 | 0.877 |
| 2833 | joint_grid | 6 / 0 | 19 | 2.324 | 0.911 |
| 2833 | joint_first_echo | 0 / 0 | 0 | unavailable | 0.911 |

Both joint maps contain six one-to-one matched planes, including floor and ceiling, and no unmatched planes. All 20 mapping/control fits accept all 12 recordings; all ten direct-only outputs contain zero surfaces. All ten room held extractions are explicitly cancelled after extraction, have exactly four accepted observations, no inferred surfaces, and capture IDs disjoint from map inputs. All methods use byte-identical extracted observations within each seed/family. Joint versus first-echo aggregate matched count is 12 versus 0. This does not overcome either joint held-path failure. Both nominal and preselected x-reference also recover all six walls; lower joint anchor error is descriptive, not the frozen required complete-transfer benefit.

## Exact failure taxonomy

Every joint seed has three zero-candidate predictions and two predictions sharing one candidate. Every held observation is accepted. No catalog candidate is marked merged; merged-flag exclusion is not the cause. All ten failed predictions differ from their independently computed physical path delays by at most 36.217 microseconds. This bounds these post-fit geometry/calibration prediction errors; it does not validate missing echoes.

| Held capture | True surface | Frozen outcome per seed | Post-fit physical diagnosis |
|---|---|---|---|
| 12 | ceiling (wall-2-1) | zero candidates | True excess delay 7106.511 us; nearest retained floor candidate is about 228 us earlier, outside the fixed window. |
| 12 | far x wall (wall-0-1) | zero candidates | True excess delay 21807.025 us; nearest retained candidate is about 3576 us earlier. |
| 14 | near and far y walls | candidate reuse, both invalid | True delays 8506.354 and 8333.332 us, separated by 173.021 us. Only one retained candidate lies in both prediction windows. The selected peak is near-wall-like for 2821 and far-wall-like for 2833. |
| 15 | far y wall (wall-1-1) | zero candidates | True delay 8005.447 us; nearest retained peak is the distinct near-x path around 7809 us. A truth-based shift might include it but would share the near-x candidate and still fail exclusivity. |

The detailed post-fit truth/candidate catalogs are in held-failure-diagnostics.json. These diagnostics never replace the frozen predictions or rescue a gate. Saved-envelope mechanisms are independently investigated by the material-review lane; this audit itself only diagnoses the saved catalog and path geometry.

## Scorer finding

The frozen scorer correctly makes transfer=false, both per-seed benefits=false, and promotion=false. No decision-changing scoring defect was found for these artifacts. However, results.json reports withheld.rms_s and max_abs_s over only the unique subset even when complete=false. That is a reporting mismatch with the protocol statement that incomplete comparators have unavailable complete-error statistics. Neither field can be quoted as 24-path prediction accuracy. The unchanged frozen results are retained; audit.json explicitly separates complete_rms_s/complete_max_abs_s=null from unique_only_rms_s/unique_only_max_abs_s and the unique denominator. Per-surface frozen RMS fields have the same subset limitation. No arithmetic/gate change or threshold relaxation is warranted.

## Integrity and scope

The approved freeze a995d28014c4c055003d34db193f5657a08d185a281d09ff1d7e667e5405da40 and all 94 bound inputs match. Four render manifests and all 56 new WAVs match their saved hashes. All original study files have identical before/after hashes. Saved nominal/x/joint calibration fields, including full joint source-speed covariance, match their fixed inputs; receiver surveys and recording hashes match their raw session declarations. No input was mutated.

Timing is the original recorded worker duration, not independently remeasured. The verifier checks finite positive values and the frozen 10-second limit; first-echo retains its longer scope (raw joint pipeline plus additional comparator inference). Historical origin-offset scoring is retained in the original results but is not needed to adjudicate the anchored gate and was not independently recomputed here.

This remains a two-instance selected development experiment using previously exposed successful synthetic calibration fits, an exact frame, independent synthetic surveys/audio, first-order point-source reflections and fixed geometry. It is neither independent generalization nor hardware qualification. The required transfer/benefit gate has failed, so these observations do not justify promoting a public multi-reference feature.

## Reproduce the independent audit

From the main repository:

```sh
.venv/bin/python work/transfer-evaluation-review/verify.py
```

This reads the preserved full artifact tree at work/frozen-transfer-runtime/work/calibration-room-transfer and writes only work/transfer-evaluation-review. Portable compact-artifact replay is owned by the integration lane; that reproduction is distinct from this independent scorer.

## Post-fit gate-design caveat

Separately from the actual frozen failure, the exact physical paths at capture 14 are only 173.021453 microseconds apart and the near-x/far-y pair at capture 15 is 196.986783 microseconds apart. Both are less than the fixed 200-microsecond candidate-window radius. With true geometry and a complete exact-peak catalog, each member of either pair would have two eligible candidates. Consequently the frozen exactly-one-local-candidate rule cannot accept that ideal oracle at these held positions. This is an acceptance-design identifiability limitation, distinct from the actual extractor's missing/suppressed peaks. The counterfactual follows directly from stored physical path delays; no new fit or extraction was performed.

The observed experiment still fails its locked criteria and does not meet the prescribed promotion decision. However, that failure alone cannot establish that the calibration or room geometry is inadequate, or that multi-reference calibration has no value: part of the criterion is structurally unsatisfiable for ideal predictions and ideal peaks at the selected held positions. Any future protocol would need a prospectively declared, independently reviewed treatment of overlapping windows or globally exclusive assignments, followed by fresh data; these exposed cases cannot be rescored to qualify the current attempt or justify production changes.
