# Frozen two-instance calibration-to-room transfer

Status: prepared only. No new WAV generation or mapper run is authorized until the coordinator inspects the exact freeze. This is one bounded development experiment, not a new physical qualification or general held-out benchmark. Existing scientific reports/gates remain unchanged.

## Question and fixed source identity

Does each of the two existing accepted two-reference fits improve room reconstruction enough to earn consideration of a public multi-reference feature, compared with nominal and existing x-reference calibration?

The V2 generator `work/source-calibration-mismatch/run_v2.py` completely defines the synthetic emitter: nominal [1.5,1.5,1.3] m; actual [1.54,1.48,1.31] m; one stationary point emitter; effective speed 346 m per source-buffer second; source FIR [.82,.13,-.045,.025]; receiver FIR [.94,.045,-.018,.006]. Its seven 40 ms 2–14 kHz linear chirps repeat every350 ms at48 kHz with100 ms lead and180 ms tail. The new renderer uses those exact settings and the existing independent waveform helper in evaluation/path_interpretations.py. The impulse uses the same49-tap Hann-windowed sinc fractional delay, interpolation clock warp, recording scale0.45, noise SD0.00012, alpha±250 ppm, offset40–100 ms and PCM16 rounding. V2 reference reflection amplitude is0.20×direct/reflected distance. The new room amplitude is the existing room renderer's0.55×0.7×direct/reflected distance, representing different room reflectors, not a change to the source or receiver.

There is no recorded hardware route, device orientation or physical directivity in this synthetic corpus. They are the same abstract point-source/FIR model by construction. No device/route accuracy claim is possible. No physical sound-speed/absolute source-clock decomposition is inferred.

## Locked inputs and realizations

Use exactly the saved single-source joint fits for2821 and2833 from evidence/joint-reference-trial/results.json. Copy source xyz, effective speed and the full physical-parameter4×4 covariance without refitting or zeroing cross terms. Preserve the paired-timing sensitivity and original reference acceptance reports by hash; nominal covariance remains a conditional supplied assumption, not measured coverage. Use each saved single-2821-x/single-2833-x calibration as the predeclared one-reference comparator; never choose x versus y after looking at room results. Nominal calibration is the original declared source,343 m/s, source SD1 cm, physical-speed SD0.6 and source-clock SD80 ppm.

settings.json fixes a5.5×4.8×3.2 m room, twelve asymmetric noncoplanar mapping stops, four additional withheld stops, all wave settings and all numerical thresholds. Coordinates are in an exact synthetic right-handed metre frame, z upward. Mapping receiver surveys have independent isotropic3 mm errors, drawn with SeedSequence([419730,seed]); independent room audio uses[419731,seed] and direct-only audio[419732,seed]. These are not the V2 calibration RNG streams. Survey error is independent of calibration source/reference/receiver errors and recording noise; the synthetic frame has no unknown shared error. Thus source-to-mapping-receiver and source-to-mapping-audio cross covariances are zero by construction. Reusing a physical tape/frame would not establish this assumption.

Per fit, generate one16-record room and one12-record direct-only control:56 new WAVs total. The two direct-only controls reuse the corresponding mapping pose declarations and use fresh noise/clocks; this does not create fit-input correlation because neither control fits the source calibration. No new dual-source case: preserve the four existing pair-admission rejections. No geometry jitter, pose search, seed replacement, failed-stop deletion or renderer restart.

## Execution and information boundaries

`freeze` and `check` do not call waveform construction, recording processing, calibration fitting or mapping. They compile the runner, check fixed dimensions/nondegeneracy, verify the actual source/speed/probe against preserved reference metadata, verify raw hashes and check every echosight/*.py byte against the selected immutable runtime commit. Freeze also binds source renderer/helpers, settings, protocol, both x/y input sessions/calibrations/manifests/truth and48 single-source WAVs, plus the joint result and original trial freeze/protocol. Truth is read only for pre-generation source-continuity checks or post-fit evaluation, never by the calibration-selection or fitting worker.

`render --approved-freeze SHA` creates one raw tree and refuses an existing tree, even if a prior run was partial. It saves byte hashes and physical truth separately from session inputs. The sessions contain only nominal/fitted source calibration, noisy receiver surveys, probe and raw paths/hashes. They contain no room bounds, wall normals/offsets, path labels, actual positions or actual source/speed. The renderer's exact room truth never enters fitting.

`run --approved-freeze SHA` verifies frozen code and rendered artifacts, creates a run-start receipt, then launches one fresh worker per case/method with a120-second operational timeout. No runtime modifications occur. A partial failure preserves all files and blocks rerun; it is not a license for another seed. All20 workers must finish before summary reads any room truth.

The five fixed methods receive identical room bytes and supplied receiver surveys: nominal mapper; x-reference mapper; joint mapper; joint direct-plane-grid; joint first-echo baseline. `process_session` performs all raw admission/provenance checks. Nominal/x/joint use the existing mapper; grid uses the public baseline method. First-echo uses exactly the joint pipeline observations and the existing infer_first_echo comparator, with its additional processing overhead disclosed. Cross-method observation hashes must match. No candidate catalog, threshold, correction or source fit is altered.

For withheld extraction, the existing public pipeline's cancellation callback becomes true when observation progress reaches0.65, after the fourth recording. That existing boundary prevents inference. The retained artifact must say cancelled, contain all four observations, and contain no surface. Only those observation rows enter the prospective prediction check; a cancelled artifact is not presented as a completed map. This reuses existing admission policy without creating a second importer or fitting held audio. The four withheld poses never enter map fitting or source fitting.

The current code freeze includes all echosight/*.py hashes. A later runtime change, even in a source-diversity module unused here, invalidates this freeze and requires inspection before a new freeze. No post-freeze arithmetic change is permitted within the same experiment.

## Acceptance and comparison

Both joint mapper room cases must recover six one-to-one matched planes including floor and ceiling, with zero unmatched definitive planes. Match angle≤5 degrees and perpendicular distance≤0.10 m at the center of each true wall, using maximum valid matching cardinality before error minimization. Report historical origin-offset0.15 m scoring separately; it cannot rescue anchored-gate failure. No support hull is a physical edge or proof of closure. All twelve raw mapping observations must be accepted; each direct-only control must also accept all twelve recordings and produce zero definitive planes. Processing rejection cannot count as successful null discrimination.

All six inferred surfaces are predicted at all four withheld receiver surveys,24 paths total. A candidate is eligible only within the fixed±200 µs prediction window and must be unmerged. Exactly one accepted candidate per prediction is required. If one candidate would serve more than one surface prediction, those validations are ambiguous. Missing/ambiguous/reused candidates remain explicit and block the withheld gate; no nearest-candidate rescue or reduced favorable denominator. All24 residuals must have RMS≤100 µs and maximum≤200 µs. These absolute gates do not claim calibrated confidence. Report per-path and per-surface results.

Record actual raw-to-result duration once per method. Both joint room runs must be≤10 seconds on the declared machine, excluding generation, acquisition/repositioning, withheld extraction and output serialization. Do not rerun to improve timing. Shared machine load is reported but does not convert a fail into a pass. Comparator timing scopes remain explicit.

A qualifying gain is required against BOTH nominal and preselected x-reference, in BOTH instances. Joint must pass the complete room/withheld gate, and each comparator must either fail that same complete gate, or the joint must reduce the complete24-path withheld RMS by at least one nominal sample (1/48000 second) AND reduce mean anchored error over all six matched walls by at least the declared receiver survey SD (3 mm). The latter fixed scales exclude improvements consisting only of tiny roundoff differences; they are selected before generation, not tuned afterward. No added false or missed plane is allowed. A comparator with incomplete geometry/held data has unavailable complete-error statistics; report the gate/recovery difference rather than invent errors or average only its favorable subset. Joint aggregate room recall must also exceed the first-echo baseline. Report grid tradeoffs without assuming superiority.

Transfer passes and promotion criteria are separate. If transfer passes but the required gain fails, there is no demonstrated need for a public multi-reference feature. Any joint room, null, withheld, runtime, input-integrity or benefit failure closes this bounded promotion attempt. Preserve all outputs and exact failure mechanism; no new seeds, noise changes, uncertainty inflation, gate relaxation or production interface follows. A pass requires fresh independent review and a coordinator decision before integration, and does not supersede failed harder/measured suites or establish hardware accuracy.

## Artifacts and commands

Prepared artifacts are settings.json, run.py, this protocol, static-check.json and freeze.json. The one-time approved stages are:

```
.venv/bin/python work/calibration-room-transfer/run.py render --approved-freeze EXACT_REVIEWED_SHA
.venv/bin/python work/calibration-room-transfer/run.py run --approved-freeze EXACT_REVIEWED_SHA
```

No command above has run during preparation. Future raw/, fits/, render-start.json, render-complete.json, run-start.json and results.json must not exist at the planning handoff. Review settings/source continuity, uncertainty independence, all gates, truth boundary and refusal behavior before approving generation.
