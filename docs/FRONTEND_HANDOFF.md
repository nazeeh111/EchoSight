# Frontend handoff v1

The backend's central claim is that sound can support several independently located 3D reflectors, including height-dependent structure, and that additional surveyed recording positions can resolve or strengthen that inference. It does not claim complete object meshes, measured edges, safe free space or hardware accuracy. The useful demonstration is understanding room layout and consequential early reflections, with visible evidence behind every surface.

## Start with these interfaces

Run `python -m echosight serve --root work/store --port 8765`. [API.md](API.md) specifies the routes, error codes and limits. The pure processing interface is `echosight.pipeline.process_session(session_or_path, cancel, progress)`. JSON schemas are in `schemas/`: session, job and scene result, all `schema_version="1.0"`. Keep session IDs, capture IDs, candidate IDs and result IDs in frontend state. The API currently accepts trusted local clients; a browser frontend needs a deliberate allowed-origin/authentication design or a same-machine server proxy. Do not make this unauthenticated local service public.

```mermaid
flowchart LR
  S[Session: surveyed poses and exact probe] --> U[Upload original recordings]
  U --> J[Start job and poll progress]
  J --> Q[Clock and direct-reference checks]
  Q --> E[Unlabeled echo candidates]
  E --> G[3D hypotheses and exclusive evidence]
  G --> R[Scene result and uncertainty]
  R --> N[Suggested new surveyed view]
  N --> U
  R --> X[Export original data and result]
```

Job status and scene status mean different things. A `completed` job may legitimately return `no_result`. Job statuses are `queued`, `running`, `completed`, `failed`, `cancelled`, `interrupted`; scene statuses are `ok`, `partial`, `ambiguous`, `no_result`, `cancelled`. A percentage describes work progress, never confidence. On restart, interrupted jobs retain input and recordings; start a new job. After another capture is uploaded, an earlier scene is marked `stale=true` until reprocessed.

Archive reload preserves raw inputs and quarantines stored computations. `GET result` stays unavailable until a new processing job completes. Session replay metadata reports the archived computation's binding issues without serving its geometry as established evidence. Result provenance includes exact implementation and numerical-library fingerprints; observation `input_diagnostics` preserves acquisition-format limits such as an unverified sample grid.

## Render the actual geometry

All positions use metres, right-handed coordinates, z up. A surface has unit `normal` n and `offset_m` d satisfying n·x=d. `vertices_m` and zero-based `triangles` can populate a mesh directly. Render the source and receiver poses using the same coordinate frame. Surface polygons summarize the convex hull of supported reflection points. Their boundary is **not an inferred physical edge**. Keep `extent_status="unknown"` visible; do not connect patches into a closed room or extrude a floor plan.

Each surface's `support` links a `capture_id` and `candidate_id` to its observed and predicted excess delay, residual and reflection point. Draw source → reflection point → receiver rays when selected. Display measured/predicted delays in milliseconds only by multiplying the stored seconds by 1000. These times are corrected source-buffer intervals; the declared source-clock scale is still needed for physical seconds. Color or opacity may summarize support, but there is no calibrated probability of correctness.

`uncertainty.offset_std_m` and `normal_angular_std_rad` are local standard deviations conditional on one path assignment and first-order point-source model. They include declared shared calibration covariance. They exclude unmodeled source/recorder bias and alternative global explanations. Do not label ±1.96 standard deviations a universally validated 95% interval. `dimensions` measure separation between plane intersections along a specified line through the surveyed source. Render their supplied reference, direction and endpoints. Nonparallel planes have no unique global separation; these measurements are not proof of enclosed room dimensions. Their uncertainty combines shared plane covariance with a conservative reference-position contribution.

When `status="ambiguous"`, definitive `surfaces` is empty. Keep `hypotheses` separate. A hypothesis may contain `surfaces`, `planes` or `image_sources_m`; render available support without inventing extents for a bare plane. Unconfirmed candidates belong in an explicitly qualified overlay, never mixed with confirmed surfaces. Diagnostics may be a code string or `{code,message}`; show the message if present and preserve the code for troubleshooting.

## Evolving the map

Upload additional captures to the same session, then start a new job. Existing recordings are immutable and remain included. Compare saved results with `POST /v1/compare` or `python -m echosight compare old.json new.json --output comparison.json`. The same `coordinate_frame_id`, source, probe and scale are required. Pipeline results default the frame to the session ID; cross-session comparisons require the caller to supply the same surveyed frame explicitly.

`correspondences` supplies a persistent frontend `track_id` across changing surface evidence IDs. Surface IDs hash supporting capture/candidate IDs and can change after refinement. The comparison reports additional support, newly supported surfaces, prior surfaces that are no longer confirmed, and ambiguity reduction. It always distinguishes inference changes from physical scene changes. A disappearing estimate does not establish a removed object.

`recommend_next_view(session,result,candidate_positions_m)` scores supplied reachable positions by predicted separation of competing image-source explanations, normalized by declared timing/pose uncertainty. It does not inspect room truth or guarantee echo visibility. A frontend can show the recommended surveyed position, the predicted delay difference and the residual ambiguity after the recording arrives. Later physical scene-change claims need stable repeated A→B→A recordings, qualified devices and independent geometric support.

## Repeatable demonstrations

```sh
python -m echosight demo work/room --seed 1 --captures 12
python -m echosight demo work/reflector --scenario reflector --seed 1 --captures 12
python -m echosight refine-demo work/refinement --seed 1 --captures 12
python -m echosight demo work/ambiguous --scenario coplanar --seed 4
python -m echosight demo work/empty-evidence --scenario null --seed 1
python -m evaluation.guidance --output work/guidance
```

Tell the audience which evidence is simulated, external measured-response replay, supplied calibration, or our own measurement. At present the first two exist and the last does not. The simulator's separate `truth.json` is evaluation-only. A future live frontend must never feed its contents to the mapper or imply that supplied geometry was acoustically recovered.

Use the held-out reports for performance claims. A useful narrative is: start with insufficient or ambiguous evidence; show an additional surveyed placement; reveal newly supported 3D structure and its rays; inspect a residual and uncertainty; finish with what remains unknown. The tilted-reflector experiment is conditional and has documented misses. No first-ever claim or competition outcome is asserted.

## Baseline integration examples

`examples/frontend/` contains actual baseline outputs for room structure, a tilted reflector, ambiguity, no result and new-view comparison. Dense response sample arrays alone are omitted from scene excerpts and listed under `example_metadata`; geometry/evidence/IDs are unchanged. `session.json` references recordings generated by the documented twelve-view demo, not committed audio. These are integration fixtures, not evidence of physical-device accuracy or a completed backend. The [coverage audit](audit/COVERAGE.md) tracks unfinished capabilities.

### Correcting calibration in an evolving session

Use revision-checked `PATCH /v1/sessions/{id}` with `expected_revision`, `calibration` and/or capture pose updates. Raw files, hashes and evidence provenance remain immutable. Active jobs keep their old calibration snapshot and their outputs become stale; a new job processes the revised session. A shared source/effective-speed covariance must remain a complete pair with its effective speed. `calibrate-reference` creates an inspectable proposal with held-out recording evidence, not a physical-validation certificate.

Comparison offsets use the shared source position as their physical reference: `offset_change_m` is the signed plane-offset change there, with `offset_reference_point_m` and `offset_semantics` explicit. This avoids changing associations when the coordinate origin moves and fitted normals differ slightly. Effective propagation speed must also match; missing calibration metadata returns `incomparable`. This display comparison does not establish a controlled physical scene change.


### Controlled acoustic change

The recording protocol now has its own API/CLI result. Show `no_repeatable_change` as insufficient evidence for change, not proof of an unchanged room. `repeatable_acoustic_change_unlocalized` supports a repeatable difference but supplies no new physical object. Only `conditional_spatial_change` contains a displacement backed by positive echoes and four geometry fits; display its conditional model and uncertainty. `inconclusive` includes failed return/repeat, changed controls or rejected recording quality. Never animate a disappeared object from missing echoes.

```sh
python -m evaluation.controlled_development --output work/controlled-demo --receivers 4 --scenario moved
python -m echosight controlled work/controlled-demo/protocol.json --output work/controlled-demo/result.json
```

This four-fixed-phone synthetic demo yields repeatable unlocalized change. `--receivers 12` generates a separate twelve-static-device geometry demonstration; it does not simulate four phones occupying twelve simultaneous positions. For that run use `--receivers 12`. The API request and actual compact four-phone result are in `examples/frontend/controlled-*.json`. Epoch response arrays are explicitly omitted; full waveforms remain reproducible from preserved raw inputs. No own-device measurement exists yet.

## Native recording evidence

The minimal iOS recorder is an acquisition harness, not a frontend viewer. Upload its original `.echosight.zip` bytes to the existing recording endpoint. [Capture manifest schema](../schemas/capture-manifest.schema.json) and [native contract](../acquisition/ios/CONTRACT.md) define exact delivered Float32, string-valued native timestamps, route and interruption evidence. Capture imports expose `acquisition.processing_eligible`; processed observations expose the recomputed `acquisition_evidence`. A well-formed interrupted capture stays downloadable and exportable but cannot enter spatial fitting. Unknown source declarations do not authenticate playback. Show `input_diagnostics`, especially unverified continuity on standalone WAV/phyphox, and never interpret eligibility or measurement mode as physical validation. Native sample/host clocks do not share the MacBook source clock.

For formal offline JSON Schema validation, register each bundled schema by its `$id`; cross-schema references resolve to those canonical versioned IDs. The `.local` IDs are identifiers, not hosted schema services. `tests/test_schemas.py` validates the shipped examples and actual pipeline/job outputs without fetching schemas from the network. Install `requirements-test.txt` for these checks; the processing runtime remains NumPy/SciPy only.
