# Local recording workspace

Install the backend with Python 3.12 on macOS or Linux, then run:

```sh
python -m echosight serve --root work/store --ui
```

Open the printed `/ui/results.html` address. Keep this server running while jobs process. Omit `--ui` to retain the native-client-only API. Serving `demo/results.html` with the separate demo server remains a file-only result inspector.

## Original recordings and calibration

Load a session definition JSON or edit its calibration JSON and create a session. A definition's capture entries become a separate upload plan; computed/unsupported top-level fields are omitted and reported. Inspect the plan before selecting the corresponding original WAV or native/phyphox ZIP files. Each capture needs a unique `capture_id`, `recording_path` matching a selected basename, explicit `provenance` (`measured`, `simulated`, `replayed` or `supplied`), and any surveyed receiver pose and uncertainty. The UI never reads a server path from a definition. Provenance is a supplied declaration, not an authenticity certification.

Select exactly the listed files, then import. SHA-256 binds metadata/checksums to the actual copied recording bytes. Imports are sequential: if a later file fails, earlier originals remain stored. Retry the same batch to verify/skip identical existing recordings. Different bytes or supplied metadata for an existing capture ID cause an error; original recordings cannot be overwritten. Use a revision-checked calibration patch to update surveyed calibration. Device IDs and notes cannot be silently changed through reimport.

Limits: 32 captures, 64 MiB per recording, 256 MiB selected recording total, 8 KiB ASCII-encoded capture headers, and 1 MiB metadata JSON. ZIP decoding and stored session limits remain enforced by the backend. Archive limits appear in the backend configuration and remain bounded by the store. Missing probe/calibration is retained, not invented; it may lead to a diagnostic `no_result`.

## Processing and recovery

Process the selected session. The backend freezes its input revision. Progress means work completed, not confidence. A per-session request identity is retained before sending the start request. If its reply is lost, use **Recover processing start**; this retries the same identity and cannot launch the same accepted request twice, including after restart. The URL fragment contains only session/job/request IDs, so retaining the address lets you restore observation. No action is automatically posted from a saved fragment.

If status retrieval fails, state remains unknown and new mutations stay locked. **Retry job status** observes the same job. Closing/reloading the page stops observation, not processing. **Request cancellation** asks the backend to stop; wait for a terminal state. Cancelled/failed/interrupted jobs publish no new successful result. Previous inspected output remains available. Restarted backend processes mark unfinished jobs interrupted; process again explicitly with a new request when ready.

If a saved session or job cannot be restored, **Retry saved workspace** repeats the original lookups. The original session/job/request address is kept and processing/import/calibration controls stay locked until those exact identities and a recognized job status are verified. Restoration never starts or cancels processing automatically. Wrong-job or cross-session replies are rejected. If the saved address itself names a nonexistent job or the wrong store, correct the address/store and reload rather than starting another job under an unknown state.

Completion reads the exact immutable job result and compares its revision with the current session. A newer manually selected result/example remains visible; **View completed job result** opens the job explicitly. Changed calibration marks earlier results stale and requires processing again. Conflicting patch revisions refresh metadata and preserve the edited patch text; inspect it before explicitly replacing its expected revision.

**Export raw archive** downloads retained originals and metadata. Imported archives never overwrite an existing session ID; archived computations remain quarantined and need recomputation. Keep source definitions and original recordings as well as exports.

## Compare successive results

With a result displayed, choose **Keep displayed result as previous**. Open another result JSON or process more recordings, then choose **Compare with displayed result**. This explicitly sends both complete result objects to this same loopback backend's existing comparison API. It does not modify either result, its recordings or the stored session. Named result IDs are required; cancelled results cannot be selected. The standalone file viewer does not expose comparison controls.

The report shows corresponding patches, newly supported patches, previously supported patches now unconfirmed, normal changes in degrees, signed offset changes in millimetres at the shared source reference, and additional/previously unretained recording support. Missing session identity makes recording-support comparison unavailable. Changed/missing calibration or coordinate frame produces an incomparable report. Stale snapshots are labelled. Display continuity thresholds are not significance tests or evidence that an object moved/disappeared; a missing echo does not establish absence.

**Download comparison JSON** retains exact backend track labels and scoped evidence references. After a successful comparison, keeping its displayed current result as previous carries those display labels into the next comparison. The snapshots and carry state live only in page memory and are cleared on reload; use the CLI with `--previous-comparison` for saved multi-step chains. Opening a different accepted result cancels/invalidates a pending report so a late response cannot be attributed to the new scene. Failed requests keep both snapshots available for retry.

## Local boundary and interpretation

The service binds only loopback. Browser mode is explicit, same-origin, with a random per-process token kept in page memory. Tokens are absent from URLs, browser storage and server logs. No CORS, remote paths, microphone or device pairing is added. This boundary protects against other web origins, not software already running as your local user. A separate design is required for remote hosting or multi-user access.

The supplied-model animated demo and measured NLOS/PHANTOM route are separate from room-recording inference. Geometry displays only backend-supported patches, without invented wall edges/enclosure/free space. Synthetic success and software checks do not establish measured-room accuracy, hardware qualification or material accuracy. See [viewer limits](RESULT_VIEWER.md), [acquisition](ACQUISITION.md) and [hardware acceptance](HARDWARE_ACCEPTANCE.md).
