# Backend integration contract v1

EchoSight uses plain JSON at public boundaries and NumPy arrays inside numerical processing. The backend is a research prototype; software execution is not physical validation. Public schemas use `schema_version: "1.0"`. See [HTTP endpoints and limits](API.md), [frontend handoff](FRONTEND_HANDOFF.md), and [schemas](../schemas/).

## Physical conventions

Coordinates are right-handed metres, z up; a plane is `normal · x = offset_m` with unit normal. Surveyed source/receiver acoustic centers are supplied calibration, not inferred structure. Source clock scale `kappa` is actual/nominal source sample rate. Corrected excess source-buffer delay is `(reflected_length - direct_length) / (c/kappa)`. Relative recorder clock correction does not separately identify physical sound speed and absolute source rate. Never halve bistatic excess delay.

A calibrated `effective_speed_m_s` and full joint `source_effective_speed_covariance` replace the separate source-position, sound-speed and source-clock budgets for the same nuisance variables; do not add both budgets. Cross terms and reused receiver survey groups matter. See [calibration](CALIBRATION.md) and [inference equations](INFERENCE.md). Conditional uncertainty does not cover every wrong propagation model, echo selection error or unreported transducer bias.

## Supported entry points

| Interface | Purpose and authoritative details |
|---|---|
| `echosight.pipeline.process_session(session_or_path, cancel=None, progress=None)` | Recording input to JSON spatial result; resolves calibration, validates original evidence, estimates responses and infers conditional geometry. [CLI and setup](../README.md). |
| `echosight.signals.generate_probe(config=None)` | Returns mono samples and a hash-bound probe description. Source playback uses one continuous buffer. [Acquisition](ACQUISITION.md). |
| `echosight.signals.process_recording(...)` | Returns clock diagnostics, response and unlabeled echo candidates. Reduced candidates alone are not independent physical evidence. [Signal model](SIGNAL_MODEL.md). |
| `echosight.storage.read_recording_evidence_snapshot(path)` | Returns decoded samples, actual rate, original-byte SHA256 and recomputed acquisition evidence from one snapshot. Import preserves original bytes. [Native capture contract](../acquisition/ios/CONTRACT.md). |
| `echosight.storage.import_recording(path, destination_dir)` | Preserves lossless WAV/native ZIP/provisional phyphox input and returns manifest metadata. Import limits differ from processing limits. [HTTP/import contract](API.md). |
| `echosight.storage.SessionStore(root)` | Session revisions, immutable recordings, queued jobs, cancellation, interrupted-job recovery and export/reload. Stored replay computations are quarantined until recomputed. [API](API.md). |
| `echosight.calibration` | Isolated known-reference source/effective-speed calibration with independent held positions. [Protocol and outputs](CALIBRATION.md). |
| `echosight.controlled.process_controlled_protocol(...)` | Four-epoch A-before/B-first/B-repeat/A-return raw-recording comparison. [Controlled contract](audit/CONTROLLED.md). |
| `echosight.evolution.compare_results(previous, current, ...)` | Bounded one-to-one display association between compatible calibrated results. [Frontend continuity](FRONTEND_HANDOFF.md). |

Sessions/captures carry stable IDs, probe, surveyed poses and their declared uncertainty, original recording references and provenance. Missing poses or calibration produce diagnostics. Exact decoded waveform copies cannot count as independent captures even when container bytes differ; every member of a reused-waveform group is withheld. Different hashes do not prove physical independence or trustworthy metadata.

Results distinguish `ok`, `partial`, `ambiguous`, `no_result` and `cancelled`. Each surface's `surface_id` is deterministic for its supporting evidence and can change as that evidence changes. `normal`, `offset_m`, supporting capture/candidate references, residuals and uncertainty explain its conditional inference. Renderable support vertices/triangles have unknown physical extent: they do not establish edges, a closed room, empty space or safety. See [frontend output examples](../examples/frontend/).

The experimental multi-source and competing-path routines remain research interfaces, separate from the public per-session processing route. Their frozen failures and promotion limits are in [coverage](audit/COVERAGE.md). Evaluation truth and model-generated labels must stay outside fitting. Simulated recordings, hybrid replay of measured responses, supplied calibration and our future device measurements remain separate evidence classes.
