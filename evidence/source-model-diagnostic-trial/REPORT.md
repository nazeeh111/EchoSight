# Early-response source-model diagnostic: independent review required

**The nominal guard removes13false surfaces by withholding24true surfaces. It is not a mapping-completeness improvement and is not ready for promotion.** The isolated experiment leaves the backend unchanged. The original raw held-out comparison still fails both two-emitter cases; none of those results or criteria changed.

The purpose is a conditional source-calibration warning when the declared single-source model cannot explain early recordings. A positive output does not prove two physical drivers. A negative output does not establish a single acoustic center or calibrated source.

## What was executed

All cases use actual generated PCM recordings imported through immutable de8442b; no ideal delay labels enter fitting. Four constant-orientation translated source poses,12receiver poses,48recordings percase. The same supplied poses/full covariance, signed estimated responses, training/held split and search budget feed the rigid-secondary and fixed-near-reflector models. Kernels are learned from32training responses;16withheld receiver responses evaluate prediction. Truth is used only after fitting for geometry/source error scoring.

V1 at seeds2401/2411 searched20waveform starts. It flagged no source case and removed no false geometry. A separately labeled, post-fit true-parameter cost showed that the waveform objective contained useful information but the search missed it. Those oracle parameters never initialized subsequent search.

V2 used4096label-free Sobol profile starts,20bounded profile refinements and at most3full-waveform refinements for EACH competitor. It flagged all four two-emitter cases, but also rejected a real near-reflector control, withholding seven true surfaces. The false flag's actual component support came only from three same-height sources; the fourth height-changing source had no audible component in the early window. Overall source rank was insufficient evidence. Some fixed-plane searches also used an inappropriate blanket invalid-path penalty. All V1/V2 failures remain preserved.

V3 corrected per-record physical absence to zero reflected contribution and required strong component support at every source, with a minimum supported-source singular value. These are engineering conditioning gates, not identification probabilities. It reused the12development cases, then ran12fresh DEVELOPMENT cases at2423/2437, rendered before any v3 fitting. No acceptance threshold was weakened.

| Fresh development, twelve cases | True surfaces | False surfaces | Missed surfaces |
|---|---:|---:|---:|
| Immutable baseline |62|13|0|
| Conditional source-needed guard |38|0|24|

All eight qualified single-source/near-reflector/null/filter controls retained their baseline geometry, including all seven near-reflector surfaces at both fresh seeds. All four dual-source cases were flagged. Their fitted offset errors were0.83–1.88mm, and held waveform error was4.6–26.6%of the single-source error. This narrowly demonstrates synthetic waveform compatibility, not physical source localization. All dual-source scenes still use one fixed room-frame displacement, relative gain and driver delay; the phase mismatch is one chosen FIR. This is not broad coverage of real devices, directionality or low SNR.

Median added computation was0.760s, maximum0.900s percase on this host. The diagnostic has not received production resource/cancellation/input-admission hardening. Acquiring the demonstrated inputs would require48recordings across four source positions and12receiver positions, with constant device orientation and surveyed coordinates. Four phones could cover those receiver positions through three placements; that extra calibration burden is substantial. Correctly routed single-emitter playback remains a potentially simpler acquisition alternative requiring physical verification.

## Declared nuisance sensitivity and its representation limit

Eight paired local draws per fresh case retained the complete source12x12covariance, receiver-group reuse and effective-speed uncertainty. With geometry/speed perturbations alone, all32dual-source fits remained flagged and all64control fits remained unflagged. This is a small local sensitivity result, not a covariance-coverage estimate.

The paired timing stress shifted/scaled the stored response axes using direct_std_s and alpha_std/alpha. All32dual flags disappeared, and all64controls remained unflagged. Waveform-ratio failure occurred in32/32; component support/conditioning additionally failed in15/32. In each dual draw,7–22of48reference shifts exceeded the prototype's ±2sample alignment domain. The observed direct timing floor was approximately41.7microseconds, while that domain itself is only ±41.7microseconds.

**Those0/32flags are a preprocessing/invariance diagnostic, not a physically coherent simulation of recorder-clock error.** The extractor defines response time zero at its chosen direct maximum. The stress shifted the stored axis without jointly recomputing that anchor and its receiver-time metadata, so it violated the extracted representation. The prototype's normalization y(0) and unregistered median-kernel learning are sensitive to such shifts. That is evidence about input-contract/preprocessing assumptions, not demonstrated failure of real-device timing correction. The rate-axis perturbation also does not reproduce the seven raw repeat windows' jointly estimated slope/intercept covariance. Direct_std_s includes an engineering resolution floor and is not an established Gaussian phase-shift distribution.

No uncertainty was reduced to recover favorable output. No extra search/gate iteration follows this test. Independent review must decide whether inconsistent response axes should be rejected as malformed, whether a coordinate-consistent nuisance transform exists, or whether raw waveform reprocessing is required. A candidate preprocessing change is to register and normalize each response at a consistently defined observed anchor before learning a shared kernel, then profile residual alignment with a declared uncertainty model. Reanchoring alone does not prove physical robustness. Real timing qualification must perturb/re-estimate the source-buffer to receiver-time map, slope/intercept covariance and direct anchor together while preserving the extractor's relative-time contract, or derive a valid equivalent transformation.

## Signed normalization assumption for independent review

The actual extractor calls its array `envelope`, but constructs it as the absolute value of the REAL signed matched-filter response, not a Hilbert analytic-envelope magnitude. It selects the largest absolute sample in the direct window, then applies a parabolic interpolation to those absolute samples. Consequently, the declared zero is a refined absolute-peak location, not a proven extremum of the signed continuously interpolated response. The prototype then normalizes each entire response by the signed linearly interpolated value y(0), rejects |y(0)|<.002, and takes a training median. Positive primary gains and the shared empirical kernel depend on this anchor/polarity convention.

There is no explicit lower bound proving that y(0) remains large relative to direct-window energy after that absolute-peak interpolation. Algebraically, signed neighboring samples[0,1,-.99] have absolute samples[0,1,.99], whose parabolic peak shifts about.490sample toward the negative neighbor; linear signed interpolation there is only about.0248despite an integer peak of1. This is an interpolation counterexample, not a rendered physical2–14kHz failure. A physical dispersive/phase-sensitive counterpart has not been demonstrated here and must not be asserted. Conversely, strong energy alone does not establish the normalization assumption. Independent review should distinguish this potential physical/representation sensitivity from the already identified invalid-axis stress. Do not silently replace signed normalization, use an analytic envelope, shrink the timing budget or claim an alternative is safe without a waveform-derived check.

## Review and integration recommendation

Do not promote v3 or expose a public mapping capability. Review the immutable source/evidence snapshot first, specifically response-axis semantics, whole-mixture alignment, training-kernel normalization, fixed-plane physical absence, component-specific source conditioning, unknown driver delay/orientation, and all geometry withheld. `CONTRACT.json` makes assumptions and missing production work explicit.

If those issues are resolved with independent evidence, the only supported integration direction is an experimental multi-source **source-calibration-needed diagnosis** that preserves raw recordings, reports alternatives and withholds definitive geometry honestly. It must not silently correct the source, merge nearby planes or claim that the remaining geometry is physically established. A qualified negative result cannot remove the existing source-model warning.

Seeds2401/2411 and2423/2437 are exposed development. Original1301/1307 are exposed held-out and remain unchanged. Proposed2609/2621 have not been generated in this work and could be used only after freezing a broader independent acceptance design. That design should vary offset direction/magnitude, gain, driver delay, orientation handling, frequency response, overlap and SNR, and preserve real close-reflector controls. No new unseen data should be used to choose the next implementation.

## External-data control limits

The evaluation specialist inspected eight selected dEchorate SOFA files: source description is “Directional Avanton MIXCUBE.” The2021primary paper describes four distinct directional loudspeakers facing the center and sequential excitation, not a single translated unit with demonstrated constant orientation. Manufacturer documentation for a current passive MixCube variant describes one5.25-inch full-range assembly, but the dataset's exact variant, acoustic center and active-driver/routing details remain unverified. These recordings are not a qualified negative control for this constant-orientation moving-source diagnostic. FLAIR's emitting hardware is also unverified; source-position annotations alone establish neither driver geometry nor routing. No measured-data source-classification result is claimed.

Provenance pointers: `backend/work/measured-multisource/metadata-audit.json`; dEchorate paper DOI[10.1186/s13636-021-00229-0](https://doi.org/10.1186/s13636-021-00229-0); manufacturer[passive MixCube](https://avantonepro.com/en/products/mixcube-passive), which does not resolve the dataset model variant; FLAIR DOI[10.1109/TASLPRO.2025.3619822](https://doi.org/10.1109/TASLPRO.2025.3619822), detailed hardware not verified here.

## Evidence

- `run-v1/{freeze.json,results.json,search-diagnosis.json}`: first failed search and separately labeled truth-parameter diagnosis.
- `run-v2/{freeze.json,results.json,component-support-diagnosis.json}`: broader search and failed real-reflector control.
- `run-v3/{freeze.json,execution-plan.json,results.json,compact-summary.json}`: frozen source hashes, full fresh corpus fingerprints, replay/fresh results and complete geometry accounting.
- `run-v3/{sensitivity-freeze.json,sensitivity-results.json,sensitivity-diagnosis.json}`: all192nuisance fits, gate-by-gate losses and representation-domain audit.
- `math-checks.json`, `profile-checks.json`, `v3-math-checks.json`: analytic propagation, signed gain/alignment, profile/full-waveform equivalence and absent-path checks.
- Raw earlier fixtures: `run-v1/cases/`; fresh fixtures: `run-v3/fresh/`. Each manifest records every PCM hash; all scored runs verified unchanged raw bytes. The generated files are local test data, not own-device measurements.
