# Independent assembled-backend review

Reviewed commit: `a9fc6b000257169ca2b9dfb0ad4de71b68695af0`.
Reviewer had no implementation ownership and made no changes to implementation, tests, or documentation. An immutable `git archive` snapshot was unpacked to `work/review-a9-snapshot`; all review probes and test execution described below import code from that snapshot. The surrounding worktree had unrelated active edits, which were excluded. This report is a review of a9, not approval of subsequent patches.

## Actionable findings

### P2: Near-parallel dimension is an origin-dependent offset difference

Location: `echosight/inference.py:349–357`, particularly line 350.

The code admits normals up to three degrees apart, then calls `abs(d1 - sign*d2)` a plane separation. For nonparallel planes, translating all coordinates by vector t changes that expression by `(n1 - sign*n2)·t`, even though the physical room, devices and acoustic observations have not changed. The disclaimer that this is not a proven enclosed room dimension does not fix the geometric error.

Independent reproduction: `work/review-a9-probes.py`, saved output `work/review-a9-probes.json`. Two exact supported planes have normals `[1,0,0]` and `[cos(2 degrees), sin(2 degrees),0]` and offsets 0 and 4.7 m, with eight noncoplanar receivers. Both runs return status `ok`, the same two supporting surface IDs and effectively zero physical residual. Before translation, the reported dimension is 4.700000 m (standard deviation 0.008372 m). Translating source and receivers by `[0,100,0]`, keeping their physically identical delays, produces 8.189950 m (standard deviation 0.282759 m). This position range is within the validated session bounds.

Requirement implication: the dimensions delivered to a frontend must be derived physical spatial relationships, with consistent coordinates and uncertainty. The quantity currently labeled separation fails coordinate translation invariance.

Repair: either reserve separation for genuinely parallel planes, or define a local width at an explicitly reported, physically anchored reference point and direction. Propagate joint covariance through that same defined quantity. A translated-scene regression must preserve the value and uncertainty.

### P2: Archive results are published without validating their session/evidence identity

Location: `echosight/storage.py:410–415` (unchecked result publication) and `echosight/storage.py:358` (freshness based only on revision).

The loader validates/hash-checks raw audio, but copies any finite JSON `result.json` into the live session without checking the result schema, session ID, recording manifest, acquisition calibration or provenance. `get_result` labels it non-stale whenever its supplied revision matches. Therefore a mixed-up or altered archive can show another session's geometry as a current result of these recordings. This is an integrity/correctness issue; it does not require an adversarial caller or a claim that hashes authenticate measurements.

Independent reproduction in `work/review-a9-probes.py`: create/export a legitimate empty session `archive_review`; add a `result.json` for `DIFFERENT_SESSION` with revision zero, a plane at 99 m, and `physical_validation: true`. Import succeeds. `get_result('archive_review')` serves that foreign plane, its foreign session ID, the incompatible validation claim, and `stale: false`. No waveform evidence is required. The response violates the published result schema's `physical_validation: false` contract. It also lacks any result-local replay marker, although the session does have one.

Requirement implication: replay/export must preserve evidence provenance and prevent silently substituting geometry from unrelated recordings. The supplied/result distinction must remain visible to the later frontend.

Repair: validate imported result structure and bind session ID, revision, calibration and capture hashes to the archive input before publishing; preserve intentionally stale snapshots only under explicit, valid subset semantics. Reject an incompatible result or keep it separately as an unverified archived artifact pending reprocessing. Mark the result itself as an archived computational output. Merely changing caller-declared provenance is insufficient to detect accidental evidence mixing.

### P2: Normal twelve-view export cannot be reloaded (already identified by coordinator)

Location: `echosight/storage.py:413`, with export path at lines 368–374 and unrestricted result persistence at the earlier `_run` writes.

The a9 loader allows only 1 MiB for a result even though ordinary waveform response exports exceed that. Independent reproduction generated and processed the normal `room`, seed 1, twelve-capture scene, uploaded its recordings into SessionStore, completed a job, exported it, then reloaded into a second store. Result serialization was 1,857,100 bytes. The job completed and export succeeded; reload raised `ValueError: result metadata too large`.

Requirement implication: the selected enhanced demonstration must survive export/reload. A legal generated result cannot exceed its own reload contract.

Coordinator already had a scoped result-size fix in progress when review began. It was intentionally excluded from this a9 snapshot. Final verification should cover actual recording-to-result export as well as the maximum legal response shape, consistent request/expanded-archive bounds, and rejection before publication.

## Direct checks performed

- Ran all 58 committed tests against the isolated a9 snapshot. The initial run passed 55 and could not bind the loopback port for three API tests under the filesystem/network sandbox. After native approval for the temporary local listener, the three API tests all passed. This is 58 passing tests in total, not a single successful initial full-suite run.
- Read all ten `echosight/*.py` implementation modules (including CLI and orchestration), all committed tests, both frozen acceptance files, scoring/evaluation runners, scientific/acquisition/API/frontend contracts and result schema. Reviewed stored frozen/external reports and their code hashes. No raw external measured dataset was independently reprocessed in this review.
- Derived the timing convention: receiver nominal time is affine in source nominal time; removing relative alpha leaves an excess delay in source-buffer seconds. With source actual/nominal rate kappa, the bistatic path difference is `(c/kappa)*delay`. The code uses that convention consistently in signal extraction and inference. It does not halve separated-source delay into range.
- Independently finite-differenced the physical forward model while holding a tilted physical plane fixed. The implemented source derivative `(u-A g)/v` and receiver derivative `(g-u)/v` agree to maximum absolute errors of `2.27e-12` and `1.81e-12` seconds/metre respectively. This validates these local derivatives at the chosen nondegenerate configuration, not universal covariance calibration.
- Inspected covariance construction for common direct timing and relative slope per capture, receiver error shared across its echoes, and source/speed terms shared across surfaces. Inspected exclusive assignment, original nonlinear physical residuals, support-specific coplanar mirror checks, rank-deficient hypothesis handling, cancellation checks and proposal/refinement bounds. No additional concrete P1/P2 defect was established in those areas during this pass.
- Verified fitting receives a whitelisted acquisition object and recording-derived observations, with generated scene truth stored separately and loaded by evaluation after processing. The imported-result flaw above is a distinct replay boundary problem.

## Evidence interpretation and remaining scientific limits

The frozen synthetic reports assert passing original and extended criteria. Their source hashes match a9 scientific modules, but `pipeline.py` changed since those reports; external-final reports also predate the reviewed `inference.py`. Those reports therefore remain source-reported evidence for their recorded code, not complete local replication of a9 or of subsequent repairs. Final integration should reproduce relevant evidence against the final immutable source hashes.

The strongest supported claim remains multi-plane 3D inference from simulated recording files under a stationary point-source/first-order specular-plane model with supplied acoustic-center poses. The original suite reports 27 matched, 19 missed and zero false surfaces; the extended suite reports 25 matched, zero missed and zero false. The serious plane-grid competitor ties most cases and misses one extended tilted reflector. This does not establish broad algorithmic superiority.

The 27/27 and 25/25 offset coverage counts are conditional local intervals on small selected synthetic sets. The simulator does not draw all declared shared calibration errors, and the benchmark does not establish 95% coverage in physical rooms. Wrong direct references, source directivity/multiple drivers, diffuse scattering, undetected reflectors, calibration bias and unsearched association alternatives remain scientific risks already materially disclosed. Collinear measured-response replay can verify extraction/abstention but cannot establish measured 3D reconstruction accuracy. These limits are not presented as implementation bugs.

Core setup is appropriate to the stated Mac/Linux local use: NumPy/SciPy pins, standard-library HTTP/storage, no billed API or runtime dataset dependency. `fcntl` excludes native Windows; API documentation explicitly identifies the POSIX/macOS/Linux store lock, so no Windows portability claim was inferred. Hardware qualification remains pending and is not satisfied by this review.

## Disposition

No P1 finding established. Three reproduced P2 issues require resolution or an explicit narrowed contract before completion; the coordinator accepted the first two and already owned the third. Follow-up review must identify the final code commit and rerun the discriminating probes after the repairs. Passing the existing tests alone did not catch these boundary failures.
