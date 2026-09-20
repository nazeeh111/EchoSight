# Material and appearance implementation evidence

**Independent final review:** [ab5ea75](FINAL-ab5ea75-REVIEW.md) closes both P2 findings at the exact delivered runtime. [Binding and commands](final-receipt.json), [cancelled-payload rejection](final-cancel-schema-compact.json), [bounded palette output](final-palette-schema-probe.json) and [independent probes](final-probe-results.json) record the follow-up.

[Clean GitHub reproduction](../reproduction-ab5ea75/) passes244 tests, both demos, exact profile/context/export/replay and offline schemas at the reviewed commit.

Version 0.2.0 adds recording-derived reference profiles, conditional material comparisons and supplied contextual color distributions to the existing API/CLI/session/replay route. No new dependency, trained model or semantic material catalogue is used. Geometry inputs and frozen scientific criteria are unchanged.

The controlled development demo recovers six room surfaces; three get correct synthetic-filter estimates and supplied colors, three remain material unknowns. Null, reused-reference and out-of-domain controls retain their unknown states. These results do not establish real building-material accuracy, calibrated confidence or optical measurement.

- [Demo audit](demo-review.md), [exact input/output hashes](demo-verification.json), [saved development summary](development-summary-bc46e97.json), and [nonvacuous reuse-gate correction](demo-gate-followup.json).
- [Initial independent assembled review at bc46e97](independent-review-bc46e97.md), [numerical/raw probes](independent-probes-bc46e97.json), and the original [cancellation-schema](cancel-schema-failure.json) and [palette-rounding](palette-schema-failure.json) failures. The report deliberately retains both findings; final follow-up records their closure separately.
- [242-test assembled execution](assembled-tests-242.txt), 83.977 seconds. Runtime was bc46e97; the cancellation-schema repair was applied while this suite was running. This is an integration result, not an immutable final-commit receipt. Its affected seven checks then passed separately ([red](cancel-schema-red.txt), [green](cancel-schema-green.txt)). Final clean-checkout evidence is authoritative for the delivered code.

Reproduce the independent mathematical/raw probe from the repository root:

```sh
mkdir -p work/material-review
python evidence/material-appearance/probe.py
```

This writes a new ignored `work/material-review/probe-results.json`; it does not replace the committed original evidence. The probe checks non-diagonal Gaussian likelihoods against a separate SciPy calculation, unbiased sample covariance, negative admission paths, palette mass, and independently rendered inverse-distance gains at two geometries. It is software/simulation evidence.

Run the actual recording demonstration with:

```sh
python -m evaluation.material_development --output work/material-demo
```

The runner writes all raw inputs, separate truth, settings, profiles, context, results and summary. Query truth is consumed only after query processing. Use a new directory; existing runs are never overwritten. The [material guide](../../docs/MATERIALS_APPEARANCE.md) and [frontend handoff](../../docs/FRONTEND_HANDOFF.md) define semantics and later physical qualification.

The original review scripts are included unchanged. `lifecycle_probe.py work/material-review/lifecycle-artifacts` generates the saved cancellation inputs used by `cancel_schema_probe.py`; create that output directory first. `palette_schema_probe.py` exercises the original nine-profile regression. These scripts write current receipts under ignored `work/material-review/`; original failing receipts above remain committed.
