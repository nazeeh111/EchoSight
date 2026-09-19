# Controlled repeated acquisition contract (development)

A two-result comparison tracks fitted planes for display. It cannot distinguish a lasting acoustic change from an unreliable repeat, a changed route or changed calibration. This module evaluates a bounded four-epoch experiment: `A_before`, `B_first`, `B_repeat`, `A_return`. All epochs enter through ordinary lossless recording sessions and use the same surveyed device/source poses, probe, coordinate frame and calibration.

The protocol has `schema_version: "1.0"`, `protocol_id`, `coordinate_frame_id`, `intervention_description`, and `controls`. Controls explicitly contain `devices_and_source_stationary: true`, `only_declared_intervention: true`, `restoration_attempted: true`, and `differential_timing_std_s`. The last number is a supplied conservative bound on remaining differential timing uncertainty from shared calibration or source drift; it is not silently estimated from successful repeats. Repeated recordings do not reduce this common uncertainty.

`epochs` contains exactly four objects in the stated order. Each has `epoch`, `session` (ordinary session JSON path or dictionary), `calibration_id`, `source_configuration_id`, and `route_ids` mapping every capture's stable `device_id` to a nonempty route identifier. Every capture declares `device_id` and `receiver_pose_group_id`. Capture IDs and these pose/device pairings must remain identical across epochs. Each epoch has exactly one capture per distinct stationary device and distinct receiver pose; coincident positions cannot inflate evidence counts. The source/probe/pose/calibration data and declared route/source identities must agree. Metadata declarations document what the operator asserts; they are not instrumented proof that nothing else changed.

`process_controlled_protocol` processes actual recordings before comparing them. It compares direct-normalized response envelopes, accounting for within-A and within-B repeat disagreement and a timing-uncertainty derivative bound. A receiver supports repeatable change only when both repeats agree and the cross-state difference exceeds both repeat disagreement and the timing bound. Pure recording gain is normalized away. A missing echo does not establish removed structure. Positive echo candidates must persist within A and within B before their delay shift can support conditional localization.

Returned statuses are `no_repeatable_change`, `repeatable_acoustic_change_unlocalized`, `conditional_spatial_change`, `inconclusive` and `cancelled`. Conditional spatial change additionally requires definitive planes in all four recording-derived results, consistent within-state fits, a cross-state plane shift beyond conservative reported geometry uncertainty, and positive shifted-echo support. Ambiguous geometry retains the unlocalized acoustic finding. Rejected captures, changed route/calibration/source metadata or poor A-return/B-repeat agreement prevent a change claim. No status declares an object removed, a safe/empty region, physical validation or unconditional causal attribution.

The numerical gates are engineering consistency gates, not calibrated p-values or false-alarm probabilities. Common uncertainty is included once as a bound, never divided by the number of repeats. The protocol cannot rule out an undeclared, reversible environmental or transducer change correlated with the intervention. A reliable hardware protocol should qualify the source/route first and keep people and other reflectors still.

Before implementation, development scope is fixed to independent raw recordings for: no change, gain-only change, declared route/calibration drift, a reversibly moved large planar reflector, failed return and cancellation/malformed metadata. These are development controls, not held-out accuracy estimates. The moved-reflector acceptance is repeatable acoustic change with positive delayed-echo evidence; conditional spatial localization is reported only if four independent geometry fits support it. Existing synthetic and measured spatial gates are unchanged.


## Executed development findings

The first unsmoothed envelope comparison missed a 0.2 m moved reflector because linear derivative bounds at the conservative 41.7 microsecond detector floor exceeded the largest possible normalized difference. The comparison now smooths to three times the combined timing-uncertainty scale before applying its derivative bound. It preserves the uncertainty and numerical gates rather than lowering them. A-return and B-repeat agreement are still checked separately.

Conditional localization propagates the source-referenced plane offset `|d-n·s|=|q-s|/2`. The per-epoch standard-deviation bound is `(sqrt(nᵀ Cq n)+sqrt(nᵀ Cs n))/2`; summing those bounds across epochs avoids assuming unknown source/image or cross-epoch correlations are independent. A test translates the entire coordinate frame by tens of metres and verifies identical displacement and uncertainty decisions. Positive shifted candidate IDs must match the evidence supporting the associated planes in all four epochs. Both signs of delay change are accepted.

The twelve-receiver development control uses twelve distinct stationary devices, not four devices claiming twelve simultaneous poses. A separate practical four-stationary-phone control establishes repeatable acoustic change but correctly keeps geometry unlocalized when each four-view map remains ambiguous. An initial development fixture had reused four device labels across twelve positions; that acquisition-label error was corrected, and the core now rejects such protocols. Earlier local reports with those labels are superseded, not physical evidence.

Reproduction: `python -m unittest tests.test_controlled`. These development controls do not establish field false-alarm rates, real source stability or hardware accuracy. Raw development outputs remain under task-local `work/controlled-development-stationary/`; they are reproducible from the independent waveform helper in the test module.

| Raw development control | Result | Evidence |
|---|---|---|
| Unchanged reflector, 12 devices | No repeatable change | Zero changed views |
| Recording gain reduced to 60% in B, 12 devices | No repeatable change | Direct normalization removes common gain |
| Reflector moved 0.2 m toward source and restored, 12 devices | Conditional spatial change | 12 positive shifted-echo views; inferred displacement −0.19994 m |
| Same move with four fixed phones | Repeatable acoustic change, unlocalized | Four positive shifted-echo views; single-state geometry remains ambiguous |
| Reflector moved but not restored | Inconclusive | A-return check fails; ordinary A/B display comparison still reports a −0.19994 m shift |
| Declared route, source or calibration drift | Inconclusive before processing | Explicit metadata mismatch |
| Large 1 ms shared differential timing uncertainty | No supported change claim | Common budget is not averaged down across receivers |

Seven focused tests pass, including coordinate translation, malformed metadata, cancellation, and repeated-device rejection. The five recorded development runs take approximately 0.15–0.52 seconds each on this local environment. This is a bounded numerical demonstration, not an estimate of live phone reliability. The raw report `work/controlled-development-stationary/summary-final.json` records the exact controlled-module hash and verifies it did not change during those runs.


Integration adds independent byte-identity checks: copied recordings cannot count as separate devices or repeats. Relative clock-rate uncertainty contributes delay-dependent variance in positive echo checks and a worst-window bound in response comparison; remaining shared differential calibration error is separately declared. Nested result responses omit dense values with explicit sample counts, while all path/geometry evidence remains. Eight core tests now include clock-budget sensitivity and duplicate-byte rejection. The API/CLI raw-recording path, version conflicts, result publication, cancellation and restart are verified separately in the integrated checkpoint evidence.
