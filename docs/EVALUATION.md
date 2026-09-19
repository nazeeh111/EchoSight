# Evaluation and useful demonstration

The selected useful scenario is surveying room layout and locating consequential early reflectors for room/audio setup. EchoSight should answer which surfaces the sound supports, what separations follow from supported parallel surfaces, and where an additional receiver measurement could distinguish alternatives. It does not establish a closed room, safe free space, finite object edges or material identity.

The central demonstration claim is acoustic recovery of several independent 3D reflectors, including height-dependent structure, from imported recordings with unlabeled echoes. Supplied device poses are calibration. Returned polygons visualize limited supporting reflection regions; they are not surveyed wall outlines. A second measurement can add evidence or resolve an ambiguity. This is useful because a user can relate a problematic early reflection to a physical region rather than seeing only an unexplained peak.

## Frozen acceptance

`evaluation/acceptance.json` was written before any implementation evaluation ran. It fixes development seeds 1–5 and disjoint held-out seeds, scenario requirements, error tolerances and negative controls. Its SHA-256 is included with every run. Truth files are separate from sessions and read only after processing; the inference receives no surface labels or room dimensions.

Three held-out room cases require at least four matched planes each, including a horizontal plane, no false surfaces, normal error at most 5 degrees and offset error at most 0.15 m, in less than 60 seconds per recording-to-result run. Partial observations require two surfaces without unsupported closure. Mismatch requires three surfaces including height information. Coplanar geometry must expose ambiguity or abstain. Direct-only and clutter cases cannot invent surfaces. Invalid nonaffine clock warp must produce diagnostics and no definitive geometry. A tilted interior reflector is an opportunity case, reported even if unsuccessful.

One-to-one matching is invariant to plane-normal sign. Metrics report matched, missed and false surfaces, angular/offset errors, local uncertainty coverage when provided, status and runtime for every case. Misses include geometrically present but acoustically unobserved planes; this is surface recovery, not a claim that every model plane must emit a detectable echo. No-result cases remain in reports. A tiny scenario suite cannot calibrate universal confidence or establish performance in all rooms.

The simple baseline uses one early echo per channel and the correct bistatic propagation model. The serious competitor uses direct plane-grid initialization followed by the same physical refinement/scorer as the main image-source method. Shared observations and scoring isolate initialization/association differences, not an independent implementation validation. Report gains and regressions; a tie does not demonstrate superiority. Mapper time includes signal processing; alternative times reuse its observations and are labeled inference-only.

```sh
python -m unittest discover -s tests
python -m evaluation.run --development --output work/development
python -m evaluation.run --output work/held-out
```

A failed required criterion exits nonzero and remains in `results.json`. Do not change thresholds in response to held-out performance. Investigate failures with independent development cases; a later rerun after a fix is regression evidence on a previously seen set, not a fresh blind test. Reports record code hashes as well as the Git commit because a run may be on an uncommitted working tree.

## External measured-response check

Install optional `h5py==3.16.0` only in the project environment if absent. Raw fixtures are not included in Git. The explicit retrieval option downloads five pinned files, about 8.8 MB in total:

```sh
python -m pip install h5py==3.16.0
python -m evaluation.external --data work/external-data --output work/external --download
```

For an existing local dataset, omit `--download`. Every file must match its original hash and size. The test convolves the generated probe with each complete measured laboratory response, normalizes amplitude and writes PCM WAV. Those WAVs enter the same lossless import/processing route. Their provenance is `replayed` with the measured parent file, transformation and quantization recorded. This is a hybrid experiment; it excludes real playback nonlinearity, actual phone AGC and clock behavior. Collinear array poses require no definitive unique 3D geometry. Finite diagnostics and honest ambiguity constitute success here, not room reconstruction accuracy. No model-generated echo annotation is treated as measured truth.

## Later physical acceptance

1. Record a fixed MacBook source through the chosen lossless iPhone route. Verify actual sample rate, repeated pilot timing, no clipping, no silent format conversion and reproducible direct response. Preserve raw originals and exact source channel/orientation.
2. Use approximately four phones in two placements, yielding at least eight stationary surveyed acoustic-center positions with meaningful height variation. Repeat a position to quantify reproducibility. Source and microphone positions and their uncertainty are supplied inputs.
3. Before collecting evaluation data, freeze extraction/inference and independent survey criteria. Withhold new receiver poses from fitting. Compare predicted delays on them and compare surfaces to independently surveyed physical structure. Report undetected and erroneous structure, not just nearest favorable matches.
4. Test a large movable reflector using A-B-A repeats with unchanged devices, then an independent view. A change in echo energy alone is not object localization. Investigate source directivity/visibility and capture processing before adding unconstrained calibration variables.
5. Test recovery after interrupted upload and cancellation on the actual acquisition route. Hardware acceptance is pending until those measurements exist.

A later frontend demo should show the capture's evidence class first; reveal surfaces with support and uncertainty; expose missing/ambiguous structure; show what a new view changes; state limitations. It should never animate supplied room geometry as though sound inferred it.

## Executed external diagnostic

The initial default-spacing replay accepted 23 of 25 responses. The two rejected channels had a shifted first pilot followed by six uniformly spaced pilots. A separate, explicitly exploratory repeat with the same full responses and 1-second probe spacing accepted all 25, with absolute inferred relative rate error below 0.001 ppm (the hybrid generator has exactly zero clock drift). This isolates inter-probe reverberant overlap as a credible cause of the timing failure; it does not certify general direct-path detection. Both runs return zero definitive surfaces because the five microphones are collinear. Artifacts: `evidence/external-results.json` and `evidence/external-spacing-results.json`. Initial reports predate code-hash instrumentation; later final reproduction must record source hashes.

Reproduce the diagnostic without replacing the default run:

```sh
python -m evaluation.external --data work/external-data --output work/external-spacing --probe-period 1
```
