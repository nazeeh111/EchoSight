# Evaluation and useful demonstration

The selected useful scenario is surveying room layout and locating consequential early reflectors for room/audio setup. EchoSight should answer which surfaces the sound supports, what local separations follow from supported surfaces, and where an additional receiver measurement could distinguish alternatives. It does not establish a closed room, safe free space, finite object edges or verified physical material identity. Version 0.2.0 separately compares reflection features with supplied reference profiles; see the controlled material demonstration below.

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

A further direct-reference diagnostic compares detected direct arrival with supplied source/receiver distance divided by the declared sound speed plus probe lead. On the 1-second replay the source-1 differences were 0.29–0.43 ms, source-5 in `000000` 0.41–0.85 ms, and source-5 in `011111` 2.61–5.58 ms. Stable pilots therefore do not certify a correct direct-path reference. Dataset/system latency and source-dependent obscured or weak direct sound remain possible; these are model-compatibility residuals, not errors against independently timed echo labels. The collinear geometry gate prevents a false unique map here. On future nondegenerate measured captures, direct reference qualification remains essential. The external runner now includes these residuals explicitly after processing, without using them to pick peaks.

The subsequent direct-reference gate detects substantial repeatable energy before the selected reference and abstains instead of relabeling it as a valid direct arrival. Baseline instrumented runs accept 20/25 waveforms at either spacing, but the rejected channels differ. At one-second spacing all five `011111/source5` responses are rejected. At default spacing four are rejected; its fourth channel remains accepted with a 5.58 ms direct-arrival model discrepancy, while one `011111/source1` channel is rejected. The prior claim that all five difficult channels were rejected at either spacing was incorrect and is superseded by this per-channel audit. Four files remain geometrically ambiguous; that source-5 file returns no result. This is a more honest failure boundary, not improved measured reconstruction. `evidence/external-final-default.json` and `evidence/external-final-spacing.json` record exact source hashes and confirm that code stayed unchanged during each run. The earlier 23/25 and 25/25 exploratory records remain available as the evidence that exposed the issue.

## Additional acquisition and guidance

Twelve surveyed views (approximately four phones at three stationary placements) are a concrete improvement over the initial eight-view arrangement. Before any new extended held-out evaluation, `evaluation/acceptance_extended.json` separately freezes three new room seeds requiring all six room planes, both horizontal surfaces and zero false surfaces, plus a clutter control. It does not replace or edit the original eight-view benchmark. A tilted reflector case is retained as a reported opportunity with a seven-surface target. Development cases showed six room surfaces consistently, while the tilted reflector remained dependent on visibility and association support.

```sh
python -m evaluation.run --extended --output work/held-out-extended
python -m evaluation.guidance --output work/guidance
```

The guidance experiment ranks proposed receiver positions using competing hypotheses before reading truth. It then independently renders an additional recording at the selected position and a same-height control, and sends both through the ordinary pipeline. A global ambiguous scene keeps `surfaces` empty; invariant supported planes are reported separately as hypotheses. The evaluation reports that evidence separately, so a partially resolved ambiguity is not relabeled as a wholly resolved room. Predicted separation is conditional on audible echoes and supplied calibration, not a promise that an operator can place a phone there or hear a given reflection.

## Frozen results

The frozen runs completed at repository checkpoint `965c0cfc09bdf02576af0d0a19f58c436ffe4e70` with exact working-source hashes in their reports and `source_unchanged_during_run: true`. Both original and extended mandatory criteria passed without changing thresholds or held-out seeds. A later integrity-only pipeline change can require a recorded reproduction; the source hashes specify exactly what these results verify.

| Case | Views | Main matched / present | False main surfaces | Serious plane-grid competitor |
|---|---:|---:|---:|---:|
| Rooms 101, 107, 113 | 8 each | 5/6 each | 0 | 5/6 each |
| Partial 127 | 8 | 3/3 | 0 | 3/3 |
| Mismatch 149 | 8 | 4/6 | 0 | 4/6 |
| Tilted-reflector scene 151 | 8 | 5/7 | 0 | 5/7 |
| Rooms 211, 223, 227 | 12 each | 6/6 each, including floor and ceiling | 0 | 6/6 each |
| Tilted-reflector scene 233 | 12 | 7/7, including the tilted plane | 0 | 6/7 |
| Direct-only 137, clutter 139/229 | 8 / 12 | No surfaces, as required | 0 | No surfaces |
| Coplanar 131 / warped clock 157 | 8 | Ambiguous / no result, no definitive surfaces | 0 | Same abstention |

The simple earliest-echo baseline matched no true surfaces and generated one false plane on the extended tilted case. The serious competitor tied the main method on most cases and missed one tilted plane the main method recovered; this small comparison supports that specific gain, not general dominance. Its timing excludes shared extraction, so totals are not direct end-to-end speed comparisons.

Across matched main surfaces, the maximum offset errors were 17.3 mm in the eight-view suite and 14.4 mm in the twelve-view suite; maximum normal errors were 0.61 and 1.50 degrees. Every reported 95% local offset interval covered its matched plane (27/27 and 25/25). Those conditional intervals and small synthetic counts do not establish 95% coverage on physical rooms. All main recording-to-result runs took less than 0.8 seconds on the local test machine. Geometry does not imply full room enclosure or known physical edges even when six model planes match.

Frozen reports: `evidence/frozen-held-out.json` and `evidence/frozen-extended-held-out.json`. The original eight-view misses remain visible. The twelve-view scenario uses additional information rather than pretending those misses disappeared in the original acquisition. Development tilted cases 2–4 still missed the tilted plane, so its detectability is explicitly conditional.

The final exploratory guidance recording comparison (`evidence/guidance.json`) selected a receiver 0.8 m above the original plane. The added recording yielded five supported invariant plane hypotheses and one unresolved mirror pair; a same-height added recording yielded no invariant plane hypotheses and four unresolved mirror pairs. Both outputs retained the global `ambiguous` status and empty definitive `surfaces`. This demonstrates partial information gain rather than claiming a single extra recording always resolves a room.

## Baseline clean-checkout reproduction and reopened audit

Commit `1c773367f787a551aec0f15fc244b5fe9290dee3` reproduced all69 tests, both frozen suites, guidance and both external replay settings from a separate GitHub clone. Reports are `evidence/reproduced-*.json`, with setup/code/runtime fingerprints in `evidence/final-reproduction.json`. These are regressions on already-seen frozen cases, not new blind tests. Earlier reports remain preserved. This checkpoint is a baseline research prototype; the [coverage audit](audit/COVERAGE.md) identifies missing physical-model and measured-spatial evidence.

## Controlled material and appearance development check

```sh
python -m evaluation.material_development --output work/material-demo
```

This additional recording-to-result check learns two synthetic reference-filter profiles from distinct raw reference sessions, then processes independent room and null recordings. Query truth is read only after all query results are saved. It checks six surfaces including height, both reference classes with no wrong estimates in this case, explicit unknowns for insufficient usable views, training reuse and out-of-domain inputs, and original-input preservation. The output `summary.json` retains all decisions. Settings, seeds and raw byte hashes are written alongside the inputs. Direct and reflected amplitudes obey the explicitly declared inverse-distance pressure model; the older geometry simulator is not used as material-training truth.

This is a controlled development demonstration, not a held-out building-material benchmark. Three of six room surfaces remain material unknowns under the fixed guards. Color palettes are supplied contextual priors. It does not change the existing frozen geometry criteria or external-data failures, qualify physical probabilities, or measure optical color. See [material assumptions and qualification](MATERIALS_APPEARANCE.md).
