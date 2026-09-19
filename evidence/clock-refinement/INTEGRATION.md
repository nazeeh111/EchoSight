# Narrow integration checkpoint

Following the independent design/results review and coordinator authorization, main `echosight/signals.py` now contains only the frozen observed-rate trigger and its explanatory comment. No additional diagnostics, threshold changes, repeated-response estimator or uncertainty claims were added. The frozen experiment/report remain historical bytes and correctly describe the state before this integration.

`tests/test_clock_refinement.py` contains self-contained deterministic raw direct-null and room-path fixtures. They failed before the fix with≈143ppm rate errors, then pass after it. They preserve the unresolved100µs overlap rather than asserting two recovered paths. Below-trigger behavior, cancellation before/during correction and30sresource limit are tested. Nineteen combined signal checks pass:

```
.venv/bin/python -m unittest tests.test_clock_refinement tests.test_signals -v
```

`integration-verification.json` pins exact source/test hashes and proves syntax-tree equivalence of the entire live signals module to immutable de8442b plus the frozen trigger. The experimental initial-clock trace is excluded from main. Full prior/postfix test logs are preserved. Independent reviewer was asked to inspect these exact files. No commit was made by the physics specialist.

The compact archive contains protocols, source, complete paired per-record metrics, summaries, all regression diagnoses, scene scoring and historical-control outcomes. It excludes raw WAVs, paired full scene response arrays, checkouts and external datasets. Numerical results remain keyed by raw SHA-256. Large originals remain at their referenced workspace paths. Reproducing the full1248study requires the preserved v3/v4 recordings and immutable de8442b checkout identified in the frozen manifest; renderer sources are included in `input-renderers/` to support regeneration using repository `evaluation/path_interpretations.py`. The archive itself is evidence and source, not a self-installing benchmark with embedded raw data. The production regression tests above require no archived audio or measured dataset.

Own-device physical validation, source-direct ambiguity and calibrated timing uncertainty remain unresolved. All reported false/missed geometry and per-record regressions stand.
