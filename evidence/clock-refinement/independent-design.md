# Independent clock-refinement design audit, frozen before reading results

Scope: read `work/clock-refinement/PROTOCOL.md` first, then current `echosight/signals.py`. Did not inspect development outputs, oracle answers, candidate runner, or result summaries before writing this note. No protocol, threshold, runtime or experiment files were edited. The experiment owner confirmed the protocol/code were frozen before execution; that statement is not independent proof of outcomes.

Inspected bytes: protocol SHA-256 `7e43632f691fd0b0e4db43eb1692f97ce01fc759b05c25567bedb7ffe3314b09`; signals SHA-256 `2fdc6c5d48f8e55efc1650eb52a9ffbc6880e4efa767dbd449900fc38859747f`.

## Main conclusion

The added trigger is a reasonable label-free development experiment, but the unchanged retry winner rule does not establish that the chosen clock is closer to the physical relative clock. It can prefer a more affine wrong peak train and report a smaller `alpha_std`. Aggregate frozen improvement gates do not by themselves exclude that regression. Production promotion needs scrutiny of the already-required per-record clock/uncertainty and negative-control reports; passing aggregate counts alone is insufficient evidence of a safe correction.

## Concrete mechanism

`signals.py:146–148` fits pilot arrivals to `alpha * source_start + intercept`. The retry searches within ±1 ms of that coarse line, selects the nearest retained peak (`165–171`), and adopts a complete retry train solely when its maximum affine residual is smaller (`172–180`). The refinement is not compared on independently held pilot evidence, lobe identity, or correctness of the relative clock. The template and peak thresholds also change before that comparison.

Any train error `delta_alpha * source_start + delta_intercept` lies in the fitted model itself and disappears from the residual. Therefore a smaller residual can coexist with a larger clock error. The ±1 ms search bounds local changes but does not resolve this affine ambiguity. At the protocol's seven starts over a 2.1 s span, hundreds of ppm of coherent rate error fit inside that local search. Peak thresholding may remove the intended peak, after which “nearest” is not evidence of the original lobe. This is a mathematical vulnerability of the selector, not a claim that a particular generated waveform realizes it.

An independent numerical arrival-train example uses starts `0.1 + 0.35 * arange(7)`, true alpha 1.0035, and zero-mean/zero-slope residual shape `[1,-2,1,0,1,-2,1]`. Coarse arrivals contain 10 ppm coherent rate bias and 20 microseconds times that residual shape. Two possible retry trains contain respectively 40 or 400 ppm coherent rate bias and 1 microsecond times the same shape. Applying the implementation's least-squares and uncertainty formulas gives:

| Train | Absolute clock error | Max affine residual | Reported alpha SD | Error / SD | Max distance from coarse fitted line |
|---|---:|---:|---:|---:|---:|
| Coarse | 10 ppm | 40 us | 14.139 ppm | 0.707 | 40 us |
| Retry A | 40 ppm | 2 us | 1.125 ppm | 35.56 | 32.5 us |
| Retry B | 400 ppm | 2 us | 1.125 ppm | 355.59 | 410.5 us |

All three pass the existing 100 us and 5,000 ppm gates; both retry trains lie within ±1 ms and win the residual comparison. The coarse observed displacement exceeds the proposed trigger (3,510 ppm versus 1,041.667 ppm for 40 ms/12 kHz), so an already accepted train would now be exposed to this choice. Retry A does not even count as a >50 ppm “large clock error.” This is an arrival-level counterexample to the acceptance/uncertainty reasoning, **not an end-to-end raw-audio reproduction** or a development answer.

## Consequence for alpha uncertainty

`signals.py:181–188` computes alpha SD from the selected train's RMS residual with a 0.1-receiver-sample floor. It does not represent affine lobe bias, uncertainty in the observed template stretch, or selection of the smaller maximum residual. Reusing the same seven arrivals for stretch, peak selection and winner selection makes a smaller selected residual especially unsuitable as proof of better uncertainty. Even ordinary unselected homoscedastic least squares would estimate residual variance with five residual degrees of freedom rather than seven; the current RMS-based estimate is smaller by sqrt(5/7) when its floor is inactive. That pre-existing factor is secondary to the much larger possible affine/selection bias.

The downstream covariance uses this rate uncertainty, so this is operationally consequential even though the protocol disclaims calibrated 95% coverage. The added trigger does not introduce the old formula, but applies the residual-minimizing selection to previously accepted trains that did not undergo this retry.

## Frozen criteria and negative controls

The protocol appropriately retains exact equal raw inputs, baseline-extraction verification, all rejects, independent seeds, fixed truth matching, no oracle fitting, unchanged gates, and completion despite a failed promotion gate. It explicitly separates nonlinear clocks' nominal affine component from a valid alpha target. These are useful protections.

The following limits remain when interpreting its frozen gate outcomes:

1. “Reduces accepted affine >50 ppm errors” and no increase in **aggregate** common-accepted false/missed paths allow individual regressions to be offset by improvements. They also allow the below-50-ppm uncertainty regression illustrated above. Error/SD is required as a reported metric but has no non-regression promotion condition. Inspect the individual changes and empirical compatibility, not only the gate booleans.
2. Newly admitted weak-direct/warped controls are correctly disallowed. Already admitted negative controls can nevertheless remain wrong or become more overconfident without creating a new admission. The weak-direct guard only searches for earlier alternatives more than 1 ms away (`195–205`), so it is not a general safeguard against within-window lobe changes. The fixed weak-direct family at +6/+12 ms does not alone establish near-lobe safety.
3. “Valid affine” must be interpreted consistently: an affine sample clock does not make weak-direct or nonlinear-source acquisition scientifically valid. Report exact denominators/family membership alongside aggregate counts. The frozen wording does not explicitly define every A/B pool or whether both requested reductions must be strict when a baseline count is zero; retain actual raw counts and avoid favorable reinterpretation after results.
4. The targeted clock grid stops at ±4,500 ppm, so it probes both signs within the existing acceptance bound but does not itself verify out-of-bound ±5,000 ppm rejection. Smooth and step warp controls are valuable examples, not exhaustive interruption coverage. No expansion or threshold change is warranted merely to rescue this experiment.

## Physical alpha convention

Let source actual/nominal rate be kappa_s and receiver actual/nominal rate be kappa_r. Receiver nominal time is `alpha * source_nominal_time + beta`, with **alpha = kappa_r / kappa_s**; beta also includes propagation and launch offset. Stretching a source pulse to `alpha * duration` in receiver nominal samples is dimensionally consistent. Corrected excess delays remain source-buffer seconds; physical seconds require division by kappa_s. The observed slope cannot independently identify physical source rate or sound speed. Nonlinear warp does not have one globally true alpha. The current code's `absolute_source_rate_calibrated=false` and the protocol's nonlinear-clock qualification are appropriate.

The trigger compares `abs(alpha-1) * duration` with half inverse bandwidth, an engineering resolution scale. It is not an uncertainty test. Chirp mismatch also depends on center frequency, taper and channel response, so that resolution argument does not prove the observed-rate threshold is universally sufficient or optimal.

## Bounded disposition before results

Finish the frozen experiment without changing its gates. If any gate fails, close promotion for this candidate as specified; do not adjust the trigger/search/uncertainty to its answers. If all gates pass, the per-record negative-control and uncertainty evidence still determines whether the proposed replacement is supported.

A safe immediate alternative is diagnostic-only recording of coarse/refined alpha and train differences while retaining production decisions. A future separately frozen candidate could preserve multiple local train explanations or test stretch/arrival agreement on held pilot evidence and explicitly account for branch/selection uncertainty. Merely keeping the larger old/new residual SD is not a proof against coherent affine bias, so it should not be presented as a complete repair. These are future design directions, not changes to the running experiment or a recommendation to tune its thresholds.
