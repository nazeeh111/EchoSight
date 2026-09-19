# Frozen source-model diagnostic v4

This directory preserves all 30 original files and the exact [manifest](MANIFEST.json) of snapshot `587df54570155117f92df5a970e47e335a371ecaef31cc16d38f2e6a95108187`. The execution log is included. README, restore.py and the archive-local .gitignore are archival additions, outside that manifest. The local ignore exception preserves the manifest-listed execution.log despite an inherited ignore rule. No original source, result, gate or log was edited. This remains an experimental calibration warning, not a production mapper or validated hardware source test.

The [report](V4-REPORT.md) records the corrected bounded-gain objective and raw affine-clock experiments. The fresh group has four warnings in four dual-source cases and zero warnings in eight controls. Guarding changes 62 matched / 12 false / 0 missed surfaces into 38 / 0 / 24. These are development simulations, not improved completeness. The runner's boolean benefit gate is only `any` successful fresh dual case; the actual four individual successes must not be confused with a four-of-four requirement. [Independent review](../independent-review-source-model-v4.md) preserves this limitation and the accepted clock bias.

## Reproduction and dependencies

Use project-local pinned NumPy/SciPy dependencies and a full Git checkout containing `de8442b2dd088c036d2b92eaeaf29a1273785795`. The historical core, repository evaluation helpers and their exact hashes are recorded in [freeze.json](run-v4/freeze.json). Restore the committed v1-v3 archive first, then this archive:

```sh
.venv/bin/python evidence/source-model-diagnostic-trial/restore.py
.venv/bin/python evidence/source-model-diagnostic-v4/restore.py
.venv/bin/python evidence/source-model-v4-review/reproduce.py
```

Both restore helpers preflight all hashes and refuse differing destination files. The independent review command needs neither raw recordings nor a classifier run; it checks 84 gain problems, physical path absence, and frozen reported totals. Its output goes to work/, preserving this archive.

Full experiment regeneration additionally requires the saved v3 raw/baseline artifacts or their regeneration using the [v1-v3 instructions](../source-model-diagnostic-trial/README.md). After that preparation, in a disposable clean full checkout restored as above:

```sh
.venv/bin/python work/source-model-diagnostic/check_v4.py
.venv/bin/python work/source-model-diagnostic/run_v4.py run
```

This regenerates the 12 fresh raw-clock cases, reuses 12 v3 cases, and overwrites working reports. Do not run `freeze`: the original freeze is evidence. The 30 files alone do not contain raw audio, full per-recording baselines or every earlier fixture. The raw manifests preserve expected hashes; recordings remain outside Git. Reproduction is of exposed development cases, not a new held-out evaluation. This archival task did not rerun the classifier or generate recordings.

The later [evaluation-oracle clock diagnosis](../clock-oracle-diagnosis/README.md) is a separate postfreeze artifact and changes no v4 result.
