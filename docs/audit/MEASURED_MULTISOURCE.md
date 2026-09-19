# Four-source measured dEchorate evaluation

**The frozen spatial target failed at `de8442b2dd088c036d2b92eaeaf29a1273785795`.** This is measured room-acoustic evidence, with an independently surveyed primary pose arm. It is not successful room reconstruction, calibrated uncertainty, or validation on our devices. The original target and failures remain unchanged.

The exact eight SOFA files comprise sources1–4 and arrays5–6 in room011111: forty measured impulse responses, four noncoplanar source positions and ten microphones. Geometry alone selected the array pair before waveform retrieval. The 14,106,687-byte download was authorized, bounded, and hash-pinned before fitting. Every file embeds the MIT license attributed to Diego Di Carlo. Full waveforms remain outside Git; the manifest permits exact retrieval.

## Frozen rules and executed results

`evaluation/dechorate_multisource_protocol.json` was frozen before retrieving these waveforms, SHA-256 `e77618d246594b15af132fad1781224af3b7bcf67cbd892a7646539fbec7751f`. Acceptance requires at least four reference-room planes, at least one horizontal plane, no unmatched definitive planes, and 5°/15cm matching. Zero-input and receiver-permutation controls must return no definitive planes. A partial result or no-result does not pass the recovery target. No enclosure or physical-edge claim is warranted.

| Method/control | Matched reference planes | Unmatched output | Missed reference planes | Outcome |
|---|---:|---:|---:|---|
| Joint mapper | 1 | 2 | 5 | Fail |
| Joint direct-grid competitor | 1 | 2 | 5 | Fail |
| Independent source consensus | 0 | 0 | 6 | Fail recovery |
| Separate source mapper, sources1/2/3/4 | 0/0/0/1 | 8/7/7/5 | 6/6/6/5 | Fail |
| First-echo baseline, sources1/2/3/4 | 0/0/0/0 | 1/0/1/1 | 6/6/6/6 | Fail |
| Digital-zero raw recordings | 0 | 0 | n/a | Control pass |
| Deliberately shuffled receiver geometry | 0 | 4 | n/a | Control fail |
| Eight rigid-array perturbation arms | 0–1 | 1–3 | 5–6 | All fail recovery |

All forty measured recordings passed acquisition/extraction diagnostics. The initial raw-input joint run took2.264s; direct-grid inference on the identical observations took0.887s. Independent consensus took3.651s. These runtime scopes differ and are recorded explicitly. A portable rerun reproduced every surface and matching metric exactly; hardware/load-dependent runtimes are retained separately.

The primary ceiling match has1.415° normal error and9.95cm origin-based offset error. The other two planes are tilted and unsupported by the six supplied room-reference planes. “Unmatched” fails the benchmark but is not independent proof that an object does not exist: all files contain a contradictory `RoomDescription` claiming a different furnished configuration. Filename and `Title` provide provisional room identity; no acoustic result resolves that metadata conflict.

## Independence, poses and uncertainty

[The dataset paper](https://link.springer.com/article/10.1186/s13636-021-00229-0) describes survey measurements followed by acoustic refinement. Primary fitting uses the original [beacon CSV](https://github.com/Chutlhu/dEchorate/blob/d3e664f1e7a7d46241d7f7b3b3761448686b9537/data/dEchorate_positions_marvel.csv) and [measurement-only expansion](https://github.com/Chutlhu/dEchorate/blob/d3e664f1e7a7d46241d7f7b3b3761448686b9537/dechorate/main_geometry_from_measurements.py). Both were read fully and hash-verified at the pinned commit. The expansion rotates known capsule offsets about each surveyed array center and translates CSV heights by2.355m. Actual SOFA position variables explicitly use Cartesian coordinates and metres. No obvious axis/unit inconsistency was found. The publication says a7.5cm third capsule interval while the pinned expansion and distributed coordinates use6.5cm; this harness follows the executable source and preserves the disagreement.

**The declared2cm numerical pose standard deviations and ±2cm perturbations do not bound the observed calibration discrepancy.** Survey versus distributed echo-refined positions differ by9.6–15.5cm for sources and7.3–8.2cm for the selected arrays. The nominal priors are conditional sensitivity assumptions, not validated acoustic-center uncertainty. Five distinct capsules on one array share center/orientation error, which the present core cannot represent across their different positions. Reusing each capsule's pose group across sources does not solve this cross-capsule correlation. Neither Gaussian confidence coverage nor independent survey replication is established.

Sensitivity arms move each whole array rigidly by±2cm along each axis, oppositely for the other array, or rotate each about its own center by±2°. The angular bound is an explicit assumption. These deterministic arms preserve array structure and are not probabilistic calibration. They are not selected by which outcome looks best.

A separately declared diagnostic uses the exact distributed echo-refined poses, without changing candidate IDs, speed, or thresholds. Both joint methods again return one room match and two unmatched planes. That arm has acoustic-label dependence and cannot replace the failed independently posed primary evaluation.

Each complete one-second measured response is convolved with a generated2–14kHz probe, using one global gain and Float32 WAV. No timing shift, crop, label-guided path selection or equalization occurs. A1s probe period is the frozen core maximum; residual late-response overlap remains possible. This hybrid replay tests measured acoustics through recording import, not original microphone clocks or MacBook/iPhone source behavior. Room dimensions are a separate dataset-provided reference, not a retrieved laser survey, and enter only evaluation. Generated echo annotations never enter fitting or scoring as measured truth.

## Dataset-specific coordinate exception

The optional echo-refined arm uses the publisher's stored world coordinates, **not a generic SOFA listener-relative interpretation**. These files have nonzero `ListenerPosition` and nondefault `ListenerView`, but the [pinned publisher converter](https://github.com/Chutlhu/dEchorate/blob/d3e664f1e7a7d46241d7f7b3b3761448686b9537/dechorate/main_build_sofa_database.py) writes world `mic_pos` directly into `ReceiverPosition`. Applying another listener transform would be wrong for this dataset. Cartesian/metre attributes alone would not establish this exception.

Independent review verified the converter's Git blob `cd03ca06621e64f217599a811e56ac0701b98760`, SHA256 `254dc40b0739944ae727a69e1d6a69288cd59d23d078324593fc1c03d2879631`, and equality of all40 stored receiver positions with the pinned annotation's world microphone coordinates. Only geometry fields were inspected; echo labels never enter fitting. The primary beacon-derived arm is unaffected. This interpretation is specific to the hash-pinned files; do not generalize it to other SOFA data. [Independent review](../../evidence/independent-review-measured-multisource.md).

## Diagnosed failure mechanism, with limits

The mapper's three surfaces have32,22,29 assigned observations and residual RMS64,72,82µs. These small fitting residuals did not prevent unmatched geometry. In a control with the same waveforms but cyclically permuted receiver positions, four unmatched planes still fit. Dense candidate association can therefore produce apparently supported structure even under an intentionally wrong geometry assignment.

Thirty-five of forty captures reach the strongest18-candidate budget. An evaluation-only instrumented copy records candidates immediately before that budget; every returned capped candidate dictionary was checked against the original forty observations and was exactly identical. No changed candidates were supplied to an inverse fit.

Using geometry-generated first-order predictions,78/240 arrivals have a retained candidate within the existing7.5cm path-residual gate, versus163/240 before the budget:85 model-compatible arrivals are removed by the cap. With echo-refined coordinates, the corresponding numbers are89/240 and178/240, with89 removed. These are **model-predicted timing compatibilities, not measured echo labels or recall**. Increasing candidate density also increases accidental compatibility; the85-count difference alone is not proof of recoverable missing information. A missing compatible peak does not establish an absent physical reflection.

All physically ordered single and double room-wall paths were also predicted, with reflection points inside the rectangular room. The ceiling estimate agrees with the ceiling prediction on27/32 original supports, or32/32 with refined coordinates. Only4/22 and5/29 supports on the unmatched planes agree with any predicted first/second room path. No coherent known double-reflection family explains either unmatched plane. This is evidence for mixed/accidental associations under the limited room model; it does not uniquely identify waveform coloration, scattering, metadata error or another cause.

A constant latency per source does not remove all direct-arrival inconsistencies: subtracting each source's median direct timing residual leaves37–221µs RMS with survey poses and17–230µs with refined poses. This is a diagnostic summary only; no latency correction enters fitting. Source-center error and direction-dependent waveform bias remain unresolved.

The useful next research question is how to retain weak spatially useful peaks while rejecting chance associations. Simply raising the peak budget is not supported: the shuffled control already produces false structural certainty. No threshold, pose or model was tuned on this measured evaluation.

## Reproduction

Use the normal pinned project environment plus optional `h5py==3.16.0` for SOFA reading. No new runtime dependency is required by the backend. Commands below create an immutable processing snapshot; the newer evaluation harness stays outside it.

```sh
mkdir -p work/dechorate-core
git archive de8442b2dd088c036d2b92eaeaf29a1273785795 | tar -x -C work/dechorate-core
.venv/bin/python -m evaluation.dechorate_multisource retrieve --workspace work/dechorate-four --core work/dechorate-core
.venv/bin/python -m evaluation.dechorate_multisource prepare --workspace work/dechorate-four --core work/dechorate-core
.venv/bin/python -m evaluation.dechorate_multisource fit --workspace work/dechorate-four --core work/dechorate-core
.venv/bin/python -m evaluation.dechorate_multisource_diagnostics poses --workspace work/dechorate-four --core work/dechorate-core
.venv/bin/python -m evaluation.dechorate_multisource_diagnostics paths --workspace work/dechorate-four --core work/dechorate-core
```

The fit command intentionally exits1 for the frozen failed criterion. An existing isolated h5py installation can be supplied with `--h5py-path`; no automatic installation or bulk archive retrieval occurs. Retrieval verifies exact bytes and pinned hashes and refuses changed existing data. To compare a future core, explicitly select it with `--core`, label its commit with `--core-commit`, and use `--allow-different-core`; that is a new comparison against the unchanged criteria.

Compact original/portable reports, licenses, conventions and support attribution are under `evidence/measured-multisource-de8442b/`. Full original processing outputs and recordings are local under `work/measured-multisource/` and are reproducible with the harness. No data-derived change to the processing core was made.

## Independent review correction

The original evaluator omitted its frozen `forbid_enclosure_claim` gate. The corrected scorer now checks the existing surface contract's exact `extent_status=unknown` and support-hull mesh semantics, as well as every frozen numeric gate. [Three counterexample/boundary tests](../../tests/test_measured_acceptance.py) pass; [re-scoring all21 saved rows](../../evidence/measured-multisource-de8442b/acceptance-recheck.json) leaves every original acceptance decision unchanged. No fitting, threshold or data changed. The original [verification record](../../evidence/measured-multisource-de8442b/verification.json) retains the pre-correction runner hash; the recheck records the corrected runner hash.
