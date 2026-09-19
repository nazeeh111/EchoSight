# Independent review: source-model v4

**The two specific v3 review defects are addressed within the bounded development prototype. Do not promote it to mapping or physical source qualification.** The exact gain objective is corrected, and the new clock experiment transforms raw recordings before the complete extractor rather than relabeling stored response axes. Its reported warning benefit still discards24 true surfaces. The accepted clock-lobe bias remains a separate consequential correctness limitation; it is not resolved by passing the warning gates.

Reviewed only frozen snapshot `work/source-model-diagnostic/review-snapshot-v4-587df5457015/`, content ID `587df54570155117f92df5a970e47e335a371ecaef31cc16d38f2e6a95108187`. All30 manifest entries were hash-verified. The separate live clock investigation was not inspected. No prototype/main edits, new raw case generation or classifier fits occurred in this review.

Independent checks are in `work/review-source-model-v4/check.py` and `checks.json`.

## Findings and verification

1. **Bounded-gain correction verified.** `gain_v4.py` evaluates feasible interior coefficients, all four box-edge optima and feasible single-column fallbacks, using the actual residual to choose. Its single-column ordering keeps secondary gain zero when that path's column is absent. Both `diagnostic_v4.profiles` and `waveform_v4.residual_profiles` use this helper, removing the prior inconsistent clipping objective. An independent84-case comparison against SciPy BVLS covered ordinary, correlated, anti-correlated, identical, zero-primary, zero-secondary and both-zero columns. Maximum objective difference was1.14×10⁻¹³. Coefficients remained feasible. This is an objective check, not a certificate for the larger nonlinear search.
2. **Absent physical plane path checked.** An independent three-record geometry check uses same-side and opposite-side receivers. Predicted first-order excess delays agree exactly with direct image-source computation; an absent secondary reflection retains the primary waveform with zero secondary gain and negligible residual. The model still assumes an infinite plane with unknown finite extent and no occlusion.
3. **Clock experiment now follows the response convention.** `render_v4.py` computes receiver samples from the underlying waveform at `(receiver_time−offset)/alpha`, then adds noise and quantizes. `run_v4.py` invokes immutable de8442b raw processing before both diagnostic versions. Thus clock correction, correlation, direct peak anchoring and training-kernel learning are all repeated. Unlike the v3 sensitivity script, it never shifts only the final stored axis. The experiment tests fresh affine-rate/offset/noise realizations, not a posterior confidence distribution, wrong-epoch gaps or general non-affine timing.
4. **Recorded totals independently re-aggregated.** The24 frozen rows match the report. Reused cases:62matched/13false/0missed becomes38/0/24. New raw-clock cases:62/12/0 becomes38/0/24. Each group has4dual warnings,0warnings on8controls and0classification changes between old and exact gain objectives. Both near-reflector cases retain seven surfaces. This checks consistency of preserved records; it is not a second execution of the24 classifiers or independent confirmation of their physical accuracy.
5. **No evidence of a new blocker in the bounded-gain fix.** The private helper assumes the two-dimensional record-by-sample arrays used by its callers. It is not a validated general public API. Its near-singular Gram threshold is a floating-point safeguard; retaining the explicit scope is appropriate.

## Limits that remain consequential

The frozen report preserves an accepted approximately143ppm rate error on the direct-only control and related family-matched recordings. Its residual maximum lies just below the unchanged100µs retry gate. That means a nearly accepted affine fit can still have selected inconsistent correlation lobes and can understate timing error. The report appropriately labels the proposed cause as a diagnosis, and does not change the threshold to pass this case. This review does not inspect or endorse any later oracle-clock result.

No control warning was observed in these finite, related synthetic cases. Many families share geometry and random draw sequences by design, and all positive cases use one fixed secondary displacement, driver delay and orientation. Counting576 recordings does not make them576 independent source-model trials. Four warning successes do not establish real-world false-alarm control, unknown speaker routing, arbitrary driver phase, finite/occluded reflectors or reliable identification of the primary direct component.

The waveform partition remains held out only for global source/plane parameters and kernel learning. Gains and local alignment are re-fitted on held records. “Held-record profiled compatibility” is therefore the correct interpretation. Equal proposal/refinement budgets between source and plane models do not prove equally complete searches across their differently sized domains. The source-support rank gate remains an engineering condition, not full shared-covariance identification probability.

The signed zero normalization was exercised coherently in the new simulation. Its observed ratio to the local peak is useful bounded evidence, but does not establish robustness for untested source filters or a wrong direct anchor. The empirical kernel may still absorb early reflected/source structure. Preserving the uncertainty and calibration-warning semantics is necessary.

The runner's boolean benefit criterion is `any` fresh dual case with a warning and a baseline false surface, while its control/near-reflector criteria are checked per case. The actual result exceeds that minimal benefit gate because all four dual cases warn. Future reports must retain individual dual misses; the current boolean alone would not certify universal retention of the nominal benefit. No result is changed by this observation.

The v4 snapshot is an immutable review artifact, not a standalone replacement for the complete experiment directory. Rendering imports pinned repository helpers, and reused v3 cases depend on their saved raw/baseline artifacts. Any later portable restoration must preserve those dependencies and the freeze's exact hashes rather than imply that the30 files alone regenerate every prior input.

## Recommendation

Accept the bounded-gain mathematical correction and the raw-clock experiment as valid development improvements to the diagnostic evidence. Keep the entire branch experimental. Preserve the24 lost true surfaces and the accepted clock bias in any handoff. Resolve the clock acquisition issue through its separately authorized investigation; do not reinterpret source-warning success as proof that timing covariance or hardware source calibration is valid. No threshold change, new source-model search iteration or promotion is recommended by this review.

## Portable archive and reproduction

The exact reviewed source is preserved at [source-model-diagnostic-v4](source-model-diagnostic-v4/README.md); all 30 original manifest entries, including its execution log, are present. The [review bundle](source-model-v4-review/README.md) preserves the original reviewer script, report and result bytes with source hashes. The portable helper changes only paths/arguments and comparison against the frozen result:

```sh
.venv/bin/python evidence/source-model-v4-review/reproduce.py
```

The archival check reproduced the 84 gain cases, physical absent-path check and aggregate results exactly, without new raw data or classifier fits. Its output is written under work/. The separate [postfreeze oracle archive](clock-oracle-diagnosis/README.md) was copied with exact hashes for provenance; it was not part of this review and was not re-executed during archival. The four individual fresh dual warnings and the runner's weaker `any` benefit flag are both preserved unchanged.
