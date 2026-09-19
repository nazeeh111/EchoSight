# Independent bounded follow-up: be5c70a

Inspected immutable **be5c70ab14a450aaae28537b0905e77e9453be33** against **198d365f3b13f221ac258332eaaccdf96506a641**, using `git archive` snapshot `work/review-be5c70a-snapshot`. All snapshot `echosight/*.py` files were byte-verified against the commit after execution. No implementation edits, Git writes, criteria changes or held-out reruns were performed.

**The three reported 198d365 P2 defects no longer reproduce. No residual P1/P2 was established within this follow-up.** This closes those implementation findings, not multisource acceptance or physical validation. The original held-out failures remain unchanged historical evidence.

## Code and scope

Read the immutable changes and surrounding logic in `echosight/multisource.py`, including `_physical_path_groups`, `_exclusive_physical_assignment`, competing-subset scoring/output, source-session identity checks, and raw-bundle admission/cancellation. Read the added regression tests. This review excludes the committed research archives unrelated to these fixes and every uncommitted acquisition change. The core covariance mathematics was unchanged and was not broadly re-reviewed.

## Original findings

### Exclusive physical-path assignment

Reran the original analytic and public numerical-entry doublet probe, changing only its snapshot path. The preceding version reused a single path for two peaks 120 microseconds apart in 24 public-output recording/path combinations. Current output has **zero path reuse**. The invalid two-parent sufficient alternative disappears; the remaining alternatives each contain three parents, with scores approximately 265.104 and 275.478 versus original score 560.181.

The output still retains two invariant parent surfaces because those are the intersection of two distinct three-parent explanations. That is consistent with the declared intersection semantics; it does not claim a two-parent model explains the complete evidence. The emitted smallest complete competing explanation contains three parents. Original first-order hypotheses remain available.

Independently checked the new assignment helper against exhaustive enumeration over candidate/path choices in **120 random small cases**, including excluded paths, infinite/incompatible costs, coincident predictions and score cutoffs. All results matched; 38 cases were correctly infeasible. The score exactly matched the returned choices, no coincident group supplied more than one arrival in a recording, and the same path remained usable in separate recordings. This independently tests the grouped assignment reduction, beyond checking only the original example.

### Source-session evidence identity

Reran the original duplicate-ID numerical probe. It now returns `calibration_needed`, no surfaces and no support entries instead of six surfaces with colliding provenance keys. The committed raw-entry regression also verifies rejection before any recording read. Both entry points check cross-session identity; distinct source indices no longer silently collapse into the same output evidence key.

### Guarded, bounded raw-bundle admission

Original null/list, malformed JSON and oversized-file probes now return `no_result` with diagnostics. The 1,200,002-byte bundle specifically reports the byte-limit error. Reading is bounded to `MAX_JSON_BYTES+1` before parsing.

Additional probes exercised invalid UTF-8, an empty file, a missing path and a directory path. All returned diagnostics without escaping exceptions. A pre-cancelled request was run with `Path.open` patched to fail if called; it returned `cancelled` without opening any file. Session identity and aggregate capture budgets are now validated before recording processing.

## Consequential regression checks

Reran the independent actual-WAV clock-units probe: four sources, eight receiver positions, physical sound speed 343 m/s, source-clock scale 1.003, different receiver clocks and effective speed 341.9740777667 m/source-buffer second. All 32 observations passed; both planes remained recovered with the same offset errors, 0.000135619 m and 0.000040182 m. Immediate and mid-signal cancellation, invalid-WAV rejection and excess-source-count rejection passed.

Executed `tests.test_multisource` (12 tests) and `evaluation.test_source_relocation` (2 tests): **14 passed**. These include genuine extra-plane preservation, exact-corner alternative preservation, hidden/tangential cases, common calibration sensitivity, source-scoped initial evidence and the four new review regressions.

## Artifacts and limits

- `work/review-be5c70a-alias-probe.py`, `.json`, `.public.json`: original helper/public doublet reproduction.
- `work/review-be5c70a-input-probes.py`, `.json`: original identity and raw admission reproduction.
- `work/review-be5c70a-raw-probes.py`, `.json`: actual recording, units, cancellation and invalid-WAV checks.
- `work/review-be5c70a-assignment-probe.py`, `.json`: independent exhaustive assignment comparison and extra admission checks.

No broad backend suite, development acceptance rerun, frozen held-out rerun, measured-data evaluation or hardware test was performed. Existing two-source abstention, hidden-parent/association limits and original held-out failures are not resolved by these fixes. The 1 ns grouping tolerance merges numerical coincidences; it is not a general detector-resolution or unresolved-multipath model. The outputs remain conditional on the tested path family and declared acquisition/calibration assumptions.
