# Independent material and appearance implementation review

Reviewed commit: `bc46e970e63039c434fab15a2c71b91c0d690be2`.

Binding: `binding-bc46e970e630.json` records all 12 reviewed production-module/schema SHA256 values. Each exactly matched the commit and working tree at binding time. Review fixes made afterward require a separate delta binding.

## Findings at reviewed commit

### P2: cancelled scene schema admits completed interpretation claims

The existing cancellation branch of `schemas/result.schema.json` restricts geometry claims but does not prohibit the newly added `interpretation`. An actual cancelled pipeline result, augmented with a valid completed material/appearance estimate from the frontend example, passes the scene validator with no errors. Runtime cancellation correctly retracts interpretation; the advertised frontend contract does not express the same rule.

Reproduction: `cancel_schema_probe.py`; observed evidence: `cancel-schema-probe.json` (`wrongly_accepted: true`). Restrict cancelled scene output to no interpretation, matching the current publication function, or require an explicitly cancelled empty interpretation if that policy is intentionally chosen. Add a regression retaining a genuine completed estimate in the attempted cancelled payload.

### P2: valid shared palettes can generate schema-invalid probabilities

At `echosight/interpretation.py:257`, sequential accumulation of the same color across nine equally likely valid reference profiles produces `1.0000000000000002`. The strict output schema rejects this probability. Reproduction uses actual recording-derived feature extraction, nine valid supplied profiles and a common full red palette; it does not mock the extractor.

Reproduction: `palette_schema_probe.py`; observed evidence: `palette-schema-probe.json` (`schema_valid: false`). Use stable summation and narrowly bounded floating-point correction where necessary. Preserve deliberately missing palette mass; do not unconditionally normalize incomplete palettes or weaken probability bounds.

No other actionable finding was identified in this bounded review. Both findings concern contract consistency, not a claim that runtime cancellation leaks or that the rounding changes physical accuracy.

## Executed checks

`probe.py`, results in `probe-results.json`:

- Full non-diagonal covariance and unequal-prior likelihoods match an independent `scipy.stats.multivariate_normal` calculation. Two usable views match the arithmetic mean of independently computed view distributions.
- The .25/.75 material mixture with only the first profile assigning .6 red and .2 blue produces .15 red, .05 blue and .8 unassigned.
- Nine negative admission controls preserve unknown: route mismatch, angle outside domain, missing angle, probe mismatch, training overlap in an otherwise incompatible profile, duplicate bytes, duplicate waveform, insufficient views and feature outlier. Rejected records remain present.
- Profile mean/unbiased covariance match an explicit centered cross-product calculation for six full-rank vectors, including exactly .4² diagonal regularization and preserved training identities.
- Independently rendered raw signals obeying inverse-distance pressure, at two geometries and with a polarity-reversed echo, recover expected band gains with maximum absolute error **0.008274 dB**. This is controlled synthetic evidence only.

`lifecycle_probe.py`, original evidence in `lifecycle-artifacts/report.json`:

- A job held active while its session context is revised retains the original input snapshot and becomes stale when completed.
- Material-reference construction through the store rejects that stale result.
- Reprocessing revised context changes identity while keeping geometry and observations exactly equal.
- Export/reload quarantines the old result; recomputation reproduces identity and interpretation without original working paths.
- Cancellation at interpretation entry and the final callback clears geometry and interpretation claims while retaining all 12 observation records; actual cancelled outputs pass the scene schema.

Focused existing public-boundary tests:

- CLI override, bounded context inputs, unchanged original manifest/output on invalid input and demo-manifest reproducibility passed (`public-boundary-tests.log`).
- Actual raw CLI and HTTP reference-profile parity, training-query rejection and failed-command output preservation passed (`http-boundary-test.log`). The initial HTTP attempt could not bind under the filesystem/network sandbox; a scoped native-permission retry succeeded. This was an environment restriction, not a code failure.

No full suite was run by this reviewer; the coordinator owns assembled verification. Production code was not edited by this reviewer.

## Scope and remaining limits

Reviewed signed response extraction, geometry/evidence binding, route/probe/angle domains, training/query reuse, Gaussian normalization and full covariance, sample covariance construction, palette mixtures, context identity, immutable jobs/revisions, raw replay, API/CLI integration, cancellation publication and new offline schemas. Existing geometry/calibration science was not reopened.

The implementation correctly describes conditional reference-library comparisons and contextual sRGB predictions. Unique recording hashes are an operational non-reuse check, not proof of statistically independent physical measurements. Declared route IDs cannot authenticate stable transducer behavior. These controlled checks establish neither real building-material accuracy nor optical measurement. Physical qualification remains a separate task; no hidden semantic library or fabricated confidence was found.
