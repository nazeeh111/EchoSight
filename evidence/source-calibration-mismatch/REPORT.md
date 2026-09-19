# One-plane distributed-source audit: the first comparison is inconclusive

All12frozen calibration sessions rejected before inverse fitting: four single-source controls and eight two-emitter cases. Therefore this study does **not** establish that current calibration rejects distributed sources while preserving usable calibration, and it does not demonstrate false qualification. No calibration proposal existed for the orthogonal-reference transfer test. These are preserved negative outcomes, not cases to drop or regenerate under the same freeze.

The scientific question remains consequential. A tangential emitter pair can have nearly equal direct and image-source distances for receiver bearings near its perpendicular bisector. Exact equal-range receivers are coplanar and already rejected by the current rank guard. Nearby noncoplanar receivers can still offer limited discrimination. A reference with a nonparallel normal changes the source-image geometry; two independent normal directions do not universally identify a distributed source because an offset along their intersection can remain tangential to both.

## Executed design and evidence

Protocol SHA-256 `aef9d096f74c3e65a575ce1f525a5c83970032857537d268ae384c99f511ad89`; complete pre-generation freeze `run-v1/freeze.json` SHA-256 `24c2bdf8804000e8e0158030f29919d8306776f8438f8361ee185ebed7be179c`. Runtime is immutable3745665352f59bc88e432b1f703054ab29398ce1, isolated from the concurrent metadata-admission repair. All source hashes remain unchanged. No main files were edited.

Seeds2801/2819 each supplied12distinct noncoplanar receiver stops,8training/4validation. Three source patterns used one primary, or a24cm secondary offset with relative gain+.8or−.8; each was recorded against isolated x- and y-reference planes. Raw WAVs used fractional geometric delays, common FIRs, independent affine receiver clocks/noise and16-bit quantization. Supplied reference/source/receiver surveys and all existing calibration gates remained unchanged. No echo label, actual source location, actual speed or rendering clock entered fitting. Independent `process_session` replay provided evidence only after the unmodified calibration call; no observations were patched into the utility.

## Why the useful controls failed

Each single-source case has exactly one missing reflected candidate, while all12recordings are otherwise accepted. The affected receivers lie close to the source compared with their reflected path distance. The generating reference/direct ratios are:

| Seed | x reference | y reference |
|---|---:|---:|
|2801, receiver1|2.26%|2.41%|
|2819, receiver2|4.63%|4.76%|

The measured matched-filter ratios are approximately2.22–4.34%, below the unchanged7%relative candidate threshold. The missing echoes are physically present but weak; absolute noise reduction alone does not bypass this relative-amplitude gate. The current calibration utility correctly refuses to silently remove these predeclared stops. This is an acquisition-arrangement failure in the experiment, not evidence that the point-source inverse model is wrong.

The dual-source cases additionally show multiple eligible echoes and some raw direct-reference rejections. In-phase x-reference cases each have two stops with multiple eligible candidates; y-reference cases have many. Opposite-phase cases have additional lost/split candidates. Those observations suggest the orthogonal reference can expose a second emitter, but the absence of a successful same-protocol single-source control prevents a useful discrimination claim. No source estimate or covariance was produced, so source-center/transfer accuracy is unavailable, not zero.

Exact per-record candidate counts, all rejection reasons, generating amplitude ratios and locally observed reference responses are in `run-v1/summary.json`; full outputs and raw hashes remain beside the corresponding sessions. All144recordings and both raw processing paths are preserved. Reserved2609/2621 were unused.

## Minimal next decision and discriminating experiment

Before another source-model comparison, arrange receivers so the isolated reference echo is observable at every predeclared stop. This can be designed from the mechanical source prior and known reference plane, without fitting labels or selecting favorable recordings. For nominal source s0, receiver r, source search radius rho and reflection H(s0), conservative distances satisfy direct_length≥|r−s0|−rho and reflected_length≤|r−H(s0)|+rho. Require their ratio to exceed a predeclared stand-off bound for both reference planes. Under this experiment's declared reflection coefficient.20/.55, a ratio>.25 implies expected reflected/direct amplitude>.09, above the existing.07gate with a small margin. This is specific to the declared ideal reflector; actual hardware must check signal quality and cannot assume the coefficient.

A predetermined corner-like12-stop layout with broad x/z range and the same30cm y diversity can meet that stand-off requirement without changing calibration thresholds, source patterns or waveform processing. Then test the same source patterns and orthogonal-reference transfer on newly declared development seeds. This is a justified acquisition-design correction, not a reason to reinterpret the completed failure or rerun until a preferred result appears. No second study has been started or frozen in this branch.

If a qualified single-source control succeeds and a distributed source also receives a proposal, test its fixed source/speed pair on the orthogonal recordings without refitting. Rejection or ambiguity would establish a concrete applicability limit of one-plane calibration; consistent results would still not prove point-source behavior at all bearings/bands. If all distributed cases reject, report only that bounded protection. A general source qualification would need independent source routing/driver evidence or more directional measurements, not a stronger verbal claim from this12-session study.

The current result is an unresolved scientific applicability question plus a demonstrated, tractable acquisition-arrangement weakness. No new feature, threshold relaxation, hardware request, measured-data claim or production change is supported by this first comparison.
