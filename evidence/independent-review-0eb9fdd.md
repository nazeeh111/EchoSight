# Independent bounded follow-up: 0eb9fdd

Inspected immutable commit **0eb9fdd55a0703ec003eb62f87e04fb4213d8646**, compared with **659099fed613f3ed26545b0a4631a05cbb97de74**. Snapshot created with `git archive` at `work/review-0eb9fdd-snapshot`; all snapshot `echosight/*.py` bytes were checked against the commit after execution. No implementation changes or Git writes were made.

**No residual P1/P2 was established within this follow-up.** The three findings in `review-659099f.md` no longer reproduce. The evolution changes address the origin and effective-speed cases tested below. This is closure of specific findings, not acceptance of the complete scientific pipeline, measured uncertainty coverage, or hardware performance.

## Scope and code inspected

Read the immutable diff and assembled `echosight/calibration.py`, `echosight/evolution.py`, and the affected ambiguity/model-output section of `echosight/inference.py` (approximately lines 400–520), together with `tests/test_calibration.py`, `tests/test_evolution.py`, `tests/test_inference.py` changes and `docs/CALIBRATION.md`. Requirements remain the original charter and continued-work addendum used in the prior review. No uncommitted controlled, multisource, or physical experiment work was inspected.

## Prior P2 findings

1. **Separate timing uncertainty in reference calibration: closed for the reported defect.** Lines 94–109 now combine candidate timing variance, direct-reference timing variance, and relative-rate variance as `candidate_std² + direct_std² + (delay * alpha_std / alpha)²`, before receiver survey variance. Reran the original discriminating raw-fixture probe: changing only `direct_std_s` from zero to 80 microseconds and `alpha_std` from zero to 100 ppm now changes the covariance. Source coordinate standard deviations change from `[0.0314184, 0.0131119, 0.0284981]` m to `[0.0692584, 0.0294790, 0.0648785]` m; effective-speed standard deviation changes from `6.60604` to `14.08792` m/s. Held-out normalized RMS changes from `0.0205603` to `0.00899707`.

   Also adapted the earlier independent analytic calculation to non-unit `alpha=1.02`, `alpha_std=0.001`, direct timing standard deviation 80 microseconds, and candidate-local standard deviation 40 microseconds. Derived source/log-speed and reference-plane Jacobians independently, including receiver survey noise, shared reference sensitivity, parameter transformation, and held-out prediction variance. Covariance matches at `rtol=2e-6, atol=1e-9` (maximum absolute matrix-entry difference `2.41055e-7`, with mixed source/speed units). Analytic versus code held-out normalized RMS is `0.2946461923150924` versus `0.29464619231524036`. Refitting perturbed reference planes agrees with analytic sensitivity at the probe's declared tolerance. This checks the local covariance formula, not empirical coverage or independence when calibration recordings are reused downstream.

2. **Repeated held-out positions counted as spatial validation: closed for the reported defect.** Lines 59–62 check all pairwise positions, including within validation, within training, and across partitions. The original four-held-out-IDs-at-one-location probe now raises `ValueError`. Separate 0.9 mm near-duplicate cases in each of those three categories also reject.

   The additional raw-recording guard at lines 89–92 was exercised through actual processing, not solely patched observation hashes: copied one held-out WAV to another pathname, kept the replacement position distinct by 2 mm, and reran calibration. It rejects with `reference_recordings_reused`. A distinct pathname therefore does not establish recording independence. Byte-hash distinctness is a duplicate check, not proof of physical independence or valid acquisition.

3. **Higher-order ambiguity skipped mirror/rank checks: closed for the reported defect.** Lines 455–457 defer clearing definitive surfaces; lines 494–495 clear them after mirror/rank analysis. Reran the unchanged original `review-659099f-mirror-probe.py` against this snapshot. The combined coplanar-receiver/corner/ceiling/double-bounce scene now retains all three diagnostics: `first_order_vs_higher_order_ambiguity`, `local_geometry_rank_deficient`, and `support_coplanar_mirror_ambiguity`. It retains both `coplanar_mirror` and `rank_deficient_candidates` alongside the first-order and fewer-surfaces interpretations, and both source-movement and receiver-height guidance. The result remains ambiguous. The focused regression also checks that no definitive surface array is published. These are preserved ambiguity families, not a complete enumeration of every joint scene interpretation.

## Evolution changes

- Independently reproduced the preceding version's behavior: translating a two-degree plane-fit pair and the source together by 100 m changes one correspondence to zero, although the physical scene is unchanged. It also labels results with effective speeds 343 and 346 m/s comparable. Saved in `review-0eb9fdd-evolution-before.json`.
- Current lines 80–85 compare signed plane offsets at the common source reference. Thirty independent rigid-coordinate transformations, including rotations, translations up to 100 m, and alternate normal/offset sign reversals, preserve correspondence and angle; maximum signed offset discrepancy is `1.86517e-14` m. The new field names make clear that this is a reference-local plane offset difference, not a global separation between nonparallel planes.
- Current calibration compatibility guard preserves comparability when both legacy results omit effective speed, accepts equal explicit effective speed, and returns incomparable for different speeds or a speed present on only one result.
- Missing required calibration fields return incomparable; malformed source vectors (null, wrong length, NaN, boolean coordinate, mapping) raise `ValueError`.

## Executed checks

Using the existing backend `.venv/bin/python`, running from the immutable snapshot:

| Test module | Passed |
| --- | ---: |
| `test_calibration.py` | 6 |
| `test_evolution.py` | 9 |
| `test_inference.py` | 20 |
| **Total** | **35** |

Independent probe artifacts:

- `work/review-0eb9fdd-probes.py` and `.json`: original uncertainty and duplicate-position probes, actual duplicated WAV, near-duplicate positions, original combined-ambiguity script, coordinate transformations and calibration compatibility.
- `work/review-0eb9fdd-formula-probe.py` and `.json`: independent reference sensitivity/covariance/held-out variance with all timing terms active and non-unit alpha.
- `work/review-0eb9fdd-evolution-before.json`: preceding-commit reproduction.

No broad suite, storage crash/archive rerun, external dataset evaluation, hardware test, or full backend re-review was performed; those are outside this bounded follow-up. The report does not assert that undeclared scientific assumptions, incomplete search, cross-stage data dependence, or active capability gaps have been resolved.
