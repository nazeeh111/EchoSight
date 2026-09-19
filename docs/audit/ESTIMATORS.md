# Waveform estimator alternatives: development findings

Status: **isolated experiments, not runtime features**. The runtime detector remains unchanged during this study. The serious comparator is a joint sparse fit using a measured direct-path waveform as its local kernel. It improves separable-overlap recovery in development tests but does not solve path-dependent phase, source-model error or measured-scene false surfaces. No FLAIR geometry or laser labels enter any extractor.

## Equal-input development comparison

First freeze: 42 synthetic two-echo cases spanning 150–1000 microseconds separation, two signs and three relative amplitudes; eight cases with common or echo-only 3/4/6/10 kHz lowpass filtering; direct-only and noise controls. A one-to-one 50-microsecond delay-matching criterion counts every unmatched predicted path as false and every missing injected path as missed. Truth enters only scoring, after extraction.

| Method | Overlap true / false / missed | Coloration true / false / missed | Direct-only / noise false |
|---|---:|---:|---:|
| Current matched-filter peaks | 60 / 9 / 24 | 5 / 9 / 3 | 0 / 0 |
| Regularized inverse, regularization 0.1 | 60 / 8 / 24 | 5 / 8 / 3 | 0 / 0 |
| Regularized inverse, regularization 0.01 | 60 / 8 / 24 | 5 / 7 / 3 | 0 / 0 |
| Regularized inverse, regularization 0.001 | 60 / 8 / 24 | 5 / 8 / 3 | 0 / 0 |
| Empirical direct-kernel joint fit | 83 / 1 / 1 | 5 / 2 / 3 | 0 / 0 |
| Joint fit, plus unexplained local waveform-energy guard | 80 / 0 / 4 | 5 / 1 / 3 | 0 / 0 |

[Inverse-filter evidence](../../evidence/audit-physics/deconvolution-development.json), [joint-fit evidence](../../evidence/audit-physics/joint-kernel-development.json), [joint guard evidence](../../evidence/audit-physics/joint-kernel-guard-development.json). The inverse filter offers too little benefit to justify adopting it alone. A remaining joint-fit error is a 52-microsecond bias in the strongest 150-microsecond overlap; the guard abstains there but also loses three additional paths. Path-only lowpass filtering still produces stable biased delays. This is not equivalent to missed temporal resolution.

A second development set was generated after the joint fitter was written, independently of FLAIR: 60 cases, seed 20261021, random fractional offsets, ±500 ppm clock rates, 180/250/500-microsecond spacing, varying echo sign/amplitude and three noise levels. The original extractor recovered 82/120 paths, with 11 false and 38 missed; both joint variants recovered 120/120, with no false or missed paths. Total extraction time was 0.327 seconds original versus 0.444 seconds joint on this machine. [All cases and failures](../../evidence/audit-physics/joint-kernel-robustness.json). These are development results, not a newly frozen independent acceptance suite or confidence calibration.

## What the comparator actually fits

The exported signed response is a matched-filter response, not a full-band physical impulse response. Take its observed direct-path kernel within ±0.8 milliseconds, normalize its amplitude, and model the response as a sparse sum of continuously shifted, signed copies. Start with the direct contribution; repeatedly choose the largest remaining residual peak, then jointly optimize all selected delays and linear amplitudes. Each nonlinear optimization is bounded around its initial delay. Stop at the original 7% peak threshold or 18-path budget. The candidate neighborhood resolution is `2 / bandwidth`; no pose, plane, room shape or expected echo time enters this fit.

The local residual guard evaluates the signed residual after accounting for all fitted neighboring kernels, within the nominal `1 / bandwidth` mainlobe. It marks a candidate unmodeled if more than half the local waveform energy is unexplained. This differs from the rejected simple waveform guard: valid neighbors are explicitly fitted first. Nevertheless, a low residual cannot prove a correct propagation delay. A pure additional phase delay looks exactly like additional distance, and sufficiently flexible multipath can explain a filtered waveform incorrectly.

The candidate requires further engineering before runtime adoption: qualify direct-kernel isolation; recover per-repetition support rather than assigning it from a median response; propagate shared direct-kernel and timing uncertainty; make cancellation and resource bounds explicit; and challenge against the unchanged frozen and independent stress suites. Do not copy the experimental output's timing floor into a claim of calibrated joint-fit uncertainty.

## Measured FLAIR diagnosis, after development

The fixed pre-audit solver at commit `1c773367f787a551aec0f15fc244b5fe9290dee3` was given identical 24 receiver poses and either original or joint-fit candidate lists. The third comparator extracts peaks from the original measured broadband RIR. That comparator has additional waveform bandwidth and is **diagnostic, not an equal-input backend alternative**. Laser annotations were opened only after all candidate extraction finished.

| Candidate source | Geometric matches | Unmatched returned surfaces | Matched horizontal surfaces | Floor / ceiling median nearest-path errors |
|---|---:|---:|---:|---:|
| Original matched filter | 3 | 7 | 1 | 64 / 85 mm |
| Joint direct-kernel fit | 5 | 5 | 2 | 62 / 83 mm |
| Original broadband RIR envelope | 2 | 8 | 1 | 57 / 72 mm |

[Complete diagnostic and limits](../../evidence/audit-physics/flair-estimator-diagnostic.json). These are post-development diagnostics on already exposed measured data, not a new blind test. Every method fails the frozen zero-unmatched-surface criterion. A label-matching increase is not enough to qualify the estimator. The floor/ceiling mismatch persists even in the original RIR, so matched-filter autocorrelation is not its sole cause. Inference from this experiment: candidate overlap is partly recoverable, while model bias, propagation-order association, missing paths and source/material phase still need separate treatment. The data do not isolate one of those as the sole cause.

## Reproduction

The exact experimental scripts are in [`estimator-experiment`](../../evidence/audit-physics/estimator-experiment/). From the repository root:

```sh
mkdir -p work/physics-estimator
cp evidence/audit-physics/estimator-experiment/*.py work/physics-estimator/
git show 1c773367f787a551aec0f15fc244b5fe9290dee3:echosight/signals.py > work/physics-estimator/baseline.py
OPENBLAS_NUM_THREADS=1 .venv/bin/python work/physics-estimator/development.py
OPENBLAS_NUM_THREADS=1 .venv/bin/python work/physics-estimator/development_joint.py
OPENBLAS_NUM_THREADS=1 .venv/bin/python work/physics-estimator/development_joint_guard.py
OPENBLAS_NUM_THREADS=1 .venv/bin/python work/physics-estimator/robustness.py
```

The FLAIR script additionally expects the documented subset at `work/audit-data/flair-subset/subset.npz`, the baseline FLAIR result/session/laser-annotation artifacts at `work/audit-flair-baseline/`, and the fixed source snapshot at `work/audit-baseline/` with its `EVALUATED_COMMIT`. It never retrieves additional data. Source/data hashes in the report and subset manifest identify the material used. Preparing those artifacts uses the existing bounded retrieval and FLAIR evaluation commands; no raw RIR or laser data are committed here.

## Isolated integration trial on 659099f

The next trial adds an explicit `process_recording(..., estimator='joint_kernel')` option in an isolated source snapshot. `matched_filter` remains the default, unknown names are rejected before signal allocation, cancellation is checked inside optimization, and per-repetition support is evaluated rather than inferred from a median response. Its structural bounds are 18 paths, 15 nonlinear evaluations per added path, at most 16 repetitions and at most 200 milliseconds of response samples. Four dedicated tests check overlap recovery, unknown-option rejection, cancellation during fitting, and rejection of an echo supported in only four of seven repetitions; these and the 15 existing signal tests pass. The trial exports repeated-fit covariance as experimental diagnostics. It is **not yet propagated into geometry as a full joint timing covariance**, so no new uncertainty-calibration claim follows.

Both estimators were run through the same frozen suites in this snapshot. Every raw WAV is byte-identical between paired runs: 90 files in the original suite, 65 extended, 156 stress and 24 FLAIR. All source snapshots stayed unchanged during their respective runs. Acceptance criteria were unchanged.

| Suite | Original true / false / missed | Joint true / false / missed | Acceptance |
|---|---:|---:|---|
| Frozen original eight-view suite | 27 / 0 / 19 | 30 / 0 / 16 | Both pass |
| Frozen extended twelve-view suite | 25 / 0 / 0 | 25 / 0 / 0 | Both pass |
| Harder stress suite | 30 / 0 / 48 | 32 / 1 / 46 | Both fail; joint adds a null-control regression |
| Measured FLAIR, conservative 659099f inference | 0 / 0 / 10 | 0 / 0 / 10 | Both fail required spatial recovery |

[Complete paired comparison](../../evidence/audit-physics/joint-integration-comparison.json), [full results and exact experimental source](../../evidence/audit-physics/integration-trial/). The joint fitter recovers both overlapping-plane stress cases fully (7/7 each), but produces **one false definitive plane in diffuse-null seed 673**, where the original returns none. This blocks promotion. It is not a waveform sidelobe: seven independent random-clutter paths accidentally support a plane with 36.9 mm RMS path residual. Better extraction exposes a weakness in the fixed clutter/association objective after many hypotheses are searched. Removing genuine detected peaks to hide this regression would not repair the underlying inference. The next justified investigation is a density-aware clutter comparison or genuinely independent validation views, with the same frozen acceptance retained.

The measured FLAIR run remains ambiguous, with no definitive geometry, under the conservative 659099f propagation-order checks. More overlap resolution does not solve its floor/ceiling timing mismatch. Two joint-fit overlap stress surfaces also fall outside their reported local normal-angle 95% intervals, despite correct geometric matches. That is further evidence that the present uncertainty model needs the joint-fit covariance and model-bias treatment before adoption.

To reproduce this isolated integration, archive commit `659099f` into `work/physics-joint-trial`, then copy the two experimental modules from `evidence/audit-physics/integration-trial/` into that snapshot's `echosight/`, its test into `tests/`, and `evaluate_estimator.py` into the snapshot root. From there, run the existing interpreter with `evaluate_estimator.py --estimator matched_filter` and `--estimator joint_kernel`, selecting `--suite eight`, `twelve`, `stress` or `flair` and separate output directories. FLAIR also requires `--subset` pointing to the licensed retrieved subset. This reproduction leaves the active runtime unchanged.

## Closed recording-level combination

A search-aware held-view guard was compared on the same raw bytes with both extractors. Joint extraction plus guard removes the diffuse-null false plane but changes twelve-view25/0/0 to22/0/3 and stress30/0/48 to29/0/49 (true/false/missed). FLAIR remains0/0/10. Frozen acceptance still fails, so neither this combination nor an API option is promoted. [Full four-arm evidence and reproduction](../../evidence/audit-physics/recording-guard-trial/README.md) preserve losses, source hashes and13focused checks.
