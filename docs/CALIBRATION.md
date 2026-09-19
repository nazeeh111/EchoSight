# Empirical source and effective-speed calibration

This utility evaluates a **calibration proposal** from original recordings near one independently surveyed planar reference. It estimates an effective source center and propagation speed per source-buffer second. It does not infer that reference plane, certify a physical device, separate sound speed from source clock rate, or guarantee the same source model at every bearing/band. The known reference geometry is calibration input and must never be passed off as acoustically recovered room structure.

Use the existing acquisition contract and preserve all raw files. Before processing, partition at least eight noncoplanar training stops and four spatially distinct held-out stops. Survey the source's mechanical position, receiver acoustic centers and the reference plane, including uncertainty. The default source search is within15cm of the nominal source and effective-speed search300–380m per source-buffer second. Those are declared bounded searches, not a claimed physical clock or temperature measurement.

```sh
python -m echosight calibrate-reference session.json reference.json --output calibration.json
```

A reference file contains:

```json
{
  "normal": [1, 0, 0],
  "offset_m": 0,
  "offset_std_m": 0.003,
  "normal_std_rad": 0.0005,
  "source_search_radius_m": 0.15,
  "effective_speed_bounds_m_s": [300, 380],
  "training_capture_ids": ["p0", "p1", "p2", "p3", "p4", "p5", "p6", "p7"],
  "validation_capture_ids": ["p8", "p9", "p10", "p11"]
}
```

The unit normal n and offset d mean n·x=d in the session frame. All training and validation positions must be mutually distinct by at least1mm, and preserved recording hashes must be distinct. Unique capture IDs alone do not establish independent measurements. Every capture must belong to exactly one partition; rejected observations are reported, never silently dropped. There must be exactly one detected echo in the physically allowed reference window at every stop. Multiple or missing candidates reject the calibration instead of choosing the one closest to the desired answer. A room with several nearby echoes may need a simpler reference arrangement. This is deliberately an isolated-reference calibration procedure, not a general echo-label oracle.

## Model, uncertainty and acceptance

For source s, reference normal n/offset d, receiver r and effective speed v=c/kappa:

`q=s+2(d−n·s)n`, `delay=(||r−q||−||r−s||)/v`.

Four unknowns are source x/y/z and log(v). Weighted least squares uses only training delays extracted from recordings. The Jacobian must have adequate rank, the fit must stay inside the declared search bounds, and the held-out stops are never refitted. The prediction variance includes candidate-local timing, direct-reference timing, relative clock-rate uncertainty and receiver survey noise. For one selected echo per recording, the timing variance is `candidate_std² + direct_std² + (delay × alpha_std/alpha)²`. A separate shared reference-plane offset/orientation sensitivity propagates into source/speed covariance without dividing the survey uncertainty by the number of recordings. The covariance is conditional and linearized; wrong path identity or dispersive hardware can invalidate it.

A proposal requires training and held-out normalized RMS≤2.5, held-out maximum normalized residual≤3.5, held-out absolute RMS≤100µs and maximum absolute residual≤200µs. These gates implement an initial calibration requirement, not measured hardware performance. Failure means preserve inputs and investigate source route/band, receiver processing, reference ambiguity or survey precision. Do not enlarge the uncertainty simply to pass.

Successful output contains `calibration.source_position_m`, `effective_speed_m_s`, and `source_effective_speed_covariance`. Matrix order is source x/y/z in metres, then effective speed in metres per source-buffer second. Source/speed cross-covariance matters. This pair replaces the mapper's separate source/sound-speed/source-clock uncertainty terms, avoiding double counting. Physical `sound_speed_m_s` remains a separate declared quantity. No fictitious absolute source-clock estimate is emitted.

The utility does not alter a session. After inspecting its evidence and source-route applicability, a local client can apply the three calibration fields together through the version-checked calibration PATCH contract. Reprocessing uses preserved raw bytes. Do not combine a fitted source center with the old independent covariance or drop its speed correlation.

## Current evidence boundary

A development raw-WAV experiment with a7cm source shift and actual combined speed346m/source-buffer-second reduced four held-out delay residual RMS from247µs to about0.91µs; the fitted source error was0.72mm. This is simulation, with surveyed reference truth explicitly supplied, not physical accuracy. Tests reject spatially degenerate or reused validation positions, missing uncertainty/invalid partitions, and a held-out path-delay shift. Shared survey uncertainty increases the output covariance. General multipath reference selection and actual hardware qualification remain open.

Reproduce the development example with `python -m evaluation.calibration_development --output work/calibration-demo`, then run the CLI on its `session.json` and `reference.json`. Separate `truth.json` is evaluation-only.

## Inspectable artifact contract

The CLI emits the [calibration result v1.1 schema](../schemas/calibration-result.schema.json) for both proposals and processing/model rejections. The [reference input schema](../schemas/calibration-reference.schema.json) describes the supplied reference v1.0 contract. Structurally invalid sessions/reference geometry still raise an input error; they are not fitted or converted into a calibration proposal.

`calibration_input.reference` preserves the supplied plane, survey uncertainties, partitions and materialized search defaults. `calibration_input.acquisition` preserves the consumed source/receiver poses and uncertainties, coordinate frame, clock/speed declaration and probe configuration. It excludes recording paths and unknown annotations. If supplied, each capture's `sha256` is the expected checksum used for admission, not a claim that the file was verified. It must be a lowercase 64-character hexadecimal digest or null (no assertion); malformed checksum declarations raise an input error without copying their contents. Missing and empty probe declarations remain distinguishable; malformed declared probe values remain inspectable on rejected outputs. The signal processor remains responsible for validating them.

`recording_inputs` reports every declared capture, including failures:

- `verified`: `sha256` is the original file-byte digest returned by recording processing. This establishes byte identity, not physical independence or measurement accuracy.
- `not_processed`: no observation was produced, such as spatial rejection before decoding or a missing/empty probe. Its digest is null.
- `not_available`: processing produced a rejected observation without an exposed verified digest, such as an unreadable file, checksum mismatch or malformed probe. Its digest is null. This does not assert that the file was never opened.

`input_id` binds the canonical supplied inputs and these per-recording states/digests. Numeric spelling and signed zero are normalized. Different failed declarations have different identities, but an unavailable digest cannot bind unidentified raw bytes. `calibration_id`, present only on proposals, also binds the fitted calibration and implementation fingerprints. `input_result_id` identifies the underlying recording pipeline result when available; it is null for early rejection. That older pipeline identifier can change when omitted probe defaults are explicitly materialized, while the canonical calibration input identity and replayed fit remain equal.

To replay, copy `calibration_input.acquisition`, restore each original local recording path by capture ID, verify any available digest, and call `calibrate_reference` with `calibration_input.reference`. Across numerical installations, fitting can differ by floating-point roundoff; compare fitted values numerically and preserve the original artifact hash rather than expecting identical `calibration_id` values. The canonical supplied-input identity is separate. A result artifact alone does not contain audio. Never invent a digest for an unavailable file. Error diagnostics retain upstream codes and capture IDs; raw exception messages are excluded because they can contain local file paths. Rejected outputs cannot contain an applicable `calibration` or `calibration_id`.

[Executed proposal and rejection examples](../evidence/calibration-contract/README.md) cover a proposal, held-out model failure, planar receiver rejection, missing probe and malformed probe. They use the existing development simulation fixture, with exact raw-WAV hashes in the report. They provide software contract evidence only. Regenerate and validate them with:

```sh
.venv/bin/python evidence/calibration-contract/reproduce.py --output work/calibration-contract-replay
.venv/bin/python -m unittest tests.test_calibration_contract tests.test_calibration tests.test_mapping_admission_cancellation.ReferenceCalibrationAdmissionTests -v
```
