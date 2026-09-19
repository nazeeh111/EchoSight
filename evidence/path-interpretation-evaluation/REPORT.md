# First frozen raw comparison: de8442b

The updated experimental mapper improved path interpretation but **failed the frozen mismatch requirement**. No criteria changed. The run returned exit 1 because both two-emitter cases retained false geometry; all 36 method executions completed without operational errors. All 576 unique recordings remained byte-identical across the three methods.

| Method | True surfaces | False surfaces | Missed surfaces | Failed cases | Median / maximum seconds | Peak process memory |
|---|---:|---:|---:|---:|---:|---:|
| Original be5c70a mapper | 38 | 8 | 0 | 6/12 | 1.209 / 2.655 | 145.1 MB |
| Updated de8442b mapper | 38 | 4 | 0 | 2/12 | 1.884 / 4.511 | 142.3 MB |
| Updated direct-grid competitor | 29 | 1 | 9 | 2/12 | 1.802 / 4.316 | 154.2 MB |

The grid's lower false count comes with nine misses, including one real surface in the first panel case and eight surfaces across the two-emitter controls. Its complete no-result at two-emitter1307 is permitted by the frozen mismatch gate but still misses six true room surfaces. It is not an unqualified winner.

The updated mapper preserved all six room planes and all seven room/panel planes at both seeds, including both horizontal planes. Both diffuse controls returned no result and no compact-location modes. At both ideal-point and dispersive-point seeds, the original mapper returned one false plane. The update retained a compact-location hypothesis and no definitive plane instead. Location errors were 5.3, 27.2, 9.6 and 27.1 mm. All four generating locations fell inside the declared conditional ellipsoids, which is not enough evidence to establish 95% calibration. Those hypotheses remain conditional on the selected path, model, calibration and bounded search.

Both two-emitter cases return six correctly matched planes plus two false duplicate surfaces, unchanged by the new interpretation check. Their per-surface physical fit residuals are only 3.8–13.4 mm. Good geometric residuals therefore do not establish the source model or physical reality of an additional surface.

## Failure mechanism

For plane normal n and offset d, reflection of source s is Hs+2dn, H=I−2nnᵀ. A rigid secondary emitter at s+δ gives Hs+Hδ+2dn. When δ=a n, Hδ=−a n, so this equals reflection of the declared source in the shifted plane d′=d−a/2. Relative to the primary direct path, the entire secondary wall-path family is exactly aliased by that shifted plane. More receiver poses or the existing four translated source positions cannot resolve this wall-path alias by themselves.

The four unmatched outputs are duplicates of already recovered y-normal walls, offset 112–123 mm, close to half the 240 mm source separation. Evaluation-only nearest-path annotation shows 40/41, 40/41, 40/40 and 32/33 support arrivals match the secondary emitter's corresponding wall reflection when referenced to the primary direct path, with 4–22 microsecond RMS delay error. These annotations did not enter fitting. One-to-one matching properly counts the extra copies as false even though each lies within 15 cm of an already matched real wall; merging all nearby planes would conceal real close reflectors and is not justified.

The raw response contains information that may distinguish the source alternatives. Across receiver bearings, the secondary direct arrival is −0.70 to +0.66 ms relative to the primary; it precedes the primary in 59/96 recordings. All pairs fall inside the current one-millisecond earlier-path exclusion guard. In 47/96 recordings, their separation is below the current 350-microsecond peak-list cutoff. The strongest local reference generally tracks the louder primary, not necessarily the earliest geometric arrival. The full signed 48-kHz response at 2–14 kHz, including about four milliseconds before the chosen direct reference, remains available for reprocessing; the reduced peak list loses part of this information.

Five of 96 two-emitter recordings are already rejected for timing consistency. Among accepted recordings, the maximum estimated recorder-rate error is 40.6 ppm at1301 and 2.2 ppm at1307; one accepted1301 record is beyond three reported slope standard deviations. All other families have maximum errors below1.3 ppm and none beyond three reported standard deviations. `clock-diagnosis.json` distinguishes accepted observations from the initial all-record diagnostic, whose larger errors include recordings the backend correctly rejected. No new clock or acquisition accuracy claim follows from these synthetic controls.

## Single highest-value next experiment

Investigate early-waveform source qualification on new development fixtures, with no changes to these held-out gates or results. Compare a single emitter, a rigid secondary emitter `q(s)=s+δ` with an optional fixed driver delay, and a genuine fixed near-reflector whose image is `q(s)=Hs+2dn`, using identical raw recordings and known probe only. Fit early signed response windows with shared bounded waveform nuisance filters, rather than supplying perfect delay labels. Retain the possibility that phase/directivity variation prevents identification.

Use all four source positions spanning three dimensions, fit only a declared subset of receivers, and compare prediction on withheld receiver bearings. Source translations change a rigid secondary source with the identity transformation, whereas the virtual source of a fixed plane changes with reflection H. This difference, and negative secondary-direct delays at some bearings, provides potentially discriminating evidence independent of the aliased wall reflections. Hold device orientation fixed in this first experiment; an eventual physical route requires orientation/source-routing information or recalibration.

Freeze new development families and tests before rendering: single-source rooms; rigid two-emitter rooms spanning direction, relative gain, separation and small driver delay; single-source rooms with real close reflectors; and source-filter/low-SNR controls. Require retention of every baseline-supported real room/near-reflector surface on the single-source controls and no spurious source diagnosis there. Any source qualification must predict withheld early waveforms better than both the single-source and near-reflector competitors, survive the declared noise/filter mismatch, and reduce false extra geometry without consuming unseen answers. If models remain indistinguishable, return an explicit source-calibration ambiguity and specify separately routed playback as the next hardware measurement. Do not add a geometric merge or a blanket delay cutoff to hide the aliases.

## Evidence and reproduction

`results.json` retains all36 scored results, residual comparisons, modes, runtime, memory, candidate counts, commit IDs and raw checks. `summary.json` provides paired deltas. Full individual exports and annotations are under `heldout/`; `execution-plan.json` was written after rendering the entire corpus and before fitting. `freeze.json`, `environment.json`, renderer checks, `two-emitter-primary-reference-diagnosis.json` and `clock-diagnosis.json` provide exact code, source, calibration and diagnostic provenance.

The frozen input parameters yielded high SNR, roughly60–64 dB active in development. The inherited specification's initial “moderate noise” wording is not supported by that measured value. This is synthetic geometry and phase-filter evidence only: not measured furniture, diffraction, realistic full-wave scattering, iPhone accuracy, or physical validation. Point-location capability outside these idealized/high-SNR surrogates remains unestablished. No fitting or threshold adjustment followed these results.
