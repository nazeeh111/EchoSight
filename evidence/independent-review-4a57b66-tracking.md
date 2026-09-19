# Independent tracking and delivery repair review

Reviewed immutable local commit **4a57b662e02485fff663b3d433b3ac81177bbef4**, extracted with `git archive` into `work/review-4a57b66-snapshot`. No implementation, documentation, schemas, tests or Git state were modified. The 16 specifically inspected source/document/schema/test files were byte-compared with that commit; hashes are retained in `work/review-4a57b66-source-hashes.json`.

## Result

**No remaining P1/P2 found within this bounded follow-up.** The previous delivery audit's two P2 findings are closed. Its smaller controlled-frame schema and placement-count corrections are also present. The new explicit prior-comparison interface preserves declared display labels across raw result revisions without modifying those results, and rejects the malformed/stale/duplicate cases checked below.

## Scope inspected

Read changes and surrounding validation/dispatch in `echosight/evolution.py`, `api.py`, `cli.py`; relevant unchanged processor admission in `signals.py`; `schemas/comparison.schema.json` and the controlled-request frame bound; current README, native README, `docs/API.md`, `ACQUISITION.md`, `CONTRACT.md`, `FRONTEND_HANDOFF.md`, and `TRACKING.md`; tracking/evolution regression sources and schema-test changes. No new scientific/path/source-model work was inspected as part of this review. STATE/COVERAGE and unrelated scientific evidence updates are outside this conclusion.

## Delivery findings closure

- **Processing versus import limits:** API and acquisition documents now explicitly distinguish preservation at 8–192 kHz/up to 120 seconds from acoustic processing at 16–96 kHz/up to 30 seconds, with `high_hz <= 0.45 * actual_rate`; native documentation retains its 20-second collector cap. API wording expressly limits `acquisition.processing_eligible` to native continuity/route evidence and retains later processor checks. These figures match the unchanged admission implementation previously reproduced in the delivery audit.
- **Track persistence:** frontend handoff now requires explicit `previous_comparison` carry state for three or more revisions and explains the fallback when omitted. Raw surface IDs are described as deterministic for their supporting evidence, rather than stable physical identifiers. The new tracking contract clearly limits claims to one-to-one display continuity and excludes physical identity, missing-echo disappearance, hidden-history resurrection and global reidentification.
- **Controlled frame schema:** independently validated a 160-character frame and rejected 161 characters in the repaired schema, matching session limits.
- **Demonstration wording:** primary acquisition demonstration now says twelve stops and correctly distinguishes four phones over three placements from three phones over four. The older eight-view misses remain explicit.
- **Integration contract:** replaced the historical ownership plan with current entry points and explicit calibration/provenance/extent limitations. The experimental research interfaces remain separate from the public per-session route.

## Independent probes

Retained script and output: `work/review-4a57b66-probes.py` / `.json`.

1. Built a six-revision sequence using a real shipped surface shape with distinct orthogonal planes: A; A+B; B; empty; B+C; B+C. IDs change on every revision. B's birth label continues when A ends; the empty intermediate result removes all carry mappings; later B receives a different birth label; both later B/C labels continue into the next revision. All five actual comparison outputs validate against the new schema. All raw result objects and prior comparison objects remain unchanged.
2. Independently mutated 29 prior-state cases: wrong/missing schema/status/revision identity; wrong mapping container, empty or incomplete coverage, missing fields, null/boolean/object/empty/overlong identifiers, duplicate surface IDs, duplicate track IDs and extra per-entry fields. Every case raises `ValueError` before producing comparison output.
3. Invoked the real CLI in separate subprocesses with malformed JSON, a prior-state file exceeding 1 MiB, and stale revision binding. Each exits 2, retains an existing output file byte-for-byte and preserves both raw result files. The oversize case reports the byte-limit failure, not a later parser failure.
4. Inspected birth collision handling: all previous labels and assigned labels are reserved; deterministic nonce generation resolves a collision. Existing targeted tests exercise this concrete collision and verify determinism. Deliberately reused result identifiers across independently constructed histories are explicitly outside the uniqueness promise, consistent with the implementation.

The carry object is deliberately declared display state. It need not authenticate geometry, and caller-chosen labels are allowed. Binding is to the previous result's nonempty ID and complete current-surface coverage; it is not a cryptographic proof of the historical comparison. The documentation states this distinction. A prior `incomparable` comparison cannot be carried; an incompatible new calibration produces no correspondences and fresh local labels.

## Executed checks

- `python -m unittest tests.test_evolution tests.test_tracking_integration -v`: 17 tests attempted. **16 passed initially; one HTTP test could not bind its ephemeral loopback port in the sandbox.** This was an environment permission error, not a failed tracking assertion.
- Reran only that HTTP test through the native scoped permission boundary: **passed**. It performs three real HTTP comparisons, retains the original display label across four raw revisions, and receives HTTP 400 for stale carry state. Thus all **17 distinct targeted tests passed**, with the initial bind restriction retained in the log rather than hidden.
- The targeted tests additionally exercise explicit previous-label conflicts, missing previous result IDs, malformed result IDs/track labels, one-to-one births/deaths, raw-object nonmutation, CLI chaining, schema-valid comparable/incomparable output and duplicate schema entries.
- Independent six-revision, 29-invalid-state, CLI preservation and 160/161-frame probes above passed.

Logs: `work/review-4a57b66-tests.txt`, `work/review-4a57b66-http-test.txt`. Source identities: `work/review-4a57b66-source-hashes.json`.

## Limits

No full-suite rerun, native rebuild, microphone, installation, signing, acoustic performance evaluation, or source/path-model mathematics was required or performed. The coordinator's 166-test result is not substituted for local verification. The comparison schema enforces structure and exact repeated entries; cross-entry uniqueness, complete coverage and revision binding are runtime semantics, correctly explained in the tracking document. HTTP retains its documented 64-surface boundary, while the core/CLI accepts 128. These checks establish bounded software display-state behavior, not persistent physical object identity or hardware/scientific acceptance.
