# Candidate budget: no evidence for a larger catalog

**The fixed comparison does not support enlarging the candidate catalog.** Removing the strongest18 cap increased room-path compatibility by85 opportunities for surveyed geometry, but by105 for the already frozen wrong-receiver control. The nominal advantage shrank from31 to11. No source had a positive aggregate increase relative to that same-density control. The proposed larger-catalog experiment is closed pending new independent information; no candidate-search implementation or inverse fit was performed.

The contrast was registered before calculation in `evidence/candidate-cap-information/PROTOCOL.json`, SHA-256 `7034d1cfa161791601d1bf11da75182978353b794d4b0e44e7f3118bd0fbe2cd`. It uses the same40 dEchorate recordings, original surveyed poses,240 geometry-generated first-order room-path opportunities,346.98m/s speed and7.5cm path-length matching gate. There is no echo-refined arm, alternative permutation, selected subset, changed detector threshold or new recording.

| Catalog | Surveyed geometry | Fixed wrong geometry | Nominal excess |
|---|---:|---:|---:|
| Strongest18 retained | 78/240 | 47/240 | +31 |
| Same qualified peaks before cap | 163/240 | 152/240 | +11 |
| Added compatibility | +85 | +105 | **−20** |

Of the240 paired opportunities,29 become compatible only for nominal geometry,49 only for wrong geometry,56 for both, and106 for neither. Increasing peak density helps the wrong geometry at least as much in this aggregate comparison. It does not establish that all additional nominal matches are accidental, nor that useful weak echoes never exist.

The fixed control rolls the ten receiver assignments by3 consistently across all four sources. Every recording's peak times, amplitudes, catalog size and retained candidate IDs stay unchanged. This is a same-density check, not a perfectly exchangeable physical null: nearby capsules, room symmetries, correlated paths and pose-dependent clutter may preserve structure. These counts are neither measured echo recall nor a calibrated probability or significance test. Matching is nonexclusive; one candidate may be compatible with more than one reference prediction.

## Complete strata

| Source | Nominal capped→precap | Wrong capped→precap | Difference of increases |
|---|---:|---:|---:|
| 1 | 17→51 | 10→45 | −1 |
| 2 | 28→43 | 18→48 | −15 |
| 3 | 13→45 | 9→41 | 0 |
| 4 | 20→24 | 10→18 | −4 |

Each source has60 opportunities. Reference surface IDs use axis0=x,1=y,2=z and low/high room coordinate. All surfaces are reported, including the absorbing floor.

| Reference surface | Nominal capped→precap | Wrong capped→precap | Difference of increases |
|---|---:|---:|---:|
| x-low | 16→33 | 3→22 | −2 |
| x-high | 4→25 | 3→25 | −1 |
| y-low | 0→20 | 2→20 | +2 |
| y-high | 8→23 | 5→26 | −6 |
| Floor | 21→29 | 15→29 | −6 |
| Ceiling | 29→33 | 19→30 | −7 |

Source/surface and all40 source/capture strata are preserved in `report.json`, alongside all240 opportunity records in `opportunities.json`. These retain both positive and negative local contrasts; none is selected to change the aggregate conclusion.

## Integrity and reproduction

The helper instruments immutable `de8442b2dd088c036d2b92eaeaf29a1273785795` only to copy candidates immediately before the existing cap. It verifies all40 retained candidate dictionaries against the earlier recording results, all40 pre-cap counts against the prior path diagnostic, all240 original compatibility booleans, and every control position against the stored wrong-permutation result. It imports no inference solver. The full original catalogs remain in the local output and are regenerated exactly; their hash is in the compact report. A portable rerun reproduced the contrasts, catalogs and opportunity records.

After reproducing the original measured benchmark and its `paths` diagnostic as described in [MEASURED_MULTISOURCE.md](MEASURED_MULTISOURCE.md):

```sh
.venv/bin/python evidence/candidate-cap-information/compare.py --dataset-work work/dechorate-four --output work/candidate-cap-check
```

The default source is read from the immutable Git object; `--core PATH` optionally supplies an archive with the same enforced `signals.py` hash. Input waveforms must retain their original recorded hashes. Compact provenance and results are in `evidence/candidate-cap-information/`. Full downloaded responses and generated recordings remain outside Git.

The original spatial failure and wrong-geometry false planes remain failures. This diagnostic provides no basis to reopen the closed density score, receiver-held guard, or proposed predictive-mixture experiment without additional independent evidence.
