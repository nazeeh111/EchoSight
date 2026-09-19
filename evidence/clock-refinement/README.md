# Recording-only clock refinement

The implementation adds the exact tested observed-rate trigger to the existing single acquisition retry. [Integration checks](INTEGRATION.md), [frozen study](REPORT.md), [protocol](PROTOCOL.md), and [independent outcome review](../independent-review-clock-refinement.md). The study report predates the production edit and intentionally preserves that historical wording; INTEGRATION.md records the later code change. Individual echo losses and inherited false planes remain failures.

`clock-refinement-evidence.tar.gz` contains32source/evidence members and no raw audio. Archive SHA-256: `88926493b70e07273c293d91b61d8860e0a046b9eb606673eea90d4712bb679d`. Its MANIFEST.json identifies original bytes. Extract into a new disposable directory to inspect it; do not overwrite an existing experiment. The readable documents here are exact copies of the original reports, not replacements for the frozen manifest.

The four self-contained production regressions need only pinned project dependencies:

```sh
.venv/bin/python -m unittest tests.test_clock_refinement tests.test_signals -v
```

Full1248case reproduction requires the earlier v3/v4 raw inputs or their regeneration, immutable de8442b core and directory layout described in INTEGRATION.md and runner.py. The archive does not embed those recordings or external datasets. Do not regenerate a freeze over existing historical evidence. The recorded study is exposed development/regression evidence, not fresh held-out acceptance or our device validation.
