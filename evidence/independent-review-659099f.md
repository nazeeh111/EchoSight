# Independent calibration and inference checkpoint review

Reviewed commit: **`659099fed613f3ed26545b0a4631a05cbb97de74`**.
Comparison baseline: **`25c20f7162cedca449a2e3f226f61a50553d11af`**.

**The two prior storage P2 findings are repaired. Three new P2 findings remain in calibration and ambiguity composition. No P1 finding was established.** This is a bounded consequential review under the original charter and continued-work addendum. It is not full-backend acceptance or physical-device validation.

## Independence and scope

The reviewed commit was unpacked with `git archive` into `work/review-659099f-snapshot`. Every execution below imports from that immutable snapshot. I inspected the implementation diff from 25c20f7 and the assembled calibration, geometry, inference, signals, storage, pipeline and CLI interfaces, plus the relevant tests and documentation. I made no implementation, test, schema or documentation edits and no commits. Other agents' uncommitted multi-source and waveform work was excluded.

The review specifically examined reference calibration equations, reference-plane sensitivity, held-out prediction covariance, source/speed covariance replacement, calibration degeneracy/bounds, physical ordered reflections, coexistence of ambiguity types, source/receiver clock units and the two previously reproduced storage failures.

## P2: Reference calibration omits separate direct-reference and clock uncertainty

**Location:** `echosight/calibration.py:87–98`, propagated into fitting/validation at 103–117.

`noise(theta)` includes candidate `delay_std_s` and receiver pose uncertainty, but never reads observation `direct_std_s`, `clock.alpha_std`, or `clock.alpha`. The signal contract explicitly separates direct-reference error and relative-rate uncertainty from independent echo localization. The ordinary mapper correctly adds these terms, so the calibration helper currently uses a different, incomplete observation-noise model.

**Independent reproduction:** extract the existing raw calibration fixture through the real pipeline, then retain every measured delay and candidate while varying only those declared uncertainty fields. Setting direct uncertainty / relative-slope uncertainty to zero versus 80 microseconds / 100 ppm produces two `calibration_proposal` outputs with **bit-identical covariance** and identical held-out normalized RMS `0.0205603270`. Their reported source/speed marginal standard deviations remain `[0.0314184, 0.0131119, 0.0284981, 6.6060354]`. The probe uses controlled changes to extracted observations to isolate uncertainty propagation; it is not a claim that a hardware recording was replicated.

Artifacts: `work/review-659099f-science-probes.py` and `.json` (`timing_uncertainty`).

**Impact:** the returned source/speed covariance omits declared noise and the normalized training/held-out gates use underestimated observation variance. Changing a known direct/clock uncertainty cannot affect this proposal even though it must affect downstream geometry. A conservative reference-plane survey term does not repair missing capture-dependent timing terms.

**Repair:** include the selected echo's direct-reference variance and source-buffer clock contribution, using the same convention as inference: `direct_std_s² + delay_s²*(alpha_std/alpha)²` in addition to independent echo and receiver terms. Retain the shared reference-plane contribution and its held-out sensitivity. Verify both covariance response and held-out normalization; do not merely inflate a global output interval.

## P2: Four held-out IDs can collapse to one validation position

**Location:** `echosight/calibration.py:51–60`.

The partition check ensures unique capture IDs and checks validation positions only against training positions. It does not require the held-out positions to differ from each other. This contradicts the documented requirement for four spatially distinct held-out stops and weakens the source-model validation gate.

**Independent reproduction:** retain the real fixture's sixteen training recordings and one held-out recording/pose. Give that same new pose and WAV to all four held-out capture IDs. The helper returns `calibration_proposal`, no diagnostics and held-out RMS about **0.463 microseconds**, although there is only **one unique validation position**. There is no training-position overlap, so the current check accepts it.

Artifacts: `work/review-659099f-science-probes.py` and `.json` (`repeated_heldout`).

**Impact:** a repeated or accidentally duplicated acquisition can satisfy the advertised four-stop check without testing four spatial predictions. Unique IDs are not independent spatial evidence. This is a validation-contract implementation gap, separate from the broader physical limitations of a single surveyed reference.

**Repair:** enforce spatial distinctness within the held-out set, using a declared tolerance consistent with the training/validation overlap guard, and count actual independent validation positions. Keep repeated captures useful as repeatability evidence if desired, but do not count them as additional held-out spatial stops.

## P2: Higher-order ambiguity bypasses existing mirror and rank analysis

**Location:** `echosight/inference.py:446–464`, especially clearing `out['surfaces']` at 455 before iterating it at 464.

Once a two-bounce explanation is found, the implementation clears the definitive surface array. The subsequent receiver-plane mirror and local-rank checks therefore iterate an empty array. These ambiguity mechanisms are independent and can coexist; detecting one must not suppress the other.

**Independent before/after reproduction:** twelve receiver positions lie in one horizontal plane. Delays support two corner walls, a horizontal reflector and a coherent double-bounce path. The source and observations are identical in both immutable versions.

- **25c20f7:** returns `local_geometry_rank_deficient`, `support_coplanar_mirror_ambiguity`, explicit `primary` / `coplanar_mirror` / `rank_deficient_candidates` hypotheses, and receiver-height guidance.
- **659099f:** returns only `first_order_vs_higher_order_ambiguity` (plus the same search-budget diagnostic), the new reflection-order hypotheses and source-move guidance. The known mirror/rank diagnostics and explicit alternatives disappear.

The overall status remains `ambiguous`, so this is not a claim that the final definitive surface array falsely became unique. It is loss of a known ambiguity and its measurement guidance. In this example the opposite horizontal fit survives incidentally among generic unconfirmed candidate fits, which is not equivalent to retaining the proven paired mirror interpretation or rank analysis.

Artifacts: `work/review-659099f-mirror-probe.py`, `work/review-659099f-mirror-before.json`, `work/review-659099f-mirror-after.json`. The fuller resulting candidate structures are also in `work/review-659099f-science-probes.json`.

**Repair:** run all applicable ambiguity/rank checks on the retained fitted model before deciding what enters the definitive surface list. Preserve the different ambiguity families and guidance together. The fix should not imply that one proposed source move necessarily resolves an unrelated height ambiguity.

## Prior storage findings: independently verified repaired

I reran the original publication-write-failure and archive-replacement probes unchanged against this snapshot (`work/review-25c20f7-probes.py` with the new snapshot path). Results are in `work/review-659099f-storage-probes.json`:

- A final completed-state write failure leaves the prior completed result current, both before and after store restart.
- Replacing the archive pathname after parsing has started no longer changes recorded archive identity. The hash matches the original snapshot actually parsed, not the replacement archive.

I also adapted and reran the actual subprocess termination probe at the same pre-commit boundary. The child exits with code 17; reopening the store returns the prior completed result and its completed job. Artifacts: `work/review-659099f-crash-probe.py` and `.json`.

Code inspection confirms that the atomic completed job record is now the publication commit point; the store recovers its latest completed result from job records, and export follows the same selected job result. Archive parsing and hashing use the same bounded immutable byte buffer. These checks resolve the specific prior findings, not every possible filesystem or power-loss failure.

## Independent mathematical checks that passed

### Reference fit, survey sensitivity and held-out covariance

`work/review-659099f-math-probes.py` independently derives the source/log-speed Jacobian and the surveyed plane offset/tangent-normal Jacobian. With direct/clock uncertainty set to zero to isolate the implemented terms, it reconstructs the weighted training information matrix, shared survey sensitivity, transformed source/effective-speed covariance and held-out predictive variance.

- The returned covariance agrees within the asserted relative tolerance `2e-6` (maximum matrix-entry discrepancy about `5.1e-8` in the documented coordinate units).
- Independently refitting after small positive/negative shared reference perturbations agrees with the derived sensitivity to about `1.6e-7` maximum entry difference.
- The independent held-out normalized RMS is `0.6480160834335`; code reports `0.6480160834366`.

This supports the **existing** shared reference-error sensitivity and held-out formula, while leaving the omitted timing terms in the first finding unresolved. Held-out delays are not refitted. Bounds and spatial-degeneracy rejection tests passed; the separate held-out uniqueness gap remains as reported.

### Common source/effective-speed covariance replacement

`work/review-659099f-joint-probe.py` independently constructs six residuals across three physical planes and two receivers. It uses a correlated 4×4 source/effective-speed covariance, per-receiver shared direct/rate/pose terms and independent echo noise. The expected covariance agrees with `_covariance` to a maximum absolute entry difference of **1.04e-25**. Cross-surface/cross-receiver terms remain nonzero, and deliberately large old independent source/sound/clock uncertainty fields are not added a second time.

The supplied joint matrix is therefore used correctly for this conditional nuisance model. This does not establish empirical coverage under wrong associations, multiple emitters or reuse of correlated calibration data; independent calibration applicability and data dependencies remain substantive scientific assumptions.

### Physical timing and template retry

The independent waveform generator assigns different actual source and receiver clock scales, with `alpha=receiver_scale/source_scale`, and injects physical direct/reflected lengths before converting to nominal source time. All three cases exercise the new rate-refined acquisition template. Source scales 0.998, 1.002 and 1.001 produce recovered 5.8 m excess-path errors of approximately **−0.052 mm, −0.336 mm and +0.510 mm**. The inferred relative rate agrees with the injected ratio. Physical excess length is recovered using `c/source_scale`, not by treating alpha as the absolute source rate. These are narrow synthetic numerical checks, not clock performance on devices.

### Physical bounce validation and semantics

An independently checked perpendicular-corner example admits exactly one of the two reflection orders. Its reported vertices lie on the respective planes, obey the reflection law, and the summed segment length exactly matches the independently unfolded image range at numerical precision. The rejected reverse order is not accepted merely because algebraic images exist.

The new output explicitly labels surfaces as conditional first-order hypotheses and excludes reflection-order/multiple-emitter/transducer model error from local covariance. The higher-order guard preserves a genuine coincident reflector as an alternative and does not establish absence. Unknown finite extents/occlusion and missing-parent failures remain disclosed. The guard is not an exhaustive model search; the ambiguity-composition regression above remains material.

## Executed focused tests

**83 tests passed independently**, against the immutable snapshot:

| Group | Passed |
|---|---:|
| Calibration | 4 |
| Inference | 19 |
| Signals | 15 |
| Storage | 26 |
| Pipeline | 6 |
| HTTP/API end-to-end | 9 |
| CLI | 4 |

HTTP tests used native permission for temporary loopback listeners. These tests include positive calibration from quantized WAVs, rejection of changed held-out delays, degenerate/reused training positions, invalid joint covariance, original physical timing and higher-order cases, and storage/API replay behavior. They did not detect the three new findings; the independent probes did.

I did not rerun the full frozen/stress/FLAIR external evaluation in this review or inspect later uncommitted scientific changes. Source-reported external failures and current coverage gaps remain active. No numerical result here establishes measured room reconstruction or own-device accuracy.

## Disposition

Keep the repaired storage behavior. Resolve the three P2 findings with targeted regressions and review the resulting immutable commit. Reference calibration is a useful bounded proposal mechanism, but its current timing budget and held-out gate are incomplete. Higher-order interpretation is more honest than the baseline on its targeted case, but must coexist with other known ambiguities. No full-charter completion claim follows from this checkpoint.
