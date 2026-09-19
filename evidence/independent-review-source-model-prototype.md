# Independent review of the source-model prototype

**Recommendation: retain as an isolated development diagnostic; do not promote the source guard or claim timing robustness.** The prototype's current report correctly identifies its timing-axis stress as an invalid representation. Independent raw evidence confirms that diagnosis. The nominal result remains a useful limited demonstration of competing source explanations, not evidence of improved spatial completeness or consumer-device source qualification.

Reviewed snapshot: [`source-model-diagnostic-trial/`](source-model-diagnostic-trial/MANIFEST.json), manifest content ID `b5de1137125e098c6e546463abb18495585fdbcc48b2c3ed5b7fe3b2c896e417`. All50 manifest file hashes verified. Raw processing source was immutable de8442b; `signals.py` SHA-256 `2fdc6c5d48f8e55efc1650eb52a9ffbc6880e4efa767dbd449900fc38859747f`. No prototype/main edits, old measured-data fits, held-out scene generation or classifier threshold changes occurred.

Independent probes and their predeclared scope: [protocol](source-model-review/PROTOCOL.md), [portable helper](source-model-review/reproduce.py), [raw/analytic results](source-model-review/results.json), [49-delay gain check](source-model-review/gain-results.json), and [algebraic counterexample](source-model-review/gain-algebra.json). The fresh raw probe uses an analytic direct path and one echo, with200ppm then600ppm receiver-clock scale and a separate three-sample raw translation. These checks address representation and objective mathematics, not source-classifier accuracy.

## Consequential findings

### P1: the timing-axis stress does not sample the pipeline's uncertainty

`sensitivity.py:27` changes only `response.start_delay_s` and its sampling rate. `waveform_v3.py:19–22` subsequently divides by the new value at time zero. But `process_recording` defines that zero using the interpolated maximum of the absolute, clock-corrected response itself. An axis-only shift moves the measured peak away from zero while leaving the waveform unchanged. The denominator becomes an arbitrary sample of an oscillatory matched-filter response, potentially negative or near zero.

The independent raw probe quantifies the mismatch:

| Operation | Normalizer at zero | Maximum change in normalized early waveform |
|---|---:|---:|
| Original accepted recording | +0.339109 | reference |
| Raw recording translated by3samples and fully reprocessed | +0.339109 | 2.85×10⁻¹² |
| Original response axis shifted by the same3samples | −0.163548 | 1.64354 |
| Actual recording clock changed200→600ppm and fully reprocessed | +0.327125 | 0.116716 |

The real translation changes the fitted intercept by exactly62.5µs; its normalized response stays invariant. The measured direct peak stays within5.1µs of stored zero after each real reprocessing. The axis-only stress moves it to66.9µs. The clock estimates were1.0002010 and1.0006003, consistent with the two rendering clocks. These are independent new synthetic recordings, not replay of the prototype's nominal counts.

Therefore the reported loss of all32 dual flags under local timing-axis stress is **not evidence that real clock uncertainty destroys the diagnostic**. Equally, reanchoring those already-perturbed axes and recovering flags would not establish physical robustness: pure translation is mostly a coordinate freedom and would be canceled by construction. The branch still lacks a valid timing/anchor uncertainty test.

### P2: clipped gains are not generally the stated bounded optimum

`waveform_v3.py:51–52` and `diagnostic_v3.py:20–22` first solve unconstrained two-component least squares and then independently clip each coefficient. When the two shifted kernels are correlated, clipping one coefficient changes the optimum of the other. This can change profile costs and competitor ranking. Both competitors use the shortcut, but their kernel correlations differ, so that does not make its bias cancel.

A two-column algebraic check gives unconstrained gains(3,−1), clipped gains(2,−1) with squared error1, versus the actual box optimum(2,−0.2) with squared error0.36. This proves the objective discrepancy, not a source-classification failure. A separate49-delay profile check on the fresh physical raw response found **no** objective discrepancy at its optimum; the nominal prototype counts are not shown to be affected. Preserve that negative result.

Exact inexpensive fix before another substantive study: evaluate the feasible unconstrained solution plus the four box edges. For primary gain g₀∈[0,2], secondary gain g₁∈[−2,2], basis vectors a,b and y, let A=aᵀa, B=bᵀb, C=aᵀb, u=aᵀy, v=bᵀy. On g₀=0 or2, minimize with g₁=clip((v−Cg₀)/B,−2,2). On g₁=−2 or2, minimize with g₀=clip((u−Cg₁)/A,0,2). Choose the smallest actual residual among these and any feasible interior solution. Edges include corners; handle zero columns/singular cases explicitly. Use the same vectorized helper in coarse profiles and raw profiles. This is a correction to the claimed nuisance objective, not a new source-model parameter or a threshold adjustment.

## Physical model and evidence checks

The secondary delay is the correct bistatic difference for a constant room-frame displacement Δ:

`τsecondary=(||s+Δ−r||−||s−r||)/v + δdriver`.

The plane model maps the source to its mirror in one fixed plane, and uses the same primary source-to-receiver subtraction. For an infinite first-order plane, same-side source/receiver admission is appropriate. Setting the secondary contribution to zero on an absent plane path, while keeping the primary component, fixes the earlier unfair blanket penalty. This does not model finite edges, occlusion, rough scattering or a direction-dependent filter. The common extra delay is a bounded waveform/phase nuisance; its negative range must not be interpreted as a physically negative propagation time.

The v3 source-diversity check uses source poses that actually support the alternative component on withheld receivers. That is preferable to counting all surveyed source positions when some have no component. Its smallest-singular-value threshold is an engineering guard, not a proof that source and reflector models are distinguishable in every arrangement. Six times the largest scalar source standard deviation does not propagate the full differential-source covariance; a large shared translation, for example, cancels in source diversity. This conservative simplification can lose power and is not calibrated identification probability.

Single, rigid-secondary and plane competitors use the same waveform records and training-only empirical kernel. Secondary and plane have equal4096 Sobol proposals,20 profile refinements and at most3 raw refinements, each bounded70 evaluations. Different parameter domains mean equal counts do not prove equal global optimization quality. Boundary diagnostics help but are not a certificate. A signaled search failure or competitor-boundary solution should not count as proof that the other physical model is absent.

The held receiver partition is held out for global source/plane parameters and kernel learning, but gains and local alignment are fitted on those held waveforms. Call this **held-record profiled compatibility**, not a completely predicted waveform. Source-versus-plane nuisance dimension is equal; source-versus-single differs. The fixed70% MSE and support gates have no calibrated false-alarm meaning.

The learned kernel can contain common reflected or secondary energy inside its±0.75ms support. Median learning reduces varying components but does not establish an independently measured direct kernel. Likewise, normalization removes global polarity/amplitude but does not qualify frequency-dependent acoustic centers or prove the chosen anchor is the primary physical direct arrival. These limitations matter for finite-near-reflector, source-filter and weak-primary cases beyond the current controls.

The immutable nominal report says62 matched/13 false baseline surfaces become38 matched/0 false/24 missed when flagged scenes are cleared. That is suppression of potentially misleading geometry with a large completeness cost, **not improved reconstruction accuracy in every sense**. The output `source_model_ambiguous` appropriately requests source qualification instead of claiming two physical drivers; `not_qualified` appropriately avoids claiming a valid single source. Those semantics should remain if work continues.

Contract limitations are correctly recorded: parsing fixture receiver IDs, assuming rather than validating constant source orientation, missing resource/cancellation handling and unsupported measured driver provenance prevent API promotion. This review did not duplicate the entire nominal classifier suite and does not treat its existing control counts as independent proof.

## Correct timing representation and a bounded next test

Let x(t) be recorded samples interpolated at receiver time and p(u) the emitted pulse. Pilot regression estimates receiver time `tᵣ=αtₛ+β`. Here β includes direct propagation and recording offset; it is not a physical emission timestamp. For pilot start tⱼ, the pipeline forms

`Rⱼ(k;α,β)=corr[x(α(tⱼ+u)+β),p(u)](k)/||p||²`,

then `R(k)=medianⱼ Rⱼ(k)`, locates `d=argmaxlocal |R(k)|` with sub-sample interpolation, and stores time `τk=(k−d)/fs`. The diagnostic's data are `z(t)=R(d+fs·t)/R(d)`.

A slope/intercept perturbation affects the waveform samples **before** correlation. Its first-order raw perturbation is `δx=x′(α(tⱼ+u)+β)[(tⱼ+u)δα+δβ]`. Thus a rate error changes within-pulse shape and differently shifts each repetition; a median across repetitions can smear it. Merely dilating final delay coordinates omits these effects. The anchor d and normalizer R(d) must be recomputed jointly. In continuous source-time notation, normalized-waveform variation is

`δz(t)=[δR(t+d)+R′(t+d)δd]/R(d) − z(t)[δR(d)+R′(d)δd]/R(d)`.

The numerator, denominator and anchor are correlated. `direct_std_s=max(bandwidth floor, repeated-peak SD)` is not an empirically calibrated independent Gaussian translation of z, and does not bound a systematic error from choosing the wrong direct component.

For conditional affine-regression sensitivity, source starts produce design matrix X with rows(tⱼ,1). Under an explicitly assumed pilot-error covariance Σ, use `Cov(α,β)=(XᵀX)⁻¹ XᵀΣ X (XᵀX)⁻¹`; the independent equal-variance special case is σ²(XᵀX)⁻¹, whose slope/intercept cross-term is negative. Either perturb raw receiver time with known physical α,β and re-run the complete extractor, or use jointly perturbed correction parameters on the unchanged raw samples and redo segment interpolation, correlation, median, peak, normalization and training-kernel learning. The latter remains conditional on a pilot assignment; it must not be presented as sampling re-association failures.

A bounded next experiment, if the coordinator proceeds, should freeze before rendering: the same declared source families plus a physically single-source close reflector and direct-null control, independently chosen development draws of sample clock/recording translation/noise, one source pose error draw per source with its existing full joint covariance, and one receiver error per reused receiver group. Re-run the raw pipeline so interruptions, wrong pilot association and rejection are retained rather than conditioning them away. For a deterministic conditional-clock check, use a finite grid of jointly correlated slope/intercept offsets and explicitly label its bounds as assumptions. Rebuild the kernel on training receivers for every accepted raw realization; preserve the held partition and all gates. Report false control flags, lost dual flags, unavailable/rejected cases and every withheld true surface.

Do not reinterpret an absence of flags after reanchoring as validated physical source calibration. If the corrected objective and physically coherent bounded test still falsely flag a qualified control or lose the intended benefit, follow the branch's declared stopping rule rather than expanding parameters or relaxing gates. No such new classifier experiment has been run by this reviewer.


## Portable reproduction of this independent review

The archived50-file source-model snapshot is verified before execution. The helper loads its preserved `waveform_v3.py` and the exact historical `echosight/signals.py` from commit `de8442b2dd088c036d2b92eaeaf29a1273785795`; hashes are enforced. It never invokes the classifier, modifies the prototype, retrieves measured data, or generates held-out cases. The three small analytic/raw probes run in memory and write only their output JSON.

From a full clean checkout with the normal pinned project environment:

```sh
.venv/bin/python evidence/source-model-review/reproduce.py --output work/source-model-review-reproduction
```

The default snapshot is `evidence/source-model-diagnostic-trial/`. The default processing source is read directly from the named Git commit without checkout changes. If using a restored snapshot or an explicitly prepared immutable core archive, select them:

```sh
.venv/bin/python evidence/source-model-review/reproduce.py --snapshot evidence/source-model-diagnostic-trial --core work/dechorate-core --output work/source-model-review-explicit
```

`--core` must contain `echosight/signals.py` with the exact historical hash; a changed implementation is rejected. Neither the original working experiment directory nor its raw fixtures are required. The helper compares all numerical outputs with the preserved review JSON using relative tolerance1e−9 and absolute tolerance1e−10, and exits nonzero on mismatch.

Both direct-Git and explicit-core modes were executed successfully. Each verified50 snapshot files and reproduced all three reference outputs. [Git-source verification](source-model-review/verification-git-core.json), [explicit-core verification](source-model-review/verification-explicit-core.json), and [artifact/original-source hashes](source-model-review/MANIFEST.json) preserve those checks. This repeatability check is not a second independent scientific validation.
