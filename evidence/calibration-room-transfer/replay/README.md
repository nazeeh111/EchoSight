# Saved-output evaluation replay

This package recomputes all 20 frozen experiment summary rows, geometry matching, held-view candidate association, recorded admission and timing gates, comparator benefits, observation identity comparison, and final decisions. It uses compact projections of existing outputs. It does not render recordings or run calibration, raw processing, or geometry inference.

From a repository clone with the declared NumPy/SciPy dependencies installed:

```sh
.venv/bin/python /path/to/portable/replay.py --repo "$PWD" --output /tmp/transfer-gate-replay.json
```

Choose an output path that does not exist. The package can live outside the checkout. Only the unchanged `evaluation/metrics.py` is imported from the repository; its expected hash is verified. The three functions in `frozen_gates.py` are exact source excerpts from the original frozen runner. This is reproducibility of that evaluator, not an independent implementation. A separate reviewer independently recomputed the gates from full saved fits using a different assignment algorithm before packaging.

The expected result is loaded after recomputation. Gates, identifiers, types and structure must match exactly; floating values use relative tolerance 1e-10 and absolute tolerance 1e-12. All 20 rows, including failures and original measured processing times, are retained. No timing is measured again. `withheld_error_labels` explicitly distinguishes complete errors from unique-only subset errors: the original `withheld.rms_s` and `max_abs_s` are subset statistics when `complete` is false. Missing or ambiguous paths never receive invented residuals.

The recorded result is `transfer_pass=false` and `promotion_criteria_pass=false`. Both joint room fits recovered six planes without false planes, but each has only 19 of 24 uniquely associated held paths. Their complete held-path RMS is unavailable. Direct-only controls pass. These results do not justify promotion.

This failure does not establish that calibration lacks value. A separate post-fit design check found that ideal complete peaks at true predictions would still violate the frozen exactly-one-candidate rule for two held-view path pairs: their separations are about 173 and 197 microseconds, inside the fixed ±200-microsecond window. The original gate is preserved here; this package does not change the window, select different data, or replace the failed decision with a revised one.

`source-identities.json` gives SHA-256 identities of each original full fit, truth/session/manifest, runner and receipts, and lists exact projections and omissions. The four retained raw manifests identify the 56 generated recordings. `freeze.json` retains identities of all 94 pre-execution inputs, including the 48 older reference recordings and saved joint fit. Hash references do not verify omitted bytes on another machine. Original observation identity is checked against full observations during projection, then retained as a recorded hash in this package; it cannot be recomputed from reduced observations. Admission decisions are recorded inputs, not fresh audio admission.

No audio, dense impulse responses, original full fit arrays, or calibration refitting inputs are included. For exact raw replay, use commit `5d6423486be5fd448a4d7b42fbbaee264eb07c9c` plus the separately retained 74-file overlay (12,728,585 uncompressed bytes). The original runner must reside at `work/calibration-room-transfer/run.py` within that exact checkout, and requires the original reference recordings. This package cannot substitute for that overlay or prove the original calibration inputs on its own.
