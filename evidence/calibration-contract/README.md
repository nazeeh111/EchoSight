# Calibration contract replay

These artifacts were produced by `calibrate_reference` from the existing seed-81 raw PCM WAV development fixture. They are simulation and software-contract evidence, not new blind evaluation, external measurements or hardware validation. Reference geometry is explicitly supplied calibration input, never an inferred room surface. No optimizer, source-admission rule or acceptance threshold changed for this repair.

- [Reference input](reference.json) and [successful proposal](proposal.json).
- [Held-out model rejection](rejected-validation.json): the existing fixture adds a 1ms reflected-path shift at held-out stops; failure is retained.
- [Planar receiver rejection](rejected-planar.json): no raw decoding occurs.
- [Missing probe rejection](rejected-missing-probe.json): acquisition is incomplete; no recording is processed.
- [Malformed probe rejection](rejected-malformed-probe.json): invalid duration; the pipeline exposes no verified raw hash for those rejected observations.
- [Machine-readable report](report.json): schema and canonical-replay checks, result artifact hashes, and all 40 original WAV hashes.

Run from the repository with its pinned runtime/test dependencies:

```sh
.venv/bin/python evidence/calibration-contract/reproduce.py --output work/calibration-contract-replay
```

The script renders the existing fixture into disposable temporary files, calls the production calibration API, validates actual outputs with the published JSON schemas, restores raw paths by capture ID and replays every canonical input snapshot. It checks equality of all calibration output fields except the upstream `input_result_id`: the older mapper hashes original probe spelling, whereas this contract materializes defaults. That distinction is observed for the malformed-probe case and reported explicitly. `input_id`, rejection diagnostics and fitted values reproduce. Implementation fingerprints and runtime versions can legitimately change across code/dependency revisions.

The focused verification command is:

```sh
.venv/bin/python -m unittest tests.test_calibration_contract tests.test_calibration tests.test_mapping_admission_cancellation.ReferenceCalibrationAdmissionTests -v
```

Initial resume run: 14 unique tests passed in 4.668s. A subsequent checksum-shape/privacy and missing-session-ID boundary check brought the focused run to 16 tests, passing in 4.893s. Before repair, the added boundary tests failed on untouched recordings marked `not_available`, absent upstream diagnostic codes, and omitted supplied-checksum declarations. Malformed checksum declarations raised no error before the boundary fix; six malformed types/forms are now rejected as input errors without serializing their contents. Missing session IDs retain a truthful rejection without inventing an ID. The checks cover canonical proposal/rejection replay, reference defaults and numeric spelling, identity changes for reference/pose/uncertainty/raw bytes/checksum declarations, missing/empty/malformed/mismatched probes, unavailable recording privacy, early/processed rejection schemas, actual CLI output and SIGINT preserving the previous file. Parent integration owns the full-suite and exact-commit independent review records.
