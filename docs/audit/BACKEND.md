# Backend/acquisition integrity audit

Scope: recording import, raw preservation, session evolution, HTTP contracts, cancellation, restart and replay. Grounding: charter read in full; audited starting commit `1c77336` plus the changes identified below. This is a backend specialist audit, not an independent review of the inverse mathematics or proof of iPhone performance. Source data, calibration and provenance declarations remain caller supplied.

## Executed findings and fixes

| Charter requirement | Before audit / reproduced failure | Implemented behavior | Executed evidence |
| --- | --- | --- | --- |
| Lossless import and trustworthy provenance | Import decoded a path, then reread it for hashing/preservation. Mutating source after decoding produced stored 44.1 kHz audio with 48 kHz metadata. | A bounded immutable byte snapshot supplies decoder, hash and preserved file. Change detected during reading rejects import. Existing corrupt content-addressed files are not silently reused. | `tests/test_storage.py::test_import_uses_same_bytes_for_decode_hash_and_preservation` failed before fix, passes after. `read_recording_snapshot` supplies consistent samples/rate/hash to orchestration. |
| Do not invent sample continuity | An empty row between phyphox audio values was silently discarded, reducing elapsed sample time. | Reject explicit interior sample gaps; original ZIP remains unchanged. Trailing empty CSV rows carry no sample values. Timestamp-free continuity is still unverified. | `test_phyphox_never_closes_an_explicit_sample_gap` failed before fix, passes after. Existing inconsistent-rate/nonfinite tests pass. |
| Cancellation and partial/recovery states | A cancellation accepted between result return and publication could still publish a completed result. | Recheck cancellation while holding the publication lock. Accepted cancellation before publication wins; cancellation after publication leaves a completed job complete. | `test_cancel_before_publication_wins_over_completed_result` deterministically reproduced failure, passes after; actual HTTP cancellation test also covers no published result. |
| Recovery and retry | Session metadata write failure left an empty directory that permanently reserved the requested session ID. | Publish newly created sessions by atomic directory rename only after metadata succeeds; failed staging is disposable and removed. | `test_failed_session_creation_does_not_reserve_identifier` reproduced failure, passes after. |
| Correct missing/changed calibration while keeping raw data | API had no route to revise calibration or receiver poses, requiring another session and re-upload. | Version-checked calibration/pose update preserves recording IDs, hashes and raw files, saves prior session metadata locally, increments revision and invalidates old results. | `test_calibration_revision_preserves_raw_and_prior_input`, actual HTTP revision-conflict and concurrent-job tests. |
| Replay never promotes unverified claims | Previously fixed archive trust issue remains relevant to charter. | Imported computations are quarantined even if their metadata matches. Original bytes and unsupported claims are preserved for audit; only recomputation publishes a current result. | `test_foreign_archived_geometry_is_quarantined_until_recomputed`; actual acoustic API/export/recompute test verifies matching session/evidence has no binding issues, yet still requires recomputation. |

## Coverage matrix and remaining limits

| Area | Code / executed evidence | Result and limitation |
| --- | --- | --- |
| Integer PCM decoding, nominal rates and raw retention | `echosight/storage.py` `_read_wav`, `_recording_bytes`, `import_recording`; `test_pcm_widths_and_rates_preserve_signed_samples` spans 8/16/24/32-bit and 8/44.1/48/96/192 kHz, exact signed endpoints and byte equality. | Storage support is verified. This does not qualify source hardware or establish actual physical sample rate. Signals impose their own usable frequency-band requirements. |
| Phyphox CSV ZIP | `_read_phyphox`, `test_phyphox_zip_preserves_decimal_values_and_source`, inconsistent-rate/nonfinite/gap tests. | Exact decimal sample parse, byte preservation and bounded ZIP expansion verified for declared columns. Actual iPhone export, append continuity, OS processing and dropped buffers remain hardware acceptance. |
| Import diagnostics reaching geometry | Current `pipeline.py` carries `input_diagnostics` and `format`; pipeline regression asserts `sample_grid_unverified`. | Confirmed current implementation after initially incomplete inspection; no change was needed here. An import diagnostic is not calibrated physical uncertainty. |
| Interrupted HTTP upload | `api.py` bounded body read; `test_interrupted_upload_does_not_publish_capture` closes write side before declared body completion, then retries a valid WAV. | 400, no capture published; retry succeeds. No app-level chunked/resumable uploads. Whole recording can be resent safely with a new capture ID, or same ID if prior upload never committed. |
| Concurrent acquisition / inference | `SessionStore.start_job`, `add_recording`, `update_calibration`; `test_concurrent_upload_and_calibration_do_not_change_running_input`. | Running job retains old input; later upload/calibration yields `stale=true`; next job consumes new state. Duplicate active jobs for same session return 409. |
| Cancellation | Store and real HTTP tests. | Cooperative, not forceful. It waits for the current bounded numerical operation; no promise of instantaneous cancellation. |
| Restart ownership / recovery | POSIX file lock and persistent jobs; subprocess ownership test; interrupted-job recovery test. | macOS/Linux process ownership verified; unfinished jobs marked interrupted and can be rerun. Hardware power-loss durability beyond filesystem guarantees is not established. |
| Resource boundaries | Recording/session/result/archive limits in storage; HTTP declared-body limits; archive corruption, expansion, traversal, oversized-result, result-shape tests. | Bounded processing and upload concurrency. Retained sessions/jobs remain user-managed; no automatic global disk quota or deletion. |
| Frontend identities / coordinates | Versioned sessions, captures, jobs; optimistic revision check; result schema/integration owned by coordinator. | Explicit right-handed metre coordinates with z up. Supplied coordinate-frame identity is a user assertion, not inferred registration. Matching surfaces across views uses comparison logic, not globally guaranteed geometry IDs. |
| Controlled scene change | `evolution.py` currently describes changed support and retains `physical_scene_change_established=false`. | This audit does not establish causal scene-change detection. Missing echoes do not prove removal. Coordinator owns further controlled-comparison work. |
| Real recording to geometry | `tests/test_end_to_end_api.py`: 12 simulated recording uploads initially return missing-calibration/no-result; PATCH adds the source pose without re-upload, then six surfaces including height are recovered, exported, quarantined and recomputed identically. | Genuine processing of synthetic WAV input, not an iPhone measurement. Geometry evaluation and measured external-data performance are separate evidence. |

## Added API contract

`PATCH /v1/sessions/{session_id}` accepts:

```json
{
  "expected_revision": 2,
  "calibration": {"source_position_m": [1, 1, 1.2], "sound_speed_m_s": 344},
  "captures": [{"capture_id": "phone_1", "receiver_position_m": [2, 1, 1.7], "receiver_position_std_m": 0.02}]
}
```

`expected_revision` is required. Mismatched revision returns 409; invalid values/unknown keys return 400. Calibration accepts source pose/uncertainty, sound speed/uncertainty, source clock scale/uncertainty, probe metadata and coordinate-frame ID. Capture updates accept only an existing ID and receiver pose/uncertainty. Recording bytes, hash, provenance and IDs cannot be patched. A successful no-op does not create a revision. Prior calibration snapshots stay in the local store; current export contains current metadata and raw recordings, not the full local revision history. Existing active jobs retain their own prior input snapshot; completed results become stale until reprocessed.

## Repeatable checks

```sh
.venv/bin/python -m unittest discover -s tests -p test_storage.py
.venv/bin/python -m unittest discover -s tests -p 'test_*api.py'
```

At this audit checkpoint: 22 storage tests and 9 actual HTTP/API/end-to-end tests pass; the latter complete in 6.824 s on this host. These are targeted audit checks, not a final whole-project pass.

HTTP tests require the native permission boundary to allow an ephemeral loopback listener. These tests send no external traffic. Coordinator performs the final integrated run against the final commit; this audit does not replace that gate.
