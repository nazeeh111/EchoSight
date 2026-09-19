# EchoSight implementation state

Objective: deliver verified backend in nazeeh111/EchoSight; hardware validation follows later. Current charter is docs/CHARTER.md plus the implementation-task user instructions, which supersede historical research restrictions.

Authority: private repository, project branches/commits/push/default-branch integration authorized; no deployment, paid services, credential/global changes. On 2026-09-18 GitHub verified nazeeh111 owner/admin; sinha-ritwik accepted write; littleapple08 pending write invitation 333732214. No invitations duplicated.

Checkout: this repository, branch backend/implementation, initially empty remote. Shared module boundaries and writer ownership: docs/CONTRACT.md. No physical recordings from our devices exist.

Architecture: small Python package, raw lossless imports, clock-aware signal processing, unlabeled multi-view 3D reflector inference, local HTTP/CLI and JSON evidence. First delivery targets useful room-layout evidence and consequential reflectors with unknown physical extents. Surveyed acoustic-center poses are supplied inputs, not recovered scene geometry.

Prioritized risks: (1) unlabeled echoes/false surfaces and direct-path timing; (2) coplanar mirror ambiguity and shared timing/pose error; (3) simulator mismatch/external measured response failures; (4) processing limits/cancellation/recovery; (5) source model and iPhone acquisition remain hardware acceptance.

Plan: establish recording-to-result baseline in parallel owned modules; integrate/import-test; freeze evaluation and compare serious alternative; investigate strongest failure and capability improvement; independent assembled-commit review; clean-checkout reproduction; verified remote delivery and one vault index note.

Current evidence: prior research at ../.. /astra-chatgpt-work-open-ended-acoustic/outputs/research (external local reference, not a portable dependency). Prior model uses q=s+2(d-n.s)n and excess delay (|r-q|-|r-s|)/(c/kappa); no bistatic divide-by-two. Source-buffer seconds are not physical seconds. Supported footprints are not object edges.

Next: specialists implement owned modules; coordinator integrates and pins local environment. Active jobs recorded in native specialist controls.

## Checkpoint 1: connected backend (2026-09-18)

Implemented: lossless PCM/phyphox ZIP import, repeated probe and affine clock correction, unlabeled multi-view image-source inference, support triangles/conditional uncertainty, local HTTP jobs/cancellation/export/reload, CLI and inference-revision comparison. First strict eight-view synthetic room result: 4/6 true surfaces including ceiling, zero false surfaces, ~0.83 s. Earlier permissive version found6/6 but failed clutter controls; seven-view confirmation deliberately supersedes that claim. Checkpoint evidence: evidence/checkpoint-1.json. Final acceptance remains pending.

Development controls now pass declared scenario criteria; serious direct-plane competitor currently ties supported surfaces. External measured-RIR hybrid replay requires1s probe spacing to avoid reverberant pilot overlap (25/25 accepted versus23/25 default); laboratory array is collinear and supports no unique3D map. Raw external data stays outside Git.

Unresolved in priority order: per-surface supporting-view ambiguity (an unused elevated capture cannot resolve a plane's mirror), missing2/6 room surfaces under conservative confirmation and extra-view improvement, frozen held-out evaluation, independent integrated review, physical source/iPhone qualification. API/schema and source-playback refinements follow. No final completion or physical accuracy claimed.

Active workers: acoustics, inference, backend, evaluation. Coordinator owns commits; checkpoint uses a brief writer freeze. Repository checkpoints should remain frequent and coherent per current user steering. Current context remains grounded in files; no coordinator handoff needed at this milestone.

## Checkpoint 2: durable store and comparison safety

Prior remote checkpoint: ea5975d6ad9c9d39139d6de9b2379c554aab0868. Added exclusive process ownership for the local store, stricter archive/revision/metadata validation, bounded API comparison, and explicit coordinate-frame identity before relating maps. 24 targeted storage/API/evolution/pipeline tests passed. This checkpoint changes safety/recovery semantics, not acoustic acceptance. Physics/playback/additional-view work continues independently and will be the next coherent checkpoint.

## Checkpoint 3: independent-view confirmation and frozen acoustic evaluation

Scientific changes: per-support receiver-plane mirror checks, explicit unresolved hypotheses, local information-rank guard, shared relative-clock covariance, local+global image-source proposals, scored next-view choices, weak-direct ambiguity rejection and left/right playback with1s spacing option. Additional12-view acquisition preserves original8-view fixtures and recovers all6 room planes; held-out tilted case recovers7/7. Original frozen8-view room cases retain5/6, with misses reported. No false main surfaces in frozen suites. Serious competitor mostly ties and misses the extended tilted plane; simple baseline performs poorly. Evidence: evidence/frozen-held-out.json, frozen-extended-held-out.json, guidance.json, external-final-*.json. Exact source hashes identify tested code; later checksum-only pipeline guard separately tested.

38 focused signal/inference/CLI/pipeline/frontend/evaluation tests pass. Assembled59-test run exposed one real archive limit error:12-capture result JSON exceeds the1MiB session metadata bound. Backend specialist is fixing a distinct bounded result size; actual HTTP-to-geometry succeeded before reload. This remains explicitly unresolved at this checkpoint, so no final completion claim.

Next: fix/recheck full HTTP export/replay; independent assembled-commit review; clean checkout setup/tests/demos/frozen regression; publish final verified default branch and handoff. Selected user model/effort unchanged. All scientific workers have completed; backend limit fix active. No physical device measurements have occurred.
