# Software integration closure, e372158

Bounded conclusion: no new material software defect established. No runtime change is justified by this lane. This is not full-charter completion, a new scientific review, or measured-device qualification.

## Scope and observations

Read the active state, charter/addendum, 43-requirement coverage, API and frontend contracts, then traced live `echosight/storage.py`, `api.py`, `cli.py` and their integration tests. The connected software obligations are implemented: raw import; processing with progress and explicit no-result states; revision-pinned calibration/pose correction; immutable per-job results; stale-session-result signaling; archive quarantine and replay; versioned frontend geometry/evidence and comparison continuity. Existing suite evidence already covers cancellation, source admission and calibration contracts; this lane did not repeat those reviews.

Exact inspected runtime HEAD: `e372158d9daa47891b0c5f7106b224b0aca75d05`. The pre-existing untracked portable-review report was left untouched. All files created by this lane are under `work/integration-finish/`.

## New connected probe

`http_revision_replay.py` independently runs the following through two actual local HTTP servers:

1. Generate twelve raw synthetic room recordings, create a session, upload all original bytes and run a job. Verify six supported surfaces and completed progress.
2. Revise one receiver's declared survey uncertainty after completion. Verify revision 12 becomes 13 and the existing session result becomes stale.
3. Export the stale-result/current-input combination. Check all twelve archived recording hashes against the original input bytes.
4. Import the archive through `POST /v1/imports` on another store. Verify the preserved archived result is quarantined with exactly `revision_mismatch` and `acquisition_mismatch`; GET current result returns 404.
5. Repeat the import and verify 409 without replacing the session, then run a new job. Verify revision 13, all original recording hashes, six surfaces and `stale=false`. Verify the original store's per-job result remains unchanged.

Run: `.venv/bin/python work/integration-finish/http_revision_replay.py`.

Result: **passed**, exit 0. Machine-readable output: `http_revision_replay.json`; stderr is empty. Initial sandbox execution could not bind the local listener. A native scoped escalation was approved and the same probe then ran, with no external network traffic.

## Coverage and remaining limits

- Recording-to-API/CLI/revision/export and frontend integration are supported by the live paths and existing `tests/test_end_to_end_api.py`, `test_cli.py`, `test_frontend.py`, `test_schemas.py`, `test_tracking_integration.py`; the new probe adds actual HTTP reload of deliberately stale archived computation followed by revision-correct processing.
- The CLI export path reprocesses preserved recordings; replay quarantines imported computation. Browser integration deliberately requires a local proxy or separate allowed-origin/authentication design, as documented; a browser viewer is not supplied by this backend.
- The six-surface check is synthetic software evidence. Harder synthetic recovery failures, external measured-data failures, source-model ambiguity and all own-device qualification remain exactly as recorded in STATE/COVERAGE. Physics specialists own current investigation of those failures.
- No false-color/material/appearance/adjudication placeholder was introduced. No runtime edits, committed changes, pushes, dependency installation or scientific-method tuning occurred.

The remaining identified limitations in this bounded lane are declared product/research constraints, not newly reproduced tractable integration defects. A complete final assembled verification still belongs to the coordinator at its final runtime commit.

## Archived replay

From the repository root, run `.venv/bin/python evidence/http-revision-replay-e372158/http_revision_replay.py`. The script uses temporary stores and prints its result; local loopback permission may be required. The saved JSON records the original execution at e372158.
