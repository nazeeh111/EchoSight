# Hardware acceptance plan: MacBook and iPhones

**Prepared before our device experiments; no hardware result is claimed.** This plan freezes an initial set of engineering gates. It does not request recordings now. Run it only after the selected software checkpoint, import route and operator instructions are ready. Preserve failures and change the plan explicitly if the scenario proves infeasible; do not widen thresholds after looking at answers.

The strongest intended physical demonstration is surveyed room structure, including height, inferred from recorded echoes, with supported reflector changes clearly separated from unlocalized acoustic change. Supplied microphone/source positions and a calibration reference plane are not recovered scene geometry. Synthetic scenes, hybrid replay of measured impulse responses, published measurements and our future phone measurements remain separate evidence classes.

## Package and fixed comparison rules

Create one private acceptance directory per software commit and source/recorder configuration. Preserve:

- Original recording/export bytes and hashes, imported lossless bytes, probe WAV/manifest hashes, session/protocol JSON, complete results and every rejected capture.
- MacBook/iPhone model, OS and recorder version; actual reported sample rate; playback channel, gain and lid/orientation; recording route and processing settings; interruptions and timestamps. A left/right software channel does not establish a single physical loudspeaker.
- A common right-handed metre frame, microphone and effective-source acoustic-center positions, survey uncertainty, calibration identifier and source configuration identifier. Device centers are not acoustic centers.
- An independently measured reference reflector and room/target geometry, with survey method, uncertainty and coverage. Keep evaluation truth in a separate file never supplied to mapping. The calibration reference is supplied only to `calibrate-reference` and is excluded from the claimed count of newly recovered surfaces unless separately reconstructed without that truth.
- The frozen training/validation capture-ID partition, evaluation script/version, baseline outputs and elapsed acquisition/processing times. Keep all attempts; a rejected recording is not a silently discarded success denominator.

Use the mapper, direct-plane-grid competitor and simple baseline on the same immutable recordings and supplied calibration. Report surfaces recovered/missed, unmatched definitive surfaces, height support, angular/distance errors, reported uncertainty versus error, rejected captures and runtime. No favorable subset replaces the complete prespecified set.

For independent geometry scoring, match one-to-one using normal error ≤5 degrees and perpendicular distance ≤0.10 m from a prespecified surveyed point on the true plane to the inferred plane. This is invariant to the arbitrary coordinate origin. Report error at all surveyed points on that plane as well. A match to a support patch does not establish a physical edge, closed enclosure or empty/safe space. If the independent survey is incomplete, label an unmatched estimate **unverified**, not proven nonexistent; it still fails the zero-unmatched demonstration gate until resolved independently.

## H0: file and route qualification

**Inputs:** Each intended phone/recorder/route at one fixed, clear-line-of-sight position. Capture one silence interval and three complete seven-pilot shots. Start with the existing 48 kHz phyphox experiment or another lossless PCM recorder, preserving actual delivered rate. Keep each record below the implemented 30 s processing limit.

**Pass gates:** All three signal recordings import without dropped/nonfinite samples, explicit sample gaps, rate changes, missing metadata or route/interruption notices. Original and imported raw hashes survive export/reload. The delivered rate supports the selected band: `high_hz <= 0.45 * actual_rate`. All seven pilots are recovered. Clipped sample fraction is ≤0.0001. Each record has `status: ok`; no `direct_reference_ambiguous`, `nonaffine_clock_or_motion`, `clock_rate_out_of_bounds`, `truncated_probe`, `weak_direct` or unsupported-band diagnostic. Silence returns no definitive geometry.

**Failure consequence:** That device/route is not qualified. Preserve originals; correct format/rate/route or acquisition interruptions and repeat H0 as a new labeled attempt. If phyphox cannot provide adequate export/continuity, a native measurement-mode recorder is a possible next implementation, not an already delivered fallback. CSV numeric fidelity and a lossless container do not prove unprocessed ADC samples or absence of sub-pilot discontinuities.

## H1: repeated level, timing and source-route checks

**Inputs:** One fixed source, one fixed receiver and one independently surveyed, isolated large planar reference. Three complete shots at each of three playback amplitude levels spanning at least 12 dB, with OS route/orientation and recorder settings fixed. Record the exact digital level and probe hash for each level. Avoid an automatically changing gain configuration. Repeat this qualification for each proposed source channel/route; do not pool them.

**Pass gates:** Every shot passes H0 signal checks. For the same clearly isolated reflected arrival, the range of median excess delays across levels is ≤100 microseconds; within-level maximum deviation from its median is also ≤100 microseconds. Differences must additionally be consistent with declared path/direct/clock uncertainty; the 100 microsecond ceiling is not permission to ignore a smaller supported error bound. Require no unresolved multiple-candidate reference window or systematic level trend hidden by averaging.

**Failure consequence:** Linear timing/source qualification fails even if samples do not clip. Reduce playback level or change the band/route/recorder and repeat H0–H1. Keep the failed configuration as a failure. Do not increase timing uncertainty solely to absorb a level-dependent bias. Path-dependent dispersion can remain invisible to this test; passing does not certify all reflector materials or bearings.

## H2: source center and effective-speed calibration

**Inputs:** Twelve independently surveyed receiver stops spanning at least three bearings and three heights, plus the surveyed reference plane. Prefer a dedicated calibration panel distinct from the six room surfaces that will be scored later. Before recordings, designate eight training stops and four held-out stops; all twelve must be distinct and the held-out stops must be at least 0.10 m from training positions. Aim for at least 0.25 m smallest centered position singular value in the training set and roughly 1 m height span. These arrangement targets supplement, not replace, the runtime Jacobian/rank checks. Capture one complete raw record per stop and one repeated reference stop outside the twelve-point calibration partition for drift checking.

**Pass gates:** Every partitioned capture passes acquisition; exactly one candidate lies in the physically allowed reference window at every stop. The calibrator must accept the fit, remain inside its declared source-position/effective-speed search bounds and pass its rank checks. Training and held-out normalized RMS are ≤2.5; held-out maximum normalized residual ≤3.5; held-out absolute RMS ≤100 microseconds and maximum absolute residual ≤200 microseconds. Across prespecified bearing/height groups, median held-out residuals differ by ≤100 microseconds. The repeated reference delay agrees within the H1 limit.

**Failure consequence:** The chosen point-source model, reference isolation, survey or band is unqualified. Inspect the specific rejection and acquire a simpler isolated-reference configuration if necessary. Do not select whichever echo best matches desired wall truth, refit held-out captures or drop failing validation positions. The current calibrator deliberately rejects ambiguous reference windows.

Apply an accepted proposal's source position, `effective_speed_m_s` and full `source_effective_speed_covariance` together. The calibrated quantity is `v=c/kappa`, where kappa is actual/nominal source sample rate. Excess buffer delay is `(|r-q|-|r-s|)/v`; physical delay is buffer delay divided by kappa. The experiment does **not** separately measure physical sound speed or absolute source-clock rate. Preserve common source/speed covariance across all later observations; do not treat each phone as independently calibrating that scale.

## H3: real clock and reverberation stress

**Inputs:** All intended phones at fixed surveyed stops, three shots per phone at 0.22 s pilot spacing and three at 1.0 s spacing, with identical route/band/source geometry. These are continuous playback buffers, never seven separately scheduled play calls. The seven-pilot 1 s buffer is about 6.32 s long. Include one deliberately interrupted acquisition as a negative control, labeled in evaluation annotations.

**Pass gates:** Each uninterrupted configuration passes all signal checks, `abs(relative_rate_ppm) <= 5000`, and maximum affine pilot residual `<= max(2 / actual_rate, 100 microseconds)`. Reference echo delays agree across repeats/spacing within 100 microseconds and their declared uncertainty. An interrupted record must be rejected or explicitly withheld from geometry; any confident geometry from the negative control is a failed robustness check, even if attractive. Report both intervals' complete acceptance rates separately.

**Failure consequence:** If only long spacing passes, qualify only that longer buffer and include its acquisition latency in the demo. This previously helped some measured-response replays, but that observation is not a guarantee for the room or phones. Relative alpha correction is not absolute clock calibration. A failed warp/interruption control limits the route; there is no validated arbitrary-warp correction. Sub-pilot gaps may be undetectable, so absence of a diagnostic is not proof of continuity.

## H4: static spatial screening, then the full room gate

**Inputs:** A static, independently surveyed room chosen before capture, with all large structural surfaces and consequential interior reflectors recorded in evaluation truth. Use twelve noncoplanar microphone stops with the qualified source fixed. Three or four phones may visit successive placements because the scene remains static. Reserve four additional distinct receiver positions before capture for response-prediction validation, without refitting the map to those recordings. Keep a repeated reference position for drift.

**Screening gate:** At least four independently supported structural planes, including a horizontal plane, meet the 5 degree/0.10 m match rule, with zero unmatched definitive planes. Report all missed surfaces and ambiguity. This is a partial spatial screening pass only.

**Full selected room-layout gate:** All six surveyed enclosing planes, including floor and ceiling, meet the same rule, with zero unmatched definitive planes and no asserted physical edges or closed-room certainty. At the four withheld positions, all identifiable supported first-order paths have RMS prediction error ≤100 microseconds and maximum ≤200 microseconds. Missing or ambiguous paths remain in the report; they cannot be silently dropped to obtain these errors. The entire twelve-stop recording-to-result run must finish within 10 s on the declared MacBook environment, measured separately from acquisition and repositioning.

**Failure consequence:** A four-plane screening result does not satisfy the six-surface room-layout demonstration. Preserve partial/ambiguous output. Diagnose direct reference, higher-order associations, finite visibility, survey conditioning and held-out residual trends. If fixed-source higher-order aliases remain, proceed to H5 using extra information; do not force missing room walls or a visually pleasing box. A room containing unmodeled furnishings can reasonably fail the complete-room gate. That requires an explicit scenario restriction or another measurement, not an edited truth set.

## H5: calibrated source-relocation improvement and degeneracy controls

**Inputs:** Four fixed noncoplanar phones and four calibrated source positions with genuinely three-dimensional movement, giving sixteen raw records in a static scene. Keep source route/orientation fixed; survey each effective source center and carry joint source/speed covariance plus each reused receiver pose covariance once. Freeze source/receiver positions and independent room/large-panel truth before fitting. Repeat a fixed-source set and a collinear source-motion set as degeneracy controls; repeated source poses are not independent directional information.

**Pass gates:** The joint mapper reports full source diversity and adequate receiver support at every included source. For a room-only scenario, require six matched surfaces including two horizontal surfaces, zero unmatched definitive planes, the same 5 degree/0.10 m geometry tolerance, and ≤60 s raw-input processing time. For the prespecified large-panel scenario, require the panel's additional plane within tolerance; support hulls must remain explicitly unrelated to physical panel edges. Fixed/collinear source controls must not receive an unconditional full-room success claim; unresolved aliases remain ambiguous. Compare identical observations with the joint direct-plane-grid method and independent-source consensus baseline.

**Failure consequence:** Source movement does not universally identify reflection order. Two source poses, tangential motion, missing-parent echoes, changing source directivity and distributed emitters can remain ambiguous. Do not label a four-source average of disagreeing planes a measured room. Qualify the route at new bearings, change the independently surveyed geometry, or retain a partial result. Current synthetic tests are evidence for selected configurations only; this is a new physical gate, not a claim that it has passed.

## H6: controlled reflector change with the actual phone count

**Inputs:** Exactly four epochs, `A_before`, `B_first`, `B_repeat`, `A_return`, with the same three or four fixed phones, source, probe and survey. Use a large surveyed planar reflector displaced by a prespecified 0.20 m normal translation and restored; keep unrelated reflectors still. Record all required protocol declarations, stable device/pose IDs, source configuration, route/calibration IDs and an independently justified conservative differential timing uncertainty. Also run a null protocol and a gain-only protocol. Do not use repeated device labels to pretend four stationary phones occupy twelve simultaneous positions.

**Acoustic-change gate:** The moved-reflector trial returns `repeatable_acoustic_change_unlocalized` or `conditional_spatial_change`, with at least three distinct phones showing repeated observed echo shifts in either direction, beyond the implemented timing/repeatability gates. Within-state isolated echo delays agree within 100 microseconds. Null and gain-only controls do not yield a spatial-change claim. A deliberately failed restoration or changed route/calibration/source identifier must return `inconclusive`. The same shared timing budget remains present across phones; it is not divided by their number.

**Localization gate, separate:** Only `conditional_spatial_change` can support a geometric-change demonstration. Both states and both repeats must have independently confirmed multi-view geometry, matching candidate-level support, displacement error ≤0.10 m, normal error ≤5 degrees and A-return geometry within those tolerances. No amplitude-only localization, object-removal assertion or unconditional causal claim is permitted. The ordinary two-result comparison is a display baseline: it can report the same A/B plane shift even when restoration fails.

**Current consequence:** With four fixed phones, the current single-source mapper generally withholds definitive geometry; the controlled module therefore returns useful but unlocalized repeated acoustic change. The twelve-static-receiver development fixture supports conditional localization, but it is not achievable by pretending our four phones are twelve stationary devices. A future protocol combining independently controlled placements or source-relocated state maps needs its own implemented association/uncertainty handling and qualification. Do not claim that capability from current four-phone results or request extra hardware as an implicit requirement.

## Evidence boundaries and stop decisions

| Observation | Permitted statement | Not established |
|---|---|---|
| Unit/synthetic benchmark pass | Software recovered specified synthetic structure under stated model | iPhone or MacBook accuracy |
| FLAIR/dEchorate impulse response convolved with the probe | Real measured propagation response was replayed through processing | Consumer clock, live playback, recorder fidelity or our room accuracy |
| Supplied tape/laser survey or reference plane | Independent evaluation/calibration input | Acoustic recovery of that supplied geometry |
| Qualified raw phone session and matched independent truth | Accuracy for that recorded configuration and protocol | Arbitrary rooms, every speaker route/material or calibrated probability |
| Missing echoes, rejected paths or ambiguity | Measurement/model does not establish that structure | Empty space, removed object, safety or a completed enclosure |
| Controlled repeated change | Repeatable acoustic difference, optionally conditional planar displacement | Causality without trusting declared controls, physical object identity or novel general reconstruction |

A failed stage blocks the claim it qualifies, not preservation or unrelated software work. Keep the runnable backend, failure diagnostics and exact next experiment. Any changed device/OS/recorder version, source route/orientation, probe band or processing setting requires recording the change and repeating the relevant qualification stages. Public demonstration/submission and deployment remain separately authorized actions.

Implementation references: [acquisition route](ACQUISITION.md), [signal model](SIGNAL_MODEL.md), [reference calibration](CALIBRATION.md), [inference conventions](INFERENCE.md), [controlled protocol](audit/CONTROLLED.md), and the committed processing source. These references establish software behavior and previously accessed source documentation, not new hardware evidence.
