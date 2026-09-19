# Local backend API v1

Run `echosight serve --root ./data --host 127.0.0.1 --port 8765` (see CLI help for current command options). The service binds only loopback, has no account system, and is intended for one trusted local user. One running process owns a store, enforced by a POSIX file lock on macOS/Linux; a second opener fails before recovering jobs. The operating system releases ownership after a process crash. Do not expose it through a public proxy. Session/job/scene JSON uses schema version `1.0`; new comparisons use `1.1` (see [tracking migration](TRACKING.md)); positions are right-handed metres, z up; durations are seconds; sample rates are Hz. See CONTRACT.md and schemas/.

## HTTP routes

| Method and route | Body / response |
| --- | --- |
| GET `/v1/health` | health/schema version |
| POST `/v1/sessions` | session JSON with empty captures; returns 201 session |
| PATCH `/v1/sessions/{session_id}` | version-checked calibration/pose update; see calibration-patch schema below |
| GET `/v1/sessions/{session_id}` | session including relative raw paths and recording hashes |
| POST `/v1/sessions/{session_id}/recordings` | original mono integer PCM/IEEE Float32 WAV, native capture ZIP or phyphox CSV ZIP bytes; `X-Capture-Metadata` header contains capture JSON; returns 201 capture |
| POST `/v1/sessions/{session_id}/jobs` | `{}`; returns 202 job |
| POST `/v1/controlled-jobs` | revision-pinned four-epoch protocol; returns202 controlled job |
| GET `/v1/jobs/{job_id}/result` | immutable completed job result, including controlled protocols |
| GET `/v1/jobs/{job_id}` | job status/progress/error |
| POST `/v1/jobs/{job_id}/cancel` | `{}`; requests cooperative cancellation; 202 current state |
| GET `/v1/sessions/{session_id}/result` | latest completed result; `stale` says whether new captures were added afterward |
| GET `/v1/sessions/{session_id}/export` | ZIP containing session, original recordings and latest locally computed result, or explicitly quarantined archived computation if no current result exists |
| POST `/v1/compare` | JSON `previous` and `current` result objects; explains new/changed/unconfirmed support in a shared calibration frame |
| POST `/v1/imports` | exported ZIP bytes; atomic reload; 201 session; existing session ID is a 409 conflict |

Example:

```sh
curl -s http://127.0.0.1:8765/v1/sessions -H 'Content-Type: application/json' \
  -d '{"source_position_m":[1,1,1],"probe":{}}'
# Use the returned session_id in subsequent requests.
curl -s http://127.0.0.1:8765/v1/sessions/SESSION_ID/recordings \
  -H 'X-Capture-Metadata: {"capture_id":"phone_1","receiver_position_m":[2,1,1.7],"provenance":"measured"}' \
  --data-binary @phone.wav
curl -s http://127.0.0.1:8765/v1/sessions/SESSION_ID/jobs -d '{}'
```

Populate `probe` with the generated probe metadata before recording: `{}` is only a syntactic session example, not valid acquisition calibration. Source and receiver positions denote acoustic centers. Pose uncertainty defaults to 1 cm; users must replace it when survey uncertainty is larger. A missing pose stays missing for processing diagnostics. HTTP requests cannot reference arbitrary filesystem paths. Browser Origin requests are rejected; a later same-machine frontend needs an explicit authenticated/allowed-origin integration design, or a trusted local server-side proxy. The API itself supplies no frontend.

## Correct calibration and reprocess preserved recordings

`PATCH /v1/sessions/{session_id}` follows `schemas/calibration-patch.schema.json`:

```json
{"expected_revision": 2, "calibration": {"source_position_m": [1,1,1.2], "sound_speed_m_s": 344}, "captures": [{"capture_id": "phone_1", "receiver_position_m": [2,1,1.7], "receiver_position_std_m": 0.02}]}
```

A stale expected revision returns 409; reload before revising. Calibration accepts source pose/uncertainty, sound speed/uncertainty, source clock scale/uncertainty, probe metadata and coordinate-frame ID. Capture updates accept existing IDs and receiver pose/uncertainty only. Recording bytes, hashes, IDs and source provenance stay immutable. Invalid fields return 400; a successful no-op leaves revision unchanged. A changed revision makes old results stale; submit another job to reprocess. Active jobs retain their earlier snapshots. Prior calibration is saved locally under session `revisions/`; current session exports include current metadata and raw recordings, not the full local revision history. Null source/receiver poses explicitly denote missing calibration and produce diagnostics until corrected.

## Capture and raw import contract

Capture metadata accepts `capture_id`, `receiver_position_m`, `receiver_position_std_m`, `provenance` (`measured`, `simulated`, `replayed`, `supplied`), and optional `device_id`/`receiver_pose_group_id`/`notes`. IDs are ASCII alphanumerics, underscore or hyphen, 1–80 characters, starting alphanumeric. The store assigns missing IDs. A capture ID cannot be overwritten. Each imported recording receives SHA-256, sample rate/count/duration, byte count and format. SHA-256 hashes identify bytes, not scientific accuracy. Provenance is the caller's declaration.

PCM WAV supports mono uncompressed 8-, 16-, 24-, and 32-bit integer PCM at 8–192 kHz, positive duration at most 120 s. No downmixing, lossy decoding, normalization, or sample-rate conversion occurs in storage. A single bounded byte snapshot supplies decoding, hash and preserved bytes; detected source changes during reading reject import. Original bytes remain available and export unchanged. Mono IEEE Float32 format3 WAV is also supported: finite delivered values widen exactly to float64 without integer quantization, including signed zero and subnormals. Integer PCM amplitude decoding is normalized to [-1,1). AAC/M4A and stereo are rejected. Standalone WAV has `sample_grid_unverified`; its container cannot prove sample continuity.

The native capture ZIP adapter accepts [manifest v1](../schemas/capture-manifest.schema.json) under the [exact capture contract](../acquisition/ios/CONTRACT.md). It preserves original ZIP bytes, verifies the inner WAV SHA/format/count, checks native buffer timestamps and route/events, and returns `acquisition.processing_eligible`. This flag covers the native continuity/route contract only; the separate processor rate, duration, signal-quality and probe-band checks still apply. A well-formed interrupted package imports with diagnostics and remains exportable, but processing rejects that observation before echo fitting. Reprocessing derives eligibility again from immutable raw bytes; uploaded/archive summary metadata cannot bypass it. Native sample and host ticks are decimal strings to avoid JavaScript integer rounding. They do not calibrate physical time or the MacBook source clock. `physical_validation` remains false.

The **provisional** phyphox adapter reads a ZIP containing CSV columns named exactly `sample_value` and `reported_rate_Hz` as defined by the provided static experiment. It accepts comma/semicolon separators and quoted headers; all reported rates must agree and be integer Hz. Decimal amplitudes convert directly to float64; there is no intermediate PCM quantization. Original ZIP bytes are retained. This adapter does not claim that an iPhone has produced this exact export yet. No timestamps means sample continuity cannot be established from this format: `sample_grid_unverified` and `phone_export_not_hardware_validated` remain explicit import diagnostics. Phone qualification must check buffer continuity, export completeness and clock behavior (ACQUISITION.md). ZIP member paths are never extracted from acquisition files; traversal/encrypted files, duplicate columns, inconsistent rates, nonfinite samples and explicit interior blank sample rows are rejected. Empty rows are not silently removed from the sample clock.

Local Python interfaces are `validate_session(dict)`, `load_session(path)`, `read_recording(path)`, `read_recording_snapshot(path)`, `read_recording_evidence_snapshot(path)` and `import_recording(path,destination_dir)`. `read_recording_snapshot` returns samples, nominal sample rate and SHA-256 from exactly the same bytes. `read_recording_evidence_snapshot` adds a fourth acquisition-evidence object from that snapshot. `load_session` intentionally accepts trusted local paths for CLI processing. SessionStore instead controls all uploaded raw paths. `SessionStore.import_archive` checks member limits, path confinement, checksums, revision metadata and decodes each recording before publishing the imported directory atomically. Audio metadata is recomputed from raw bytes, not trusted from archive labels. Reload records `replay.kind=archive_reload` without changing original measured/simulated provenance. Every imported computation is quarantined as `archived-result.json`, even when its metadata matches. The import checks schema version, structural fields, session ID, revision, capture hashes/provenance and acquisition metadata; issues appear under `session.replay.archived_result.binding_issues`. Agreement does not authenticate geometry or accuracy. Imported claims of physical validation are never adopted. Original computation bytes remain preserved for audit, including unsupported claims, but are not served as a current result: GET result returns 404 until a new job completes. A new local job records `computation_origin=local_processing`; this means computed here, not hardware-validated. Original capture provenance remains the source declaration. Export before recomputation uses the explicitly named `archived-result.json`; export after recomputation includes the current `result.json`, while the quarantined original remains in the store. This separation also prevents a same-session, same-hash fabricated mesh from becoming a current result.

## Display continuity across refinements

`POST /v1/compare` also accepts optional `previous_comparison`. Its current result ID must match this request’s previous result, and its complete `current_tracks` mapping must be valid and unique. Carry this state across successive raw-result pairs to retain display track labels; no scientific result is rewritten. Stale or malformed state returns400. Missing surfaces end continuity, and calibration changes do not establish matching. See [tracking contract](TRACKING.md) and [comparison schema](../schemas/comparison.schema.json).

## Jobs, recovery and limits

Statuses are `queued`, `running`, `completed`, `failed`, `cancelled`, `interrupted`. A completed job means processing finished, even if its scientific result is `partial`, `ambiguous` or `no_result`. Progress is 0–1 with an optional message; it is not a confidence score. Cancellation is cooperative and may wait for the current bounded numerical operation. Cancelling a finished job leaves it finished. An accepted cancellation before result publication prevents publication; the publication boundary is serialized with cancellation. Each job persists an input session snapshot and records session revision; completed results carry the exact capture hashes used. Uploading another capture increments the session revision; the prior result remains retrievable with `stale=true`. At most one active job per session prevents out-of-order overwrite. Failed/cancelled jobs do not erase earlier results.

On restart unfinished jobs become `interrupted`; raw data and prior results survive and a new job can be started. Jobs do not silently resume with changed inputs. Session JSON, job state and results use temporary files followed by atomic rename. Export/reload does not overwrite existing sessions. Abrupt power-loss durability of the directory entry is filesystem-dependent; recovery is designed for process interruption, not a guaranteed hardware-failure transaction.

Import/retention limits: mono PCM or Float32,8–192kHz,64MiB per recording and120s. **Acoustic processing is narrower:16–96kHz and at most30s per recording**, with `high_hz <= 0.45 * actual_rate`. A successful upload preserves bytes and does not promise processing eligibility. An unsupported rate or duration is reported on the observation during processing; the backend never silently resamples or trims it.

Other limits:32 captures, 256 MiB total recording bytes per session, 1 MiB session/general JSON request, 32 MiB per result, 65 MiB comparison request (two full results plus envelope), 8 KiB capture header, two processing workers, eight unfinished jobs, and four concurrent HTTP connections (excess connections close). Archive expansion is bounded to 289 MiB (256 MiB raw + 1 MiB session + 32 MiB result), with at most 64 KiB additional ZIP container overhead; no arbitrary extraction. Input bodies require Content-Length; socket reads time out after 15 s. The result allowance covers 32 captures with up to 15,169 response samples each (96 kHz, 150 ms echo window, two 4 ms margins), including JSON float and indentation overhead. Oversized result persistence/import fails explicitly; the session and raw limits are unchanged. Storage retention is local and user-managed; no automatic deletion. Error shape: `{"error":{"code":"invalid_request","message":"..."}}`. Statuses: 400 invalid input, 403 origin/host violation, 404 missing resource, 409 conflict/busy, 413 body limit, 500 internal error. Errors do not include stack traces.

### Joint empirical calibration and publication durability

`calibration` PATCH may include `effective_speed_m_s` and `source_effective_speed_covariance` together, with `source_position_m`. Speed is250–460 metres per source-buffer second. The finite symmetric positive-semidefinite4×4 matrix is ordered source x/y/z and effective speed; cross terms are retained. These fields replace separate source/sound-speed/source-clock uncertainty contributions. A partial pair, null clearing or invalid covariance is rejected. [Reference calibration](CALIBRATION.md) produces a proposal from raw recordings without applying it automatically.

A completed per-job state record is the publication commit. Results from a failed/interrupted final write cannot displace the previous completed result, including after restart. Per-job result bytes are immutable; the current-result index is rebuilt from completed jobs. Archive parsing and its provenance hash use one bounded byte snapshot.


## Controlled recording comparison

`POST /v1/controlled-jobs` accepts [controlled-request schema](../schemas/controlled-request.schema.json). Create four separate sessions and upload their original recordings first. Every capture must have stable `device_id`, `receiver_pose_group_id`, capture ID and surveyed pose across epochs. Supply epochs in order `A_before`, `B_first`, `B_repeat`, `A_return`. Each epoch references a stored `session_id` and `expected_revision`, with declared `calibration_id`, `source_configuration_id` and per-device `route_ids`. The API never accepts embedded session objects or filesystem paths in this request. Changed revisions return409; malformed or changed controls return400 before work is admitted.

The job pins all four calibration/recording snapshots, shares the normal two-worker/eight-job queue and supports progress, cancellation and interrupted-state recovery. Fetch its output with `GET /v1/jobs/{job_id}/result`. It cannot replace any single-session scene result. Only completed jobs serve results, including after restart. All raw hashes and epoch/session/revision bindings are preserved. Reprocess by submitting a new revision-pinned request; export the four individual sessions to preserve their original recordings alongside the request and result. A completed protocol result is not imported as trusted geometry.

[Controlled-result schema](../schemas/controlled-result.schema.json) distinguishes repeated acoustic change from conditional spatial localization and inconclusive controls. No status certifies physical change, causality or validated hardware. Numerical gates are engineering bounds, not calibrated false-alarm probabilities. Missing echoes do not prove absence. Dense response sample arrays are omitted from nested epoch results, with exact sample count and omission metadata; geometry, paths, diagnostics and provenance are retained. Normal per-session reprocessing returns the full responses. The32MiB result bound and32captures-per-epoch limits still apply.

CLI form: `python -m echosight controlled protocol.json --output controlled-result.json`. Here each epoch uses trusted local `session` JSON paths or embedded session dictionaries instead of API references. Ctrl-C cancels cooperatively; inconclusive input/control results exit2 and retain diagnostics, cancellation exits130. [Protocol math/limitations](audit/CONTROLLED.md) and [later hardware acceptance](HARDWARE_ACCEPTANCE.md) define what the declarations and evidence mean.

## Recording independence and native controls

Imports now expose `waveform_sha256` separately from the original-container `sha256`; processed observations retain both the waveform identity and `recording_sha256`. The versioned waveform digest includes nominal rate, frame count and exact decoded mono Float64 values in little-endian order; signed zero is canonicalized only in the digest. PCM padding, exact Float32 conversion or ZIP metadata cannot turn the same sample sequence into independent evidence. All members of an exact-equivalent group are rejected before mapping, with `recording_waveform_reused` diagnostics; original files remain exportable. Multi-source raw processing groups across source sessions. Calibration and controlled protocols also check waveform identity across their independence sets. Different hashes do not prove independence; gain changes, near-duplicates and shifted copies are outside this exact check. Legacy prepared numerical/result interfaces cannot authenticate raw acquisition.

Controlled jobs return inconclusive on known contradictions in native device/recorder/input-route/active-format evidence across epochs, different known source/probe/playback declarations, mixed native-evidence coverage, or an inner source configuration conflicting with its outer epoch declaration. Receiver route IDs and source playback route IDs remain different namespaces. Legacy WAV relies on its existing operator declarations; no metadata is treated as authenticated hardware truth. Native unavailable sample/host timestamps are explicit JSON null, with false validity flags.
