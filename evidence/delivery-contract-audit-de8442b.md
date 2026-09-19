# Independent delivery/contract audit

Commit: **de8442b2dd088c036d2b92eaeaf29a1273785795**. Read-only review of the existing immutable `work/review-de8442b-snapshot`; its Python/Swift byte identity was independently verified in the preceding admission review. No live uncommitted code or documentation was used. No implementation or documentation edits were made.

## Findings requiring delivery correction

### P2: Separate processing limits from preservation/import limits

Locations: `docs/API.md:52,66`; `acquisition/ios/README.md:42`; missing concrete processing boundary in `docs/ACQUISITION.md:9–15`.

The API contract advertises 8–192 kHz and 120 seconds, including in its general job/resource limits. Those are preservation/import limits. `echosight/signals.py:92–99` processes only integer 16–96 kHz, at most 30 seconds, and additionally requires the emitted upper probe frequency to be no greater than 0.45 times the receiver rate. The native README says only that the downstream range is “narrower.” A client or acquisition operator following these interfaces can collect and successfully upload a recording that can never enter the detector. It should not have to discover this after acquisition. `docs/HARDWARE_ACCEPTANCE.md:23` mentions 30 seconds, but does not repair the API or acquisition interface's incomplete limits.

Independent reproduction: actual one-second PCM WAVs at 8 kHz and 192 kHz both import successfully, then yield `no_result` with `recording_rejected: unsupported recording sample rate`. A 31-second, 48 kHz PCM WAV imports successfully and yields `recording_rejected: recording exceeds 30 second processing limit`. The rejection precedes acoustic quality analysis. Evidence: `work/delivery-contract-probes-de8442b.py` / `.json`.

Exact correction: add a small explicit distinction to API and acquisition documentation: storage accepts 8–192 kHz / 120 s; acoustic processing accepts 16–96 kHz / at most 30 s and a compatible probe band; native collector caps capture at 20 s. The default 15 kHz upper probe frequency requires a delivered receiver rate of at least 33,334 integer Hz, so 44.1/48 kHz are within that frequency condition whereas 16 kHz is not. State that successful import and `acquisition.processing_eligible` do not promise acoustic processing support. Keep original data preservation behavior.

### P2: Persistent track identity is not supplied automatically across three results

Locations: `docs/FRONTEND_HANDOFF.md:40`; related overbroad “stable surface_id” wording in `docs/CONTRACT.md:9`. Implementation: `echosight/evolution.py:99`.

The handoff says correspondences supply a persistent frontend `track_id` across changing evidence IDs. Current pairwise comparison uses `previous_surface.track_id` if present, otherwise `previous_surface.surface_id`. Neither the pipeline nor comparison writes that track into the current result. A straightforward consumer comparing consecutive saved results loses identity on the next revision even with exactly unchanged geometry.

Independent reproduction: copy one real shipped room surface into three otherwise equivalent result objects with surface IDs `a`, `b`, `c`. Comparing A→B returns track `a`; B→C returns track `b`. Explicitly carrying `a` onto B's surface before comparison produces `a`. This is a deterministic contract mismatch, not an acoustic association failure. Evidence: the same retained probe script/JSON.

Exact correction options: (1) document that frontend state owns a surface-to-track map, demonstrate how to compose each pairwise correspondence with the prior map, and preserve raw acoustic results unchanged; or (2) implement explicit optional prior-comparison state and document its binding/validation rules. Either way, state that association is bounded one-to-one display continuity, not guaranteed global physical identity; “surface_id is deterministic for its supporting evidence and may change after refinement” is the accurate contract wording.

If adding the proposed prior-comparison input, consequential cases to cover are: its `current_result_id` must match the new previous result's nonempty `result_id`; prior status must be comparable; mapped surface IDs must exist uniquely in the previous result; duplicate tracks/mappings must reject; new births absent from prior correspondences initialize their own track; stale/foreign state cannot be silently applied; absent/ambiguous intermediate surfaces do not resurrect tracks automatically. Split/merge alternatives remain subject to current one-to-one association and must not imply physical identity. These are design review recommendations only; no future change is verified here.

## Smaller contract corrections

- **P3, schema boundary:** `schemas/controlled-request.schema.json:23–26` permits a 1,024-character coordinate-frame ID, whereas the referenced session schema and runtime allow only 160 characters. Controlled processing requires equality with every session's frame, so lengths 161–1,024 cannot ever describe an admissible protocol. A 161-character request validates against the published controlled schema; constructing the matching session fails with `coordinate_frame_id must be a string of 1 to 160 characters`. Set this field's `maxLength` to 160 (or reuse the common definition). Keep unrelated free-text protocol fields at their intended limits.
- **P3, stale demonstration description:** `docs/ACQUISITION.md:3` still identifies eight stops/two placements as the main software demonstration. README and frontend commands now explicitly use twelve views, and the README correctly discloses eight-view misses. Update the acquisition paragraph to distinguish the twelve-view primary demonstration from the older eight-view case. README also says “Three or four phones can be reused across three placements to obtain twelve views”; specify four phones across three placements or three phones across four placements.
- `docs/CONTRACT.md` still reads partly as the initial team assignment rather than a current consumer reference. Its numerical timing convention and main signatures remain compatible, but it omits the joint source/effective-speed replacement semantics, controlled interface, native evidence API, and exact-waveform admission boundary now documented elsewhere. Prefer a compact current entry-point table linking the authoritative API/acquisition/calibration documents; mark historical ownership planning separately. This is maintainability guidance, not a separate runtime defect.

## Checks and scope

Read README; `docs/ACQUISITION.md`, `CONTRACT.md`, `FRONTEND_HANDOFF.md`, `API.md`; native README/CONTRACT; all seven published schemas. Cross-checked relevant current CLI parser/dispatch, API route dispatch, storage/session validation and controlled-job admission, signal admission, pipeline evidence/result construction, evolution comparison, and native UI/source-declaration fields. New path-model mathematics, STATE/COVERAGE, and the pending hardware-status edits were excluded.

Executed one small standalone probe covering the three concrete boundary/identity cases above. Ran CLI help for `echosight`, `probe`, `evaluation.controlled_development`, and `evaluation.guidance`; documented command names/flags resolve. The README's twelve-view, process/export/replay and controlled demo routes correspond to current parser behavior. No missing executable command was found that warrants another full demonstration run. The preceding independent admission report already verified native bridge reproduction and exact-waveform/replay behavior; those checks were not repeated here. No full suite, install, network server, hardware, signing, or launch was run for this documentation audit.

The major physical-validation qualifications, raw/provenance quarantine semantics, native explicit-null timestamp contract, scene-vs-job status distinctions, geometry support/unknown-extent wording, and separation of controlled unlocalized change from conditional geometry are appropriately disclosed. The findings above are delivery contract issues; they do not overturn those bounded claims or establish scientific/hardware acceptance.

Portable historical reproduction: create a clean detached checkout ofde8442b, then run `.venv/bin/python evidence/delivery-contract-probes-de8442b.py --checkout PATH_TO_CHECKOUT --output work/delivery-reproduction.json`. The wrapper now requires that exact clean commit; the probes are unchanged. Current fixes must be checked separately.
