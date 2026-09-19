# Stand-off reference experiment and joint-information diagnosis

**One-plane calibration can issue a conditional proposal for a distributed source.** In the separately frozen stand-off study, all four single-source controls produce proposals. Both opposite-phase two-emitter cases also produce proposals against the x-reference, with held residual RMS9.8/13.7µs, while the perpendicular y-reference exposes two eligible echoes at every receiver and rejects. The output source uncertainty is large, approximately22cm along the emitter-separation direction. This is an applicability limitation of a conditional proposal, not proof that the utility falsely certified physical hardware or reported a precisely known wrong point.

The original12-session study remains an acquisition-observability failure: even its single-source controls had weak reference echoes below the existing7%detector floor. No rejected stops, source patterns, thresholds or historical outcomes were removed. Only a separately frozen receiver arrangement and new seeds changed in V2.

## Frozen design and outcomes

V2 freeze SHA-256: `91df03d959f036f5bcad7671f04090d22633b56001d7fdb51c83be281d5b101a`. Runtime stays at immutable3745665352f59bc88e432b1f703054ab29398ce1; this predates the concurrent declared-source metadata repair, which cannot resolve the acoustic ambiguity studied here. V2-PROTOCOL.md fixes twelve sessions at seeds2821/2833: single, in-phase dual and opposite-phase dual sources, each against isolated x/y reference planes. All source centers,24cm separation, gains, band, FIRs, clock/noise parameters and calibration gates remain identical to V1.

The predetermined8training+4held positions have broad x/z spread and30cm y spread. Under the explicitly assumed reflection coefficient.20/.55, the source-radius geometric lower bound gives reference/direct amplitudes≥14.0%(x) and10.77%(y), above7%without selecting realized echoes. Training centered-position singular values are4.596/3.394/.424m. This improves visibility and avoids exact coplanarity, but does not by itself establish good source/speed conditioning.

| Source pattern | x reference, two seeds | y reference, two seeds |
|---|---|---|
|Single emitter|2proposals|2proposals|
|Dual, same phase|2rejections|2rejections|
|Dual, opposite phase|2proposals|2rejections|

In-phase x cases each have one stop with an unidentified reference path; y cases have ambiguous eligible paths. Opposite-phase x observations pass the existing exactly-one candidate rule and held residual gates. Their conditional source centers lie3.37/6.52cm from the primary,20.63/30.52cm from the secondary, and8.63/18.52cm from their midpoint. These are descriptive distances: a distributed source has no single generating point center. Its source/speed pair may approximate one bearing/reference arrangement without applying to another.

## Transfer failure and uncertainty must remain visible

The two opposite-phase x proposals cannot be tested against one unique y-reference echo: every y recording has two eligible candidates. The frozen evaluator labels this ambiguous and chooses neither. It does not fit to the best-looking echo or force an apparent residual pass. This exposes additional physical information from the second reference while preserving unknown path identity.

Both single-source y sessions contain one eligible reference echo at all12stops. Applying the x proposal unchanged gives:

| Seed | Orthogonal RMS | Maximum residual | Existing absolute100/200µs gates |
|---|---:|---:|---|
|2821|50.9µs|71.6µs|Pass|
|2833|229.5µs|282.7µs|Fail|

The second result is a valid-control failure of a reject-only transfer rule. It must not be recast as evidence of a distributed source. That x proposal is8.8cm from the generating point but reports22cm y-axis source SD. Its parameter-covariance projection already predicts substantial orthogonal uncertainty. Low residuals on a weakly informative reference arrangement do not guarantee useful predictions elsewhere. The large linearized covariance also extends beyond the bounded15cm search region; it is a local conditional approximation, not a globally calibrated/truncated probability distribution.

Single-source x proposals have y-axis SD≈22cm and speed SD7.9–8.6m/s. The y-only proposals have y-axis SD24.7–25.0cm and speed SD44–46m/s. These are poor constraints despite passing the relative Jacobian-rank guard. The original procedure truthfully emits covariance and calls the result a proposal, but clients must not silently treat this as a precise source center or universally applicable route calibration. Independent held positions within the same narrow bearing arrangement do not remove that limitation.

## Bounded joint-reference information calculation

No joint source fit, new waveform search or raw case was run. `joint_information.py` uses only supplied mechanical source[1.5,1.5,1.3]m, nominal speed343, supplied receiver positions, known reference geometry and the uniquely selected single-source observations. Derivatives are evaluated there, without actual source coordinates, true speed or echo labels entering the calculation.

For source parameters theta=(s_x,s_y,s_z,v), reference n/d and image q=s+2(d−n·s)n, the prediction is f=(|r−q|−|r−s|)/v. Its source derivative is `[(I−2nnᵀ)(q−r)/|q−r| − (s−r)/|s−r|]/v`; its speed derivative is−f/v. The observation covariance retains candidate/direct/relative-rate timing terms, the shared error of each receiver reused across x/y captures, and the independent plane-survey offset/orientation errors shared across all captures from each reference. No source-position prior is invented from the search bound.

With the training rows stacked, conditional local information is `Hᵀ C⁻¹ H`; its inverse estimates attainable local parameter covariance under the stated correct-model assumptions. The two source/speed models are not averaged as independent estimates. Analytic versus finite-difference source/speed derivatives agree within1.7e-13. Adding the second reference reduces covariance by a positive-semidefinite amount in both seeds. Results are nearly identical across seeds:

| Information used | Source SD x/y/z | Effective-speed SD |
|---|---|---:|
|x only|3.55/21.6–21.7/2.92cm|≈8.0m/s|
|y only|4.42/23.5–23.7/2.61cm|≈42m/s|
|Joint x+y|1.65/2.51/1.84cm|≈3.85m/s|

These numbers are information calculations, not executed joint-calibration accuracy or empirical confidence coverage. Shared receiver errors are retained across references. Plane surveys were explicitly assumed independent; a real common survey-frame error would require the corresponding cross-reference covariance, not duplication of independent uncertainties. Wrong source models, unresolved/incorrect paths and nonlinear effects can invalidate this local approximation.

## Bounded recommendation and burden

The evidence justifies investigating a new joint two-reference proposal for a stationary, consistently oriented source. It does not justify applying the already failed x proposal to the orthogonal scene, suppressing large covariance, or promoting a multi-driver detector.

A prospective implementation should retain the current single-eligible-path admission rule and all original per-reference training/held gates. It may form a new shared source/speed fit from the8training stops on each reference, with the full cross-reference receiver/reference uncertainty, then test both original held sets without refitting or exclusions. It must preserve the failed one-plane transfer as a separate result. The current opposite-phase dual inputs would be unavailable before fitting because all y stops have two eligible echoes; no oracle assignment is needed. If a future joint fit still fails a qualified single-source control or its fixed held gates, that failure remains decisive. This report does not execute or claim success for that future fit.

The practical burden is24recordings at12receiver stops instead of12, plus two independently surveyed nonparallel reflectors and a source that remains fixed in position/orientation/routing between arrangements. With four phones, the12stops could span three placements, but this is an acquisition plan, not a demonstrated device workflow. Isolating a single reference reflection from each ordinary room recording is itself restrictive. Repeating this for every source relocation would be costly; transferring a source-center offset between poses requires known rigid device orientation and actual route stability, neither established by this experiment. Qualifying a controllable single emitting route may therefore be more valuable than adding unconstrained calibration complexity.

Two nonparallel planes are not universally sufficient: an emitter separation along their intersection remains tangential to both, and frequency/bearing-dependent device responses can defeat the point model. Further directional information or physical source evidence may be necessary. The present24cm/opposite-phase surrogate is not a measured MacBook driver arrangement. No material/appearance inference or adjudication layer was introduced.

## Preservation and reproduction

V1 source/output snapshot is `snapshot-b8c1049d8d6d/`; all original failures remain. V2 artifacts are `run-v2/{freeze,results,covariance-diagnosis,joint-information,information-checks}.json`, raw session/reference/truth/observation/calibration files and recorded raw hashes. `run_v2.py` refuses to overwrite its freeze or existing generated cases. The numerical diagnosis requires the preserved single-source V2 sessions and observations; its source is included.

The compact archive excludes WAVs and runtime checkouts. It includes both frozen protocols/runners/results, all per-session input and evaluation metadata, observation evidence needed for the information diagnosis, source hashes, and reproduction requirements. Regenerate from the pinned commit with project NumPy/SciPy dependencies into a fresh work directory; no external datasets, credentials, downloads or hardware are needed. All runtime code and thresholds remain unchanged. No production feature has been implemented by this audit.
