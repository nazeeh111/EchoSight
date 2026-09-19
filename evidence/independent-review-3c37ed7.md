# Independent bounded review: controlled comparison at 3c37ed7

Reviewed **3c37ed7ac1d11ffb9f90a4d69ebaeede6b8ef18f**, using an immutable `git archive` snapshot at `work/review-3c37ed7-snapshot`, against **0eb9fdd55a0703ec003eb62f87e04fb4213d8646**. After execution, every snapshot `echosight/*.py` file was byte-compared with the commit. No implementation files were edited, no Git writes were made, and no uncommitted multisource or physics experiments were inspected.

**No actionable P1/P2 was established in this bounded review.** This is not a claim of calibrated false-alarm rates, physical validation, complete causal identification, or acceptance of the complete backend.

## Actual scope

Read the original charter, `docs/audit/CONTROLLED.md`, `docs/HARDWARE_ACCEPTANCE.md`, relevant API/frontend contracts, and the complete new `echosight/controlled.py`. Inspected the integration diff and surrounding storage admission, result retrieval, publication, cancellation/recovery, export/import and calibration-update code; API routes; CLI handling; controlled request/result and job/session schema changes; core/job/HTTP/CLI tests; and the development waveform generator. Rechecked the pipeline's raw-byte digest, metadata, provenance and implementation-fingerprint boundaries where consumed by the new module. Did not repeat unchanged main inference mathematics or the earlier general backend audit.

## Consequential checks

### Change controls and interpretation

The four-epoch loader requires matching source, pose, probe, sound-speed/clock/effective-speed calibration and uncertainty, route/source identifiers, stable capture/device/pose IDs, and distinct stationary-device positions. All declared captures must pass recording processing. Duplicate raw hashes are rejected across epochs and devices. Metadata equality and byte inequality are necessary controls, not independent proof of operator declarations or independent physical acquisition.

Executed the committed raw null, gain-only, moved-reflector, failed-return and shared-timing controls. Independently ran a different random seed (`177`, four fixed receivers), with actual WAV processing, for unchanged geometry and recording-gain change combined with polarity reversal in both B epochs. Both produced `no_repeatable_change`, with zero changed receiver views. This uses the existing development waveform model with a new control transformation; it is not an independent acoustic simulator or held-out field evaluation.

Separate changes to physical sound speed, source-clock scale, source-position uncertainty, one receiver's position uncertainty, or the presence of a joint source/effective-speed calibration reject as inconclusive before any epoch is processed. The output's lack of unconditional physical/causal claims is consistent with what these tests establish. An undeclared reversible transducer/environmental change can still produce repeated acoustic difference, as the contract states.

### Timing, spatial uncertainty and candidate linkage

Independently constructed four observations with a 1 ms persistent echo shift, non-unit relative rate `alpha=1.02`, rate standard deviation `0.0002`, direct timing standard deviation 20 microseconds, candidate-local standard deviation 30 microseconds, and shared differential standard deviation 40 microseconds. The independently calculated differential timing standard deviation and code both give **0.00007077073358406104 s**. Raising the shared budget to 1 ms withholds the shift; receiver count does not average it down.

For localization, `|d-n·s|=|q-s|/2` gives image/source gradients of magnitude one half in the plane-normal direction. The implemented sum of marginal standard deviations bounds unknown source/image and cross-epoch correlations rather than assuming they vanish. Constructed geometry with image covariance `10^-6 I` m² and source standard deviation 0.003 m yields a four-epoch bound of **0.008 m**, exactly matching code. A 0.2 m reference-local plane shift passes in this controlled mathematical fixture; large source covariance withholds localization. Translating source, planes and image sources together preserves the result.

Changing one associated plane's supporting candidate ID causes the three-view mathematical fixture to lose localization, despite otherwise unchanged plane geometry and positive response evidence. Thus the geometry claim is tied to the shifted candidate identities across all four epochs. The cross-state nearest-delay assignment remains conditional; these checks do not prove physical path/object identity in dense clutter. No statistical p-value or calibrated confidence coverage is inferred from the engineering gates.

### Job snapshots, raw preservation and publication

A separate probe paused an admitted controlled job before actual processing, revised the stored A-before source position (revision 4 to 5), then released processing. The result completed against revision 4 and the original `[1.2,1.7,1.1]` source, with its pinned revision recorded. It remained unlocalized repeatable acoustic change. No per-session scene result was created or replaced. Export/reload preserved raw hashes plus device/pose metadata. As documented, ordinary exports contain current session metadata; preserving an earlier protocol also requires its request/result and pinned local input, not an assumption that a later session export rewinds calibration.

Independently killed an actual subprocess with `os._exit(23)` immediately before the completed-job state write, after the controlled result file had been persisted. Restart marked the job interrupted; the persisted but unpublished result was not served. This probes the publication boundary more directly than a crash inside the processor. The committed cancellation, failed-state-write, restart and raw-session-isolation tests also passed.

The API accepts only stored session IDs/revisions for controlled jobs, not embedded server paths. It uses the existing bounded body, queue and worker limits. The loopback HTTP test checks path-field rejection, stale revision conflict, oversized request handling, and equality of API/CLI receiver evidence on the same raw input. CLI relative recording paths also reproduce. Reading the schema changes found no material contradiction with these returned statuses/fields; no JSON Schema validator was installed in the project environment, so schema inspection was not an automated full validator pass.

## Independently executed checks

| Tests | Passed |
| --- | ---: |
| `tests.test_controlled` | 8 |
| `tests.test_controlled_jobs` | 3 |
| `tests.test_cli` | 4 |
| `tests.test_controlled_http` | 1 |
| **Total** | **16** |

Tests ran using the existing backend `.venv/bin/python` from the immutable snapshot. HTTP required and received native approval for a temporary loopback server. The independent probe script initially used the wrong calibration-update request shape; it failed validation as expected, was corrected to the documented nested `calibration` object, and then passed. That first probe error was not a product defect.

Additional evidence is in `work/review-3c37ed7-probes.py` and `work/review-3c37ed7-probes.json`. The script includes raw controls, mixed-calibration rejection, a concurrent snapshot mutation, export/reload, actual publication-boundary process death, analytic timing/spatial checks and candidate-link rejection. Temporary recording stores were disposable; saved JSON records outcomes without raw data.

Not run: broad backend suite, new frozen/generalization evaluation, hardware experiments, incomplete-upload socket repetition from earlier audits, or uncommitted experimental work. The selected tests and probes support the bounded integration behavior described above, not the full charter's final acceptance.
