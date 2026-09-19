# Independent raw path-interpretation evaluation

Current state: renderer and score semantics verified on development seed 1001; unseen seeds 1301/1307 have not been generated or fitted. Wait for the coordinator to identify the immutable integration commit.

Portable entry points are `evaluation/path_interpretations.py` and `evaluation/path_interpretations_acceptance.json`. The renderer has no inference import, uses independently calculated propagation lengths, and keeps annotations in truth.json outside session/bundle input. All three methods receive the same PCM bytes and supplied calibration: original be5c70a mapper, immutable updated mapper, updated direct-grid competitor. Every immutable core file is checked against Git before use.

The first freeze and development corpus remain untouched. The exact covariance comparison caught .005**2 versus .003**2+.004**2 floating-point rounding, a 3.39e-21 m2 discrepancy. This metadata expression was corrected to the original expression before any unseen generation. `initial-variance-mismatch.json` retains the original failure; `verified-v2/freeze.json` identifies the corrected renderer, unchanged criteria and current specification.

Executed evidence:
- `verified-v2/renderer-development.json`: exact probe, fractional impulse centroid checks, all six development families with 48 mono PCM16 recordings each, source rank and calibration PSD checks, actual panel support, SNR and peak amplitude.
- `verified-v2/renderer-independent-checks.json`: exact original physical/surveyed geometry and covariance, 1,008 independent broken-path checks, 912 reflection-law checks and 48 byte-identical regenerated WAVs.
- `metrics-checks.json`: six acceptance semantic checks, including preserving ideal-point no-result failure and rejecting unsupported compact locations on null/two-emitter controls.
- `verified-v2/environment.json`: local versions and shared scoring helper hash.

The fixed inherited noise gives minimum active SNR about 60.6–63.6 dB. These cases cannot establish moderate-noise robustness despite that wording in the initial specification. Parameters remain unchanged. Ideal point and dispersive filters are synthetic path surrogates, not measured furniture, edge diffraction, full-wave simulation or physical accuracy. Finite-panel visibility does not model occlusion; the panel is partially transmitting in this geometric model.

Run after coordinator supplies the actual commit, replacing COMMIT with that identifier:

```
.venv/bin/python -m evaluation.path_interpretations evaluate --output work/path-interpretation-eval/verified-v2 --integrated-commit COMMIT --allow-unseen
```

The hash guard deliberately rejects changed source/specification. Preserve any earlier freeze; do not silently replace it. The runner renders and fingerprints the entire twelve-case corpus before fitting any case, then preserves individual results, errors, operational 300-second timeouts, partial progress and final acceptance. Expected scientific failures yield exit 1 with report retained. Operational timeout is not a new accuracy criterion. Do not rerender favorable scenes, tune to answers or weaken frozen criteria.
