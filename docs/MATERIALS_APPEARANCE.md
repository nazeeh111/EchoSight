# Material reference matching and contextual appearance

EchoSight can extract frequency-band reflection features from supported geometry, learn labelled reference profiles, compare new recordings with those profiles, and combine the matches with supplied color palettes. The outputs remain separate from acoustic geometry and raw evidence. There is no bundled, qualified library for recognizing arbitrary real building materials. A useful real-material result requires suitable labelled references and a matching measurement setup; the feature is implemented, while general physical classification remains unqualified.

Install and run the backend using [USAGE](USAGE.md). Request shapes, revisions, jobs and export/replay behavior are in [API](API.md). The exact new contracts are [interpretation context](../schemas/interpretation-context.schema.json) and [interpretation result](../schemas/interpretation-result.schema.json).

## Run the controlled demonstration

From the repository root, with the environment activated:

```sh
python -m evaluation.material_development --output work/material-demo
```

Use a fresh output directory. This demonstration generates original PCM recordings for controlled synthetic reference filters and separate query scenes, learns profiles through the same feature extractor, and writes results and an evaluation report. Read that report for accepted, unknown and failed cases; do not interpret a generated label or supplied palette as a measurement of a real material or color. Generating truth is saved separately from processing inputs. The original general room simulator has no guaranteed inverse-distance amplitude law and is unsuitable as material-training truth.

The output directory contains:

- `summary.json`: the declared checks, geometry/material outcomes and unknown count.
- `context.json`, `flat_reflector-profile.json` and `lowpass_reflector-profile.json`: the learned synthetic library and ready-to-use context.
- `reference_flat-result.json` and `reference_lowpass-result.json`: reference geometry and extraction evidence.
- `room-result.json` and `room/with-context.json`: the interpreted room result and a portable session manifest for reprocessing.
- `null-result.json`, `reused-reference-result.json` and `out-of-domain-result.json`: negative controls. `out-of-domain-context.json` preserves the deliberately incompatible library.

```sh
python -m echosight inspect work/material-demo/room-result.json
python -m echosight process work/material-demo/room/with-context.json \
  --output work/material-demo/room-reprocessed.json
```

The first integrated development run passed its eight declared checks while leaving **three of six room surfaces unknown for material**. Passing the demonstration does not mean every reconstructed surface is classifiable. Your generated `summary.json` is the record for your run.

## Build a profile from your reference recordings

Record a known sample using the [acquisition contract](ACQUISITION.md), with surveyed poses and a setup that supports an isolated first-order reflection. Process the session and inspect the result to choose its supported reference surface:

```sh
python -m echosight process reference-session.json --output reference-result.json
python -m echosight inspect reference-result.json
```

Create a provenance JSON file with `kind` (`measured`, `simulated` or `supplied`) and a `note` explaining the known label and measurement setup. These are your declarations, not backend authentication. Then substitute the selected surface ID and your identifiers below:

```sh
python -m echosight material-reference reference-session.json \
  --surface-id SURFACE_ID_FROM_RESULT \
  --material-id known-sample-a \
  --label 'Known sample A' \
  --route-id measurement-chain-a \
  --provenance reference-provenance.json \
  --output sample-a-profile.json
```

The command processes the original recordings again and uses the selected surface's valid features. It requires at least five distinct usable reference observations. Duplicate original bytes or decoded waveforms cannot add independent samples. Different hashes alone do not prove independent physical measurements.

For feature vectors `x₁…xₙ`, the builder stores their mean and predictive covariance:

`S = Σ (xᵢ − mean)(xᵢ − mean)ᵀ / (n − 1) + λ² I`.

The default `λ` is zero. `--regularization-std-db` supplies an explicit diagonal regularization assumption in dB; it is recorded in the profile and is not measured noise. A singular or invalid final covariance rejects. Do not increase regularization simply to make a query pass. Five observations permit four-dimensional covariance estimation but do not establish reliable probability calibration. The builder records `qualification: not_evaluated`; reserve separate labelled recordings for evaluation.

The profile binds its feature version, probe fingerprint, training hashes, observed incidence-angle range and `route_id`. Treat the route ID as the entire qualified measurement chain: emitter/channel, orientation, gain/processing, receiver/input route and orientation, plus relevant environment and distance conditions. The software checks the supplied ID, probe and angle domain; it cannot verify that unchanged names mean unchanged physical conditions. Directional source response, microphone directionality and differential air attenuation remain possible confounds.

## Apply your library to a new session

An interpretation context embeds profiles; a filename alone is not a profile. This example creates a one-profile context:

```sh
python - <<'PY'
import json
from pathlib import Path
profile = json.loads(Path('sample-a-profile.json').read_text())
context = {
    'schema_version': '1.0',
    'route_id': 'measurement-chain-a',
    'profiles': [profile],
    'maximum_squared_distance': 16.0,
    'minimum_views': 3
}
Path('context.json').write_text(json.dumps(context, indent=2) + '\n')
PY
python -m echosight process query-session.json \
  --interpretation-context context.json --output query-result.json
python -m echosight inspect query-result.json
```

The distance cutoff and minimum count above are explicit example operating choices, not confidence levels or universal acceptance criteria. Set them before evaluating your application. Add other independently established profiles to compare more labels. A single-profile probability of one means it is the only retained library alternative; it does not prove the query's real-world identity.

The `process --interpretation-context` override applies only to that run. To carry it through a later export/replay, also save the object as `interpretation_context` in the session JSON; the controlled demo already does this in `room/with-context.json`.

Use fresh query recordings. Any query byte or waveform hash found anywhere in the supplied training library is rejected for material evidence. Duplicate query views are also rejected. The same raw session can be reprocessed with another interpretation context; the context participates in result identity, while the geometry stage keeps its existing acoustic inputs. For persistent API updates, use the version-checked session contract in [API](API.md).

## What the extractor measures

Each supported path gets four apparent reflection gains in dB, over **3–5, 5–8, 8–11 and 11–13 kHz**, in source-buffer frequency units. These are not independently calibrated physical frequencies. The full bands must lie inside the supported probe band with a 1 kHz edge margin.

The extractor takes equal Hann windows centered on the direct response and observed echo, each with a ±0.5 ms radius. It sums squared Fourier magnitudes within each band and computes:

`feature_db = 10 log10(echo_band_energy / direct_band_energy) + 20 log10(reflected_path_length / direct_path_length)`.

The last term assumes spherical pressure spreading. Geometry supplies the conditional path lengths and incidence angle. The signal is the signed matched-filter response, not a deconvolved impulse response. These gains are therefore features for compatible reference matching, not absorption coefficients, optical properties or authenticated material signatures.

All known candidate centers must be separated enough for the 1.5 ms isolation screen. A second ±0.75 ms window must change no band by more than 1 dB. Bands also pass a repeat-difference noise-proxy guard; this is not a calibrated spectral signal-to-noise ratio or a feature covariance estimate. Missing hashes, unsupported probe/clock, malformed or stale support links, merged/overlapping paths, truncated candidate catalogs, weak bands and unstable windows return explicit unknown records. Undetected interference and systematic transducer bias can still escape these screens.

## Read material and appearance outputs

For each usable path and compatible profile `k`, the model computes a Gaussian log weight from the four-band vector, the profile mean `μₖ`, full predictive covariance `Σₖ` and supplied prior weight `πₖ`:

`log_weightₖ = log(πₖ) − ½[(x−μₖ)ᵀ Σₖ⁻¹(x−μₖ) + log det(Σₖ) + 4 log(2π)]`.

Only profiles with matching route/probe/feature version, covered incidence angle and squared distance within the supplied cutoff participate. Their weights normalize within that path. No compatible profile means unknown. The predictive covariance already represents the profile's feature variation; the matcher does not invent another query covariance.

A surface's `material.probabilities` averages the usable per-view distributions equally and sums to one only when `minimum_views` is met. It is a conditional library mixture, not physical confidence. Views are not multiplied to produce artificial certainty. `evidence_coverage = valid_views / total_views` and `unassigned_view_weight = 1 − evidence_coverage` separately show how much supported evidence was usable. Rejected feature records stay in the denominator. An unknown estimate can still have full coverage when the absolute view count is too small.

Appearance is optional. Supply an `appearance` object in a profile, or pass `--appearance palette.json` when building it, using the context schema's provenance and `colors` fields. Color entries contain an sRGB hex value and a probability. No palette is guessed from the material name. The result mixes those supplied color distributions with the material weights; missing palettes or incomplete palette mass remain in `appearance.unassigned_probability`. Unknown material yields unknown appearance.

These are contextual color predictions. They are neither optical measurements nor acoustic false-color visualization. A palette can describe an externally justified prior for a material/context, but sound frequency does not measure visible color.

Historical [NBS measurements](https://nvlpubs.nist.gov/nistpubs/jres/4/jresv4n2p289_A2b.pdf) report dependence of absorption on incidence angle, supporting the need to preserve measurement conditions. [Published work on learned material detection from impulse responses](https://arxiv.org/abs/1901.05852) explores a trained neural approach; EchoSight does not include that model or its trained weights. Neither source establishes the accuracy of this implementation. Current software and controlled synthetic results remain separate from later physical qualification.
