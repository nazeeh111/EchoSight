# Independent final-commit follow-up review

Reviewed commit: **`565769a078b3f834de626a5d0697c21f5ceb5e8a`**.
Baseline review: `work/review-a9.md`, against `a9fc6b000257169ca2b9dfb0ad4de71b68695af0`.

**Disposition: the three reproduced P2 findings from the baseline review are resolved. No remaining P1/P2 issue was established in this follow-up.** This conclusion is bounded by the implementation and checks below; it is not physical-device validation or a universal correctness/security claim.

## Independence and exact code

I had no implementation ownership and changed no project implementation, tests or documentation. I unpacked this commit using `git archive` to `work/review-565769a-snapshot`, read the complete implementation diff from a9, and ran checks importing exclusively from that snapshot. After the checks, I compared all 11 `echosight/*.py` snapshot files byte-for-byte with `git show` at the reviewed commit; all matched.

Changed implementation inspected: `echosight/inference.py`, `storage.py`, `pipeline.py`, `api.py`, and `cli.py`. I also inspected the new regression tests and changed API/inference/frontend contracts. The prior review covered the assembled signal extraction, geometry, inference, storage, API, pipeline, CLI, evolution, simulation, frozen criteria and evidence interpretation.

Independent probe source: `work/review-565769a-probes.py`.
Independent probe output: `work/review-565769a-probes.json`.

## Repair verification

### Coordinate-invariant, explicitly local dimension

The implementation now reports `local_plane_intersection_separation`: distance between the planes' intersections with their mean-normal line through the supplied source acoustic center. It reports the reference, direction and endpoints, and explicitly denies a unique global separation for nonparallel planes.

I reran the independent two-plane, eight-view example from the original review, then translated source and receivers by `[17,100,-31]` metres without changing the delays. The value was **4.6321248476 m**, with standard-deviation bound **0.0019182493 m**, unchanged to the asserted `1e-7` tolerance. Endpoints translated by the same vector. This differs appropriately from the old erroneous 4.7 m coordinate-offset difference because the corrected quantity is a defined local distance.

I implemented the explicit line/plane intersection formula separately, finite-differenced it at `1e-6`, and propagated the returned full shared covariance. My independently computed geometry standard deviation was **0.0018833391922 m**, compared with the implementation's **0.0018833391942 m**. The reference-location contribution was **0.0000349101299 m**. The reported total equals the sum of these marginal standard deviations, consistent with the disclosed conservative first-order bound for unknown correlation. The existing exact-parallel regression also passed. This verifies the repaired definition and propagation locally; it does not calibrate intervals against physical data.

### Imported geometry cannot become a current result

I independently tested two fabricated archives based on a legitimate processed twelve-view session:

- A foreign-session result claiming physical validation. Import retained its bytes only as `archived-result.json`; metadata reported `session_mismatch` and `unsupported_physical_validation_claim`, `physical_validation=false`, and `requires_recomputation=true`. `get_result` raised `KeyError`.
- A fabricated 999 m plane retaining all correct session, revision, recording hash and acquisition labels. Metadata had no binding mismatch, but it was still quarantined, required recomputation, and was unavailable through `get_result`.

Thus matching labels no longer authenticate supplied geometry. The archived artifact preserves original claims without adopting them. This is stronger than checking metadata alone and resolves the original defect.

### Ordinary large results and legitimate stale results survive replay

The independent twelve-view seed-1 result was **1,863,226 bytes**, above the former 1 MiB restriction. Current and stale versions both imported successfully. For the stale case I added another recording after the completed job, confirmed `stale=true`, then exported.

Both imports withheld archived geometry from the current-result interface; the stale archive explicitly reported revision/manifest/acquisition mismatch. Re-export before recomputation contained `archived-result.json` and preserved the original result bytes exactly. I imported that re-export into another store successfully. A new processing job in each original replay store recovered six surfaces, returned `stale=false`, marked `computation_origin=local_processing`, and retained `physical_validation=false`.

This is a documented change in replay semantics: import preserves the old computation as an archived artifact; a job is required before serving a current result. It does not silently drop stale computations or mislabel them as current. After recomputation, the new current result is exported while the original quarantined artifact remains locally retained, as documented.

## Other consequential checks

- **All 67 tests independently passed**, across two runs. Initial full discovery passed the 62 non-HTTP tests; five HTTP tests were unavailable because the sandbox denied binding a loopback port. After native approval for a temporary local listener, I reran those five tests only; all passed, including actual recordings through HTTP, export/import, and replayed processing. The initial full discovery itself did not pass, and no application failure was inferred from the sandbox denial.
- The passed suite includes maximum legal response-shaped result storage/export, oversized-result rejection before publication, unchanged raw-session budgets, checksum/path handling, cancellation/restart recovery, physical timing/mirror checks and existing end-to-end scientific regressions. I inspected the relevant limit changes: general session JSON remains 1 MiB, results are bounded separately at 32 MiB, compare accepts two full results, and import checks total expanded and raw-recording budgets.
- I ran the new CLI `export` and `replay` commands in **separate processes** from the immutable snapshot. They imported original recordings, processed them, archived, reloaded and recomputed six surfaces, with local-computation provenance. The commands did not merely copy the archived result.
- I independently recomputed the implementation fingerprint from all package source bytes and matched the CLI result's value: **`71bad6d2dbf18e114a0eee0047377e1e9f84c8b58dafb18e1b77e6d40c1cf2be`**. Reported runtime versions matched this run: Python **3.12.14**, NumPy **2.3.5**, SciPy **1.18.1**. The result identity now incorporates implementation and runtime fingerprints. As tested, source remained immutable throughout; this is not verification of hot-editing a running process.

## Scope and remaining limits

I did not repeat the entire frozen evaluation or external measured-response experiments in this follow-up; the coordinator was independently reproducing those against the final checkout. Prior frozen reports are evidence for their recorded code hashes, not substituted here for fresh execution. This review does independently exercise the complete recording-to-3D path through the API, CLI and replay pipeline.

The scientific limits in the initial review remain: supplied surveyed poses, stationary effective point-source and first-order plane assumptions, incomplete reflector visibility, unresolved direct-path/systematic calibration risks, conditional local covariance, and non-exhaustive association search. The repaired local dimension is not a room enclosure or physical edge measurement. Physical MacBook/iPhone accuracy remains untested. Nothing in the patches or this review justifies weakening those distinctions.

No further P1/P2 repair is requested based on the evidence obtained. Subsequent implementation changes would need appropriately scoped verification and a new identified code revision; documentation/evidence-only publication can reference this exact reviewed implementation commit.
