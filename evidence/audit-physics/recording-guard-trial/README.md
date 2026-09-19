# Recording-path held-test experiment: promotion branch closed

The conditional clutter test removes the previously observed joint-extractor false plane, but its recording-level recall loss fails the unchanged acceptance criteria. Do not promote this branch as a default backend option. No main runtime files were edited.

## Fixed comparison

The source baseline is `198d365f3b13f221ac258332eaaccdf96506a641`. `design.json` froze the original recording experiment; `combination-design.json` froze the subsequent joint-extractor comparison after the first failures. These are exposed-case regression experiments, not new blind validation.

All original eight-view cases, all separately frozen twelve-view cases, and all harder stress cases were processed from existing lossless WAVs. The later comparison added the already exposed FLAIR measured-RIR replay. Both guarded and unguarded runs independently read the same raw files through the immutable pipeline. Exact raw hashes and complete extracted observations agree within each extractor's guarded/unguarded pair. Across matched and joint extractors, the raw hashes agree in all19 comparable cases but the extracted observations differ in all19. This difference is intentional and preserved in `candidate-input-differences.json`.

The held test retains the analytic design unchanged: six training views, six held views, all720 permutations, maximum statistic over the training-derived hypothesis pool,0.01 conditional global-null threshold,25mm prediction scale, at least four geometrically valid held views. It adds the already frozen exclusive assignment and bounded shared-covariance joint refit. These parameters were not widened after recording failures. The core's physical residual, local rank, mirror ambiguity and higher-order ambiguity checks remain. Any original-core higher-order ambiguity also remains, because removing a parent in the statistical stage must not make an ambiguous path appear resolved.

Fewer than12 valid independent nonempty views return the original result with explicit `held_guard.status='unavailable'`, `calibrated=false` and no p-value. This applies to all ten original eight-view cases and two stress cases. More than12 valid views use the first12 in acquisition order for the fixed test, followed by all-record refinement; FLAIR has24. The p-value refers only to the prerefit training image and conditional exchangeable global null, never to physical first-order correctness, postrefit geometric accuracy or calibrated confidence.

## Results

Each cell is matched / false / missed surfaces. False here uses the unchanged one-to-one geometry matching definitions; FLAIR's incomplete laser reference retains its documented unmatched-surface interpretation.

| Dataset | Matched filter | Matched + guard | Joint extractor | Joint + guard |
|---|---:|---:|---:|---:|
| Original eight-view suite |27 /0 /19|27 /0 /19, guard unavailable|Not rerun|Not rerun|
| Frozen twelve-view suite |25 /0 /0|17 /0 /8|25 /0 /0|22 /0 /3|
| Frozen stress suite |30 /0 /48|24 /0 /54|32 /1 /46|29 /0 /49|
| FLAIR measured-RIR replay |0 /0 /10|0 /0 /10|0 /0 /10|0 /0 /10|

The twelve-view matched guard fails all three room cases and the optional reflector case. Joint+guard still fails room227 (5/6 surfaces) and reflector233 (5/7). Stress retains the same four required higher-order/edge-path failures. Joint+guard removes the diffuse-null673 false surface while losing three true stress surfaces relative to unguarded joint extraction. No criterion changed and no failed case was dropped. FLAIR remains ambiguous in every arm, which honestly preserves uncertainty but does not pass measured spatial validation.

Runtime totals, in seconds, include raw import, extraction, inference and the guarded arm's original-model ambiguity preservation:

| Dataset | Matched | Matched + guard | Joint | Joint + guard |
|---|---:|---:|---:|---:|
| Twelve-view |2.17|2.86|3.25|3.70|
| Stress |13.73|18.28|27.95|32.64|
| FLAIR |3.35|4.24|6.66|7.30|

Concurrent development load was not controlled; these are observed local runtimes, not a platform performance guarantee.

## Failure diagnosis and decision

Seven of the eight lost matched-filter twelve-view surfaces have compatible training hypotheses but fail the unchanged held test. One is absent from the six-view hypothesis pool. Several real echoes are missing or merged, leaving only four or five clean held confirmations; contaminated training fits further reduce predictive agreement. `lost-surface-diagnosis.json` preserves all eight, with truth used only after fitting. Combining the better overlap extractor improves this, but does not meet frozen criteria. Increasing the threshold or selecting a more favorable split from these answers would not constitute validation.

The earlier analytic physical countercontrols also remain relevant: exact coherent double-bounce paths pass the test as phantom first-order planes. Thus this procedure tests pose-dependent acoustic association under a restricted null, not physical reflection order. Receiver-dependent reverberation is not exchangeable clutter. Bootstrap/Hessian timing uncertainty remains an independent unqualified experimental branch and is not rescued by this test.

Close default promotion. The bounded evidence does not justify adding API complexity for this version. Better acquisition information, improved path extraction, or a separately designed sample-efficient model test could justify a future branch; none should be asserted to pass from these exposed cases.

## Checks and provenance

`checks.json` records13 passed focused checks: pre-cancellation at raw entry; explicit under12 unavailability with no p-value; cancellation inside training search and joint optimization; hypothesis/permutation limits; exclusive candidate evidence and shared covariance; finite JSON export/reload; and preservation of six original higher-order ambiguities. Both full runs record `source_unchanged=true`. The final portable builder was verified to reproduce every executed scientific module byte-for-byte.

`input-manifest.json` and `combination-input-manifest.json` preserve WAV fingerprints. `results.json` and `combination-results.json` preserve per-case counts, misses, failures, diagnostics, runtime and source hashes. Individual result files remain locally under `results/` and `combination-results/`; generated raw files stay outside Git. The external dataset is FLAIR Zenodo17037517v1, CC-BY-4.0; source0 measured room responses are convolved with a generated probe and normalized. This is measured-RIR hybrid replay, not recordings from our phones. Original source/license and partial-download integrity limits are in the repository's FLAIR manifest and retrieval code.

## Reproduce

From a checkout containing commit198d365 and this experiment directory, using the existing project-local environment:

```
.venv/bin/python evidence/audit-physics/recording-guard-trial/build.py
.venv/bin/python evidence/audit-physics/recording-guard-trial/prepare_inputs.py
.venv/bin/python evidence/audit-physics/recording-guard-trial/run_generated.py
```

`build.py` extracts immutable project source and copies the two archived experimental extractor files. Its generated `snapshot/pyproject.toml` pins NumPy2.3.5 and SciPy1.18.1; Python3.12+ is required. `prepare_inputs.py` preserves existing files, regenerates missing synthetic cases and requires their hashes to match the executed corpus. The original null137 case was regenerated locally and all eight WAVs matched byte-for-byte. A full clean regeneration was not performed for this closed research branch.

For the combination including FLAIR, obtain the fixed subset using the repository's licensed retrieval instructions, then:

```
.venv/bin/python evidence/audit-physics/recording-guard-trial/prepare_flair.py --subset PATH_TO_FLAIR_SUBSET_NPZ
.venv/bin/python evidence/audit-physics/recording-guard-trial/run_combination_generated.py
.venv/bin/python evidence/audit-physics/recording-guard-trial/checks.py
```

The FLAIR preparation helper verifies all24 generated WAV hashes against the executed input manifest. It has not been rerun in this branch because the existing24 raw inputs were already available and were reused directly. These commands overwrite generated report files; preserve original reports before reproducing. The scientific modules, original scripts, compact reports and hashes are sufficient to archive this negative result; do not commit `raw/`, `snapshot/`, caches or large per-capture result arrays.
