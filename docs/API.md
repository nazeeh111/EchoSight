# Local backend API v1

Run `echosight serve --root ./data --host 127.0.0.1 --port 8765` (see CLI help for current command options). The service binds only loopback, has no account system, and is intended for one trusted local user. One running process owns a store. Do not expose it through a public proxy. JSON uses schema version `1.0`; positions are right-handed metres, z up; durations are seconds; sample rates are Hz. See CONTRACT.md and schemas/.

## HTTP routes

| Method and route | Body / response |
| --- | --- |
| GET `/v1/health` | health/schema version |
| POST `/v1/sessions` | session JSON with empty captures; returns 201 session |
| GET `/v1/sessions/{session_id}` | session including relative raw paths and recording hashes |
| POST `/v1/sessions/{session_id}/recordings` | original mono PCM WAV or phyphox CSV ZIP bytes; `X-Capture-Metadata` header contains capture JSON; returns 201 capture |
| POST `/v1/sessions/{session_id}/jobs` | `{}`; returns 202 job |
| GET `/v1/jobs/{job_id}` | job status/progress/error |
| POST `/v1/jobs/{job_id}/cancel` | `{}`; requests cooperative cancellation; 202 current state |
| GET `/v1/sessions/{session_id}/result` | latest completed result; `stale` says whether new captures were added afterward |
| GET `/v1/sessions/{session_id}/export` | ZIP containing session, original recordings and latest result if available |
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

## Capture and raw import contract

Capture metadata accepts `capture_id`, `receiver_position_m`, `receiver_position_std_m`, `provenance` (`measured`, `simulated`, `replayed`, `supplied`), and optional `device_id`/`notes`. IDs are ASCII alphanumerics, underscore or hyphen, 1–80 characters, starting alphanumeric. The store assigns missing IDs. A capture ID cannot be overwritten. Each imported recording receives SHA-256, sample rate/count/duration, byte count and format. SHA-256 hashes identify bytes, not scientific accuracy. Provenance is the caller's declaration.

PCM WAV supports mono uncompressed 8-, 16-, 24-, and 32-bit integer PCM at 8–192 kHz, positive duration at most 120 s. No downmixing, lossy decoding, normalization, or sample-rate conversion occurs in storage. Original bytes remain available and export unchanged. Float WAV, AAC/M4A and stereo are rejected with an actionable error. Raw amplitude decoding is normalized to [-1,1).

The **provisional** phyphox adapter reads a ZIP containing CSV columns named exactly `sample_value` and `reported_rate_Hz` as defined by the provided static experiment. It accepts comma/semicolon separators and quoted headers; all reported rates must agree and be integer Hz. Decimal amplitudes convert directly to float64; there is no intermediate PCM quantization. Original ZIP bytes are retained. This adapter does not claim that an iPhone has produced this exact export yet. No timestamps means sample continuity cannot be established from this format: `sample_grid_unverified` and `phone_export_not_hardware_validated` remain explicit import diagnostics. Phone qualification must check buffer continuity, export completeness and clock behavior (ACQUISITION.md). ZIP member paths are never extracted from acquisition files; traversal/encrypted files, duplicate columns, inconsistent rates and nonfinite samples are rejected.

Local Python interfaces are `validate_session(dict)`, `load_session(path)`, `read_recording(path)` and `import_recording(path,destination_dir)`. `load_session` intentionally accepts trusted local paths for CLI processing. SessionStore instead controls all uploaded raw paths. `SessionStore.import_archive` checks member limits, path confinement, checksums and decodes each recording before publishing the imported directory atomically. Reload records `replay.kind=archive_reload` without changing original measured/simulated provenance. Restored results remain archived computational outputs, not new measurements.

## Jobs, recovery and limits

Statuses are `queued`, `running`, `completed`, `failed`, `cancelled`, `interrupted`. A completed job means processing finished, even if its scientific result is `partial`, `ambiguous` or `no_result`. Progress is 0–1 with an optional message; it is not a confidence score. Cancellation is cooperative and may wait for the current bounded numerical operation. Cancelling a finished job leaves it finished. Each job persists an input session snapshot and records session revision; completed results carry the exact capture hashes used. Uploading another capture increments the session revision; the prior result remains retrievable with `stale=true`. At most one active job per session prevents out-of-order overwrite. Failed/cancelled jobs do not erase earlier results.

On restart unfinished jobs become `interrupted`; raw data and prior results survive and a new job can be started. Jobs do not silently resume with changed inputs. Session JSON, job state and results use temporary files followed by atomic rename. Export/reload does not overwrite existing sessions. Abrupt power-loss durability of the directory entry is filesystem-dependent; recovery is designed for process interruption, not a guaranteed hardware-failure transaction.

Limits: 64 MiB per recording, 120 s, 32 captures, 256 MiB total recording bytes per session, 1 MiB JSON request/session, 8 KiB capture header, two processing workers, eight unfinished jobs, and four concurrent HTTP connections (excess connections close). Archive expansion is bounded; no arbitrary extraction. Input bodies require Content-Length; socket reads time out after 15 s. Storage retention is local and user-managed; no automatic deletion. Error shape: `{"error":{"code":"invalid_request","message":"..."}}`. Statuses: 400 invalid input, 403 origin/host violation, 404 missing resource, 409 conflict/busy, 413 body limit, 500 internal error. Errors do not include stack traces.
