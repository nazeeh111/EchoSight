# Independent backend integrity checkpoint review

Reviewed commit: **`25c20f7162cedca449a2e3f226f61a50553d11af`**.
Comparison baseline: **`6f50be0`**, separately unpacked for reproducing findings.

**Two residual P2 findings are reproduced below. Both also reproduce on the comparison baseline; neither is attributed to the new patch.** The new calibration revision, raw-recording snapshot and cancellation-lock changes passed the scoped checks described below. No P1 finding was established.

This is a storage/API/integration checkpoint review, **not final backend acceptance**. I read the original charter, continued-work addendum and `docs/audit/COVERAGE.md`. The project remains a research prototype with active scientific capability gaps. This review does not close those gaps or validate physical iPhone/MacBook accuracy.

## Independence and inspected scope

I unpacked the reviewed commit through `git archive` into `work/review-25c20f7-snapshot` and imported only from that immutable snapshot. A second immutable archive, `work/review-6f50be0-snapshot`, supplied the prior-version comparisons. Uncommitted physical-model changes and the new calibration module in the shared checkout were excluded. No implementation/test/schema/documentation changes or commits were made by the reviewer.

I inspected the diff and assembled `echosight/storage.py`, `api.py` and `pipeline.py`, including unchanged surrounding recovery/archive code; the changed tests and calibration/session schemas; and API, audit and coverage claims. The numerical inverse solver and active scientific changes were not re-reviewed. Snapshot hashes bind decoded audio samples and metadata but do not validate caller-declared calibration or physical provenance.

## P2: A failed or interrupted publication can replace the latest completed result

**Location:** `echosight/storage.py:459–463`, with exposure at `477–483` and restart recovery in `SessionStore.__init__`.

The worker writes its job result and the session's public `result.json` before persisting the job's terminal `completed` state. If the final state write fails, the exception handler records `failed`, but the new session result remains visible. If the process terminates at that boundary, restart labels the job `interrupted`, yet still serves its result as current. `get_result` checks only the session revision, not the result's job state or a committed publication record.

**Independent reproductions:**

1. Complete an initial job with marker `previous_completed`. Inject an `OSError` only when the subsequent job tries to persist its `completed` state. The second job becomes `failed`, while `get_result` returns its marker `new_failed_job` and `stale:false`. Closing and reopening the store preserves this contradiction.
2. Repeat in a separate process, terminating it with `os._exit(17)` precisely before the second completed-state write. The parent reopens the store. The served result has marker `interrupted_uncommitted` and `stale:false`, while its referenced job has `status:interrupted` and a restart diagnostic.

Artifacts:

- `work/review-25c20f7-probes.py` and `.json`.
- `work/review-6f50be0-probes.json`, which confirms the injected-write failure also exists in the prior version.
- `work/review-25c20f7-crash-probe.py` and `.json`, which demonstrate actual process termination and restart in the reviewed version.

**Requirement implication:** the API promises the latest completed result; failed/cancelled jobs are documented not to displace earlier results, and process-interruption recovery should be coherent. A client can currently receive a current result from a job it was told failed or must rerun. The earlier result's job-specific file still survives, so this is not total raw-data or result-file loss; it is incorrect latest-result publication and recovery.

**Repair direction:** make one durable record authoritative for completed publication, or recover/roll back incomplete publication to the last completed job. Reading and exporting must agree with that authority after both write errors and process interruption. Simply checking job status and returning no result would still unnecessarily hide the earlier completed result. Add a fault-injection/process-restart regression at this exact boundary, while retaining the repaired accepted-cancellation behavior.

## P2: Archive hash can describe different bytes from the imported archive

**Location:** `echosight/storage.py:506–510` and **540**.

Raw recording import now uses one bounded byte snapshot, but the enclosing archive import does not. `ZipFile(path)` reads one open file, while `archive_sha256` is computed later by reopening `path.read_bytes()`. If the pathname is atomically replaced during import, the open ZIP continues loading the original inode but the recorded hash describes the replacement archive. The final path reread is also outside the initial size check.

**Independent reproduction:** create `original_archive` containing one recording and a separate empty `replacement_archive`. After the raw recording has been decoded during `import_archive`, atomically replace the source archive pathname with the second archive. Import succeeds with `session_id:original_archive` and one capture, yet its recorded `archive_sha256` equals the empty replacement archive's hash rather than the imported archive's hash. Both SHA values and loaded identity are preserved in the probe output. The same probe reproduces on `6f50be0`.

Artifacts: `work/review-25c20f7-probes.py`, `work/review-25c20f7-probes.json`, and `work/review-6f50be0-probes.json`.

**Actual scope:** local `SessionStore.import_archive` and CLI replay of a concurrently replaced source archive. The HTTP route first creates a private temporary upload file, so this probe is not evidence of a remote attack through an ordinary HTTP upload. Per-recording hashes still agree with the loaded recordings; the incorrect field is the enclosing archive provenance. No large resource allocation was used in the reproduction.

**Requirement implication:** retained provenance must identify the bytes that were actually replayed. The recording snapshot fix should extend consistently to this archive boundary.

**Repair direction:** parse and hash one bounded immutable archive snapshot, or otherwise guarantee hashing the same stable bytes with mutation checks. Do not reopen an unbounded pathname after parsing. Keep current member/expanded-size checks and quarantine semantics.

## Passed independent checks

**43 targeted tests passed**, executed against the immutable reviewed snapshot:

| Test group | Count | Result |
|---|---:|---|
| Storage | 22 | Passed |
| Pipeline | 5 | Passed |
| Evolution | 7 | Passed |
| HTTP/API and actual recording end-to-end | 9 | Passed in 7.100 s |

HTTP tests ran with native approval for temporary loopback listeners. They cover interrupted upload returning an error without publishing a capture, valid retry, stale revision conflicts, concurrent upload/calibration while a job retains prior input, cooperative cancellation without publication, and synthetic recordings uploaded before calibration, corrected through PATCH, then processed/exported/recomputed. These are executed software checks, not device measurements.

Additional reviewer-written probes, separate from the builder's tests, are in `work/review-25c20f7-positive-probes.py` and `.json`:

- Changed the source WAV after decoding a captured byte snapshot but before orchestration completed. The observation and result recording hashes continued to identify the exact bytes decoded, not the changed path. The expected original checksum matched.
- Mutated a WAV after its read returned but before the post-read file-stat check. `read_recording_snapshot` rejected it as changed during reading.
- Issued two concurrent calibration updates against the same revision. Exactly one succeeded and the other reported a conflict; the revision advanced once.
- Confirmed a true no-op preserved the revision and an attempted provenance change was rejected without changing state.
- Injected a session metadata write failure during calibration update. The prior published session/revision and raw bytes remained unchanged; a later retry remained possible.
- Set the source pose to null through the supported update path. It became missing calibration rather than invented geometry, while raw recording bytes remained unchanged.

The reviewed locking and copying preserve old job inputs while calibration and later captures create a new revision. The publication lock now rechecks cancellation before publishing, addressing the earlier cancellation race; the residual completion-state issue above is a different boundary. Schema inspection found the documented PATCH allowlist, expected revision, bounded capture updates and null-pose semantics aligned with runtime validation. Probe field contents continue to be validated by signal processing rather than fully at PATCH time, as explicitly documented.

Resource tests cover the ordinary file/session/result budgets, maximum response-shaped result persistence, over-limit result rejection, archive members/path/checksum constraints, and PCM/CSV decoding. These checks do not establish a global disk quota; retained local data remain user-managed as documented. The archive reread issue above is a remaining resource/provenance boundary, not a reason to discard the passed checks.

## Status and limits

The two findings require scoped repair and follow-up verification. The other examined checkpoint changes are supported by direct execution. This review neither reran the complete frozen scientific evaluations nor inspected in-progress physical-model/calibration changes; those need their own integration checks once committed.

`docs/audit/COVERAGE.md` correctly treats scientific capability, simulation evidence, external measured replay and own-device validation separately. Updating its recording/calibration/cancellation rows can cite the passed checks here, but recovery and archive provenance should retain the two unresolved findings until repaired. Passing this bounded review's tests must not be presented as full-charter completion.
