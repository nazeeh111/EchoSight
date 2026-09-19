# Independent assembled calibration-contract review

Reviewed commit: `38ce3ffcbca671fa00134284d53cdf9aef82dc90`.
Comparison base: `27bb6a42f06924b66711360ddb24bc3bfc24a6b3`.
Date: 2026-09-19.

**Result: no actionable material finding in the assigned calibration provenance/schema repair and its affected recording/CLI boundaries.** This is a bounded software review, not proof of physical accuracy or completion of the broader charter.

## Scope and method

Read `docs/CHARTER.md` and `docs/CHARTER_ADDENDUM.md`, the exact candidate diff, live calibration implementation, signal processing entry/validation, session validation and recording admission, pipeline evidence construction, CLI interruption handling, calibration schemas, existing contract/evidence examples and relevant tests. Checked that supplied reference geometry remains explicitly labeled and is not exported as inferred room structure.

The main checkout was initially clean at the reviewed commit. Runtime and tests were executed from an isolated `git archive` of that exact commit at `work/review-38ce3ff/source`; no runtime, tests, HEAD or index edits were made. The coordinator's later `STATE.md` change was left untouched. The only runtime file changed in the candidate relative to the base is `echosight/calibration.py`.

The complete numerical block from construction of selected delay observations through fitting, noise/uncertainty propagation, fixed acceptance checks and proposal construction is byte-identical to the base. Its SHA-256 is `4caf18c0fc5c10a1dcbf9cb909c7d43dab576672def9464a9b2212c7f9ed27d8`. The source-admission checks and shared recording/CLI/API implementations remain unchanged by this repair. No frozen criterion or optimizer adjustment is introduced.

## Executed evidence

Environment: existing pinned local environment, Python 3.12.14, NumPy 2.3.5, SciPy 1.18.1, jsonschema 4.25.1. This reviewer did not create a fresh dependency installation; the coordinator independently owns clean GitHub reproduction.

From repository root, archive creation:

```sh
mkdir -p work/review-38ce3ff/source
git archive 38ce3ffcbca671fa00134284d53cdf9aef82dc90 | tar -x -C work/review-38ce3ff/source
```

From `work/review-38ce3ff/source`, using the existing repository `.venv/bin/python` by absolute path:

```sh
PYTHONDONTWRITEBYTECODE=1 /Users/nazeeh/Documents/Codex/2026-09-18/echosight-autonomous-backend-implementation-lead-a/backend/.venv/bin/python -m unittest tests.test_calibration_contract tests.test_calibration tests.test_mapping_admission_cancellation.ReferenceCalibrationAdmissionTests tests.test_completion_cancellation tests.test_cli -v
```

Result: **25 tests passed in 12.554 seconds**, exit 0. Log: `work/review-38ce3ff/tests.log`. This includes actual recording calibration, held-out failure, covariance checks, supplied source conflicts, schema/replay boundaries and CLI behavior. The reported earlier 210-test integration run is source-reported evidence, not this reviewer's independent test count.

Additional independent probe, from repository root:

```sh
PYTHONDONTWRITEBYTECODE=1 .venv/bin/python work/review-38ce3ff/probe.py
```

Result: exit 0. Source, results and log are in `work/review-38ce3ff/probe.py`, `probe-results.json`, and `probe.log`. The probes exercised:

- Mixed missing-path, silent valid WAV and corrupt WAV captures in one calibration session. The rejection remained schema-valid; statuses were respectively `not_available`, `verified`, `not_available`. All other 17 raw recording hashes remained verified. The silent WAV digest matched independently hashed file bytes. No applicable calibration or calibration ID was returned.
- Rejection replay after restoring only available original paths. Input identity and diagnostic codes remained equal.
- Numeric probe spelling changes and unknown annotations. Equivalent numeric declarations preserved both input identity and calibration ID. Removing supplied verification assertions changed input identity while leaving the numerical fit equal.
- A separate real CLI process receiving SIGINT during calibration. It exited 130, reported cancellation, and preserved the exact prior output bytes. This probe did not replace the processing or optimizer with a mock.
- Formal validation of the five checked-in proposal/rejection examples.

The existing focused tests additionally verify pre-decoding planar/missing-probe rejection, malformed declared probe retention, checksum assertion admission and malformed-checksum input errors, source contradiction rejection before fitting, exact snapshot replay, and unchanged caller inputs.

Verified exact candidate/archive source hashes:

| File | SHA-256 |
| --- | --- |
| `echosight/calibration.py` | `4346c68fcf462fc9aabee8c54caffc999d065a64ec7ed9dcba5f7eefa7f12931` |
| `schemas/calibration-result.schema.json` | `c77b7f5404c60fecb338d887066a131414fa534e47ec9b92fa0258eae2bb69f0` |
| `schemas/calibration-reference.schema.json` | `7f8469b34bd9b2da80252034d9bbbc3dc5efd44cac63cb5cef244a2ca2b1f006` |

Machine-readable comparison: `work/review-38ce3ff/source-check.json`.

## Contract assessment and limits

The snapshot preserves consumed fit declarations/defaults and reference partitions while excluding recording paths and unknown annotations. Known malformed probe fields remain inspectable as authorized. The supplied checksum is an admission assertion; the separately exposed digest records only bytes whose hash reached an observation. Early/unavailable digest states do not claim verified raw identity. Input identity cannot distinguish unidentified bytes when no digest exists, as the documentation explicitly states.

Rejected outputs are structurally prohibited from carrying an applicable calibration or calibration ID. Missing acquisition metadata remains distinguishable from malformed processing input. Expected upstream diagnostic codes and capture IDs survive without raw exception paths. Reference geometry and conditional uncertainty remain explicitly qualified, and the combined speed parameter does not claim separate physical sound-speed and source-clock recovery.

The coordinator reported tiny fresh-installation numerical differences while reproducing all statuses, raw hashes and input identities. That was not independently reproduced by this reviewer. A changed `calibration_id` when fitted floating-point values differ is consistent with its current binding to the actual calibration and implementation. The documentation does not establish bitwise equality across numerical installations; delivery should distinguish numerical agreement from byte-identical artifacts.

No new HTTP calibration-fit route exists in this change; affected HTTP/recording behavior uses unchanged shared pipeline/storage code. I did not repeat unrelated completed mathematics/security/evaluation reviews, a full API suite, new held-out scientific experiments, or own-device tests. The synthetic fixture checks software behavior only. Exact reproduction of every interrupt instant, universal malformed-input coverage and physical generalization are outside this bounded review.

Coordinator packaging note: exact probe sources/results and logs are retained in [calibration-contract-review](calibration-contract-review/README.md); the reviewer report above is unchanged.
