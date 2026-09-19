# Independent clock-refinement outcome review

## Recommendation

**No material blocker found to implementing the exact frozen observed-rate trigger as a bounded production acquisition correction, subject to the coordinator's planned focused raw regression and resource/cancellation checks.** The branch need not close. Do not tune its thresholds or search from these outcomes. Preserve the individual extraction losses and uncertainty/model limitations; this evidence does not establish improved spatial acceptance, general lobe identification, calibrated alpha confidence, or a corrected source model.

The independent pre-results design note remains unchanged at `work/clock-refinement-independent-design.md`, SHA-256 `eed5e4a704e0f206ab870afa530f1167e3ca4c98506d1b04a1a7e435561bee5d`. Its affine-nullspace counterexample remains valid. The actual development evidence below did not realize that harmful clock-selection example.

## Exact inspected candidate and evidence

The frozen baseline is `de8442b2dd088c036d2b92eaeaf29a1273785795`; signal source SHA-256 `2fdc6c5d48f8e55efc1650eb52a9ffbc6880e4efa767dbd449900fc38859747f`. Reconstructed the candidate directly from the frozen runner and verified its SHA-256 **`6650fe627a8b18748eac2bb200e25c3058630676231fb67e1f4ebf2e6683d6a7`** against freeze and result metadata. The retained independent diff is `work/clock-refinement-independent-candidate.diff`.

The candidate changes only (1) the retry trigger, adding observed `abs(alpha-1)*duration > 0.5/bandwidth` while retaining the existing coarse ±5,000 ppm bound and failed-residual trigger, and (2) initial-clock diagnostic recording. The retry winner, peak search, rejection thresholds and final uncertainty calculation are unchanged. Read the renderer and runner; truth annotations are not processing arguments and metric truth is loaded after the two extraction calls. No oracle code or answers were used for fitting or this recommendation.

All five recorded protocol/runner/renderer/baseline hashes match the freeze. The 1,248-row result file SHA-256 is `2ea5270d63c19aa3fd13f77975d23ee0799eb49a29d3c35b8642318852e68b28`. File hashes verify inspected bytes, not independently prove historical freeze timing.

## Independent verification

Executed `work/clock-refinement-independent-outcome.py`; retained calculations in its `.json` companion.

- Recomputed one-to-one 75 us truth matching and affine rate errors/standardized errors for **all 1,248 records**, checking saved per-record metrics.
- Reexecuted both extractors from the actual hashed WAVs for **63 consequential records**: all 48 targeted negative controls, every increased-miss/increased-false record, the original >50 ppm error cases, and the worst accepted standardized-clock case. Status, clock, candidates and diagnostics reproduced exactly.
- Independently confirmed the aggregate frozen acquisition gates: accepted valid affine records **1,180 → 1,180**; accepted affine >50 ppm errors **3 → 0**; direct-null false candidates **1 → 0**; common-accepted valid-affine false candidates **813 → 799**, missed paths **2,989 → 2,985**; negative-control admissions **0 → 0**. There are no lost valid admissions or newly admitted negative controls. Recorded maximum candidate runtime is 0.03759 seconds, below the frozen two-second gate; this is a local workload measurement, not a universal runtime guarantee.
- **111** common-accepted clock objects changed. Twelve rate errors worsened slightly, by at most **0.589 ppm**; the largest changed candidate error/SD is **0.8802**. Thus the alleged “no worsening” must retain its >1 ppm qualification; exact monotonic improvement is false. The overall worst standardized rate error remains **4.4328**, in an unchanged record.

The numerical distinction matters: the existing residual-based alpha uncertainty is not now proved calibrated, but the additional selection did not create the large wrong-clock/small-SD failure in these tested records.

## Individual losses are real

Seven records have an increased net missed-path count; five have increased false candidates, with one gaining two. Eleven unique records are affected because one belongs to both groups. Full keys/count changes are preserved in the independent outcome JSON. All occur in the raw-clock v4 cohort. The false-candidate increases occur in dual-source families; increased misses also affect single-room and near-reflector cases.

For example, `single_room-2441`, source 3, capture 11 improves rate error from about 17.489 ppm to 0.445 ppm while losing a weak 22.362 ms path (baseline amplitude about 7.26% of direct) and moving the nearest peak for a 5.4807 ms truth path to 5.5613 ms, beyond the frozen 75 us matching tolerance. More accurate alpha does not imply monotonically better peak extraction when resampling, overlap, anchoring and amplitude gates interact. These losses must not be suppressed, relabeled as successes, or repaired by tuning the matching or detector threshold.

Changed-clock records also retain direct-reference bias in the dual-source cases: the candidate's worst physical-direct error is about **519.54 us**, or **12.45** supplied direct standard deviations after converting source-buffer SD to receiver-time units. The baseline worst is about 12.42 SD. This is inherited source/direct-reference model failure, distinct from the improved alpha estimation. It cannot support a general timing-calibration claim.

## Spatial consequence check

Inspected the postfreeze scene runner: both arms use the same immutable mapper, with only the observations changed; truth is used for subsequent scoring. Independently recomputed all **24** stored paired scene scores using the immutable baseline evaluation metric implementation. Every case's matched/false/missed counts is unchanged; totals are **124 matched / 25 false / 0 missed** for each arm. Conditional interval checks are unchanged at 124/124 offset and 123/124 normal; those counts do not calibrate physical coverage.

To avoid relying only on stored geometry, independently reran both mapper arms for `single_room-2441` and `near_reflector-2441`, the two valid-source scenes with the concrete extraction losses above. Returned surfaces match the stored outputs exactly: respectively **6/0/0** and **7/0/0** matched/false/missed in both arms.

Artifacts: `work/clock-refinement-independent-spatial-check.py` / `.json`. The inspected scene report SHA-256 is `4f2a9466566bf96332709b6a55b8037fef2943b786222423c6e8abbcd88b965b`. This establishes no observed spatial-count regression on these exposed cases, not an improvement: the 25 existing false surfaces remain.

Read the additional historical-control code/report, which reports 27 affine admissions in both arms, zero admissions among 30 negative controls, and 21 accepted / 4 rejected among 25 measured-response-derived replay signals in both arms. These extra historical waveform runs were **not independently rerun here** and are supplementary author-produced evidence; measured response replay does not test physical clock drift. The independent 63-record and two-scene reruns above are separate local execution evidence.

## Promotion limits

The frozen acquisition gates pass, their individual losses have been examined, and the scoped downstream scene checks do not turn those losses into a new surface-count failure. This supports proceeding with the exact trigger, without changing the estimator, thresholds, alpha convention or source-model interpretation. Keep the production change narrow and retain initial/final clock diagnostics so a future problematic train can be diagnosed.

Before claiming the integrated production repair verified, run the planned focused regression and resource/cancellation checks against the actual committed implementation, including preservation of the coarse ±5,000 ppm guard and the single-retry bound. Do not describe the design note's unresolved affine ambiguity as solved. Neither an additional trigger nor reduced affine residual proves direct-path identity, unbiased alpha, absence of model mismatch, or physical hardware validation.

No implementation, frozen experiment, threshold or archived result was edited during this review. No full 24-scene refit ritual or new acceptance-seed generation was performed.
