# Source-model information audit

2026-09-19. Bounded analytic audit only: no detector implementation, no microphone or phone activity, no held-out answers, no main-code changes. Numerical checks are `check.py` and `nuisance_checks.py` in this directory; results and complete surveyed coordinates are in the corresponding JSON files. They use new analytic seed 27119 and installed NumPy/SciPy.

## Result

A rigid secondary emitter and a plane reflection are exactly indistinguishable when all source moves are tangent to that plane, provided the secondary displacement equals the original image displacement and its relative driver delay matches the path-delay convention. This ambiguity holds for arbitrarily many well-spread receivers; another receiver cannot resolve two models that have exactly the same virtual source.

Two source positions can distinguish a **specified** candidate plane if their displacement has a measurable normal component. Four noncoplanar source positions remove the universal tangent-plane ambiguity under a fixed-orientation rigid-emitter model, but rank three alone does not establish useful separation. Unknown orientation, placement-dependent driver delay, narrow receiver bearings or weak normal displacement can restore exact or practically unresolved alternatives.

## Observables and clocks

Let `s_a` be the primary acoustic-center position at source placement `a`, `r_aj` the receiver acoustic center, `R_a` the source-body orientation, `δ` a rigid secondary-emitter offset in the body frame, and `τ_b` its relative driver delay in **source-buffer seconds**. The secondary emitter is

`q_E,a = s_a + R_a δ`.

For a plane `n·x=d`, with unit `n`, define `H=I−2nnᵀ` and its source image

`q_P,a = Hs_a + 2dn`.

With effective speed `v=c/κ` in metres per source-buffer second, the direct-relative observables are

`μ_E,aj = (‖r_aj−q_E,a‖ − ‖r_aj−s_a‖)/v + τ_b`,

`μ_P,aj = (‖r_aj−q_P,a‖ − ‖r_aj−s_a‖)/v`.

An optional common phase/group-delay offset for the plane model enters identically to a scalar `τ_P,b`; then only the difference between the two scalar offsets matters for discrimination. A dispersive, angle-dependent response is not generally represented by one scalar delay and is outside this derivation.

Receiver affine clock offsets cancel when the same capture's correctly identified primary direct arrival is subtracted. Relative recorder rate must still be estimated from known probe timing; warp must be bounded or diagnosed. An unconstrained offset on each *already direct-relative* observation can force either model to fit anything. An unconstrained per-record rate can likewise destroy range information. Neither freedom is justified merely because independent phones have unsynchronized clocks. If the direct reference was actually the second emitter, these equations use the wrong primary reference; that must be treated as another model/diagnostic rather than silently absorbed.

`τ_b=κ τ_physical` for a physical driver delay. A supplied nominal sample rate or a host timestamp does not establish `κ`, physical sound speed or synchronization. The common effective-speed uncertainty and source/receiver survey covariance remain shared nuisance terms.

## Exact equivalence and the role of receiver geometry

For a sufficiently informative receiver arrangement, equal distance observations determine the virtual source and additive range bias. The two models are then exactly equivalent only if

`R_a δ = 2(d−n·s_a)n` for every source placement,

with compatible relative driver/path delay. With constant orientation this implies

`n·(s_a−s_0)=0` for every placement.

Therefore:

- One source has an exact image/secondary alias for a suitable secondary offset.
- Any number of source positions on a line leaves candidate normals perpendicular to that line ambiguous.
- Any number on a plane leaves its normal ambiguous. A particular differently oriented reflector can nevertheless be distinguished.
- Four affinely independent sources leave no nonzero normal perpendicular to every displacement. This removes the universal fixed-orientation alias, conditional on observable virtual positions and timing.

Receiver count alone is not a proof. With known additive delay, four generic noncoplanar receiver ranges determine a virtual source by subtracting squared ranges. With unknown common range bias `b=vτ_b`, write `D_j=‖s−r_j‖+v μ_j`. Subtraction gives

`2(r_j−r_0)·q − 2(D_j−D_0)b = ‖r_j‖²−‖r_0‖² − (D_j²−D_0²)`.

Four receivers give three linear equations for `(q_x,q_y,q_z,b)`; the remaining range equation is quadratic and can retain two branches. Five generic receivers give four linear equations and can identify the four unknowns if that augmented matrix has full rank, followed by physical consistency checks. Shared delay across source placements may resolve branches with fewer receivers per placement. Three or four phones can acquire more receiver positions by moving them between stationary shots; this is an information requirement, not a requirement for five simultaneous phones.

The numerical control deliberately places six noncoplanar receivers on a distance-difference surface. Two distinct virtual positions and a compensating **−116.62 μs** driver-delay difference have equal observations to **5e-15 m** distance precision. The augmented system has rank three despite receiver-position rank three. All receivers remain on the same side of the candidate plane as the source. Thus generic bearing coverage and augmented conditioning matter even with six receivers.

## Quantified source-layout examples

The primary plane is `x=0.20 m`; its baseline image offset at `s_x=0` is 0.40 m. This is an illustrative analytic baseline, not a claim about the MacBook's speaker separation. Twelve shared receiver positions span three dimensions on the primary-source side. Every secondary model profiles one global 3D offset and one common delay bounded to ±150 μs. No selected arrivals are dropped. Effective speed is 343 m/s. Shared source-center standard deviation is 3 mm, independent placement 4 mm, reused receiver survey 6 mm and shared effective speed 0.6 m/s; independent timing is an **assumed** 20 μs standard deviation for this information calculation. These are declared budgets, not measured phone accuracy.

| Source layout | Source rank | Normal span | Best secondary-vs-plane RMS difference | Fixed plane-covariance squared residual |
| --- | ---: | ---: | ---: | ---: |
| One source | 0 | 0 | 0 μs | 0 |
| Two tangential sources | 1 | 0 | 0 μs | 0 |
| Four on a tangential line | 1 | 0 | 0 μs | 0 |
| Four on a tangential plane | 2 | 0 | 0 μs | 0 |
| Two with normal displacement | 1 | 100 mm | 235.91 μs | 316.17 |
| Four along the normal | 1 | 200 mm | 352.18 μs | 1431.33 |
| Coplanar, with normal displacement | 2 | 160 mm | 380.06 μs | 1668.85 |
| Four genuinely 3D | 3 | 180 mm | 304.91 μs | 1170.86 |
| Four 3D but short normal span | 3 | 11 mm | 18.42 μs | 4.30 |

The final row illustrates weak information despite rank three. The score is an engineering separation calculation with a fixed covariance, not a calibrated likelihood ratio or false-alarm probability. Letting that last case use a different driver delay at each source placement lowers RMS separation to **2.55 μs**, with fitted placement offsets from **−18.69 to +31.63 μs**. This extra timing freedom breaks the constant-driver assumption and materially reduces usable information.

## Unknown source orientation

A fixed orientation lets an unknown rigid body offset be represented by one constant world vector. If the MacBook rotates, using a constant world vector becomes physically wrong. Record `R_a` or explicitly maintain and declare constant orientation. Survey positions must identify the primary acoustic center, not an unspecified laptop-center point; otherwise orientation also changes the reference position.

Unknown orientations do not automatically make every plane explainable by a rigid emitter of fixed baseline length: the required image displacement must still have constant magnitude. However, there is a concrete exact counterexample even with source rank three. Put four source centers at `x=±0.20 m`, choose distinct y/z values giving rank three, and place each recording's receivers on the same side of plane `x=0` as its source. A 0.40 m secondary baseline pointing toward the plane alternates between +x and −x. The resulting emitter is exactly the plane image for every placement. The supplied numerical control has positive excess delays, valid same-halfspace plane geometry and constant baseline norm. Unrecorded 180° orientation changes therefore retain an exact alias despite a 3D source constellation. Accessibility of such two-sided acquisition is a separate practical question.

If the acoustic-center offset itself is permitted to vary arbitrarily by placement, the condition can always be satisfied by selecting `δ_a=2(d−n·s_a)n`. No source-motion pattern alone can distinguish those unconstrained models. This explains why fixed source configuration and acoustic-center/orientation calibration are load-bearing assumptions.

## Useful next measurement

At a placement where the two virtual sources coincide, let `u=(q−r)/‖q−r‖`. For a small source displacement `h` that preserves source orientation,

`d(μ_P−μ_E) = −2(u·n)(n·h)/v`.

Move the source across the candidate normal and use receivers with substantial `|u·n|`. Tangential source movement gives zero first-order separation and, for the exact alias, zero separation at any distance. Moving only receivers cannot separate identical virtual-source/driver-delay hypotheses.

For the concrete starting point `[0,0,1.2] m` and the published twelve receiver positions, compare four candidate source moves while keeping the already calibrated explanations fixed:

- `[0,0.25,1.2]` and `[0,0,1.45] m`: **zero** predicted separation.
- `[0.10,0,1.2]` or `[-0.10,0,1.2] m`: **478.08 μs RMS**, at least **327.98 μs** over the receiver set.

Both proposed normal moves remain on the same side of `x=0.20 m`. Physical accessibility, audible direct paths, unchanged source configuration and stable orientation must be verified before using these coordinates. The numerical candidate positions are an illustrative local-frame recommendation, not an instruction to place a device in an unverified real location.

For an actual ambiguous result, score accessible candidate placements using the fitted competing models and their joint uncertainty. Prefer the largest *remaining* predicted separation after profiling permitted common calibration/driver nuisance and retaining all current observations. Do not reset an independent delay offset for each new echo, and do not choose by source-rank increase alone. Known calibrated source rotation can also distinguish a body-fixed secondary emitter from a fixed room plane, but unknown rotation/changed directivity can instead invalidate the comparison.

## Minimum declarations and waveform-experiment implications

Record: primary acoustic-center positions in one frame with common/per-placement uncertainty; receiver acoustic-center positions and reused survey groups; constant source orientation or measured body-to-world orientations with uncertainty; stable hardware/output-route/configuration and probe IDs; channel routing and any common relative driver delay assumption/bounds; effective source speed/clock calibration and uncertainty; repeated-probe relative recorder-rate/warp diagnostics; direct-reference identity or competing-reference diagnostics; exact raw recordings and interruption/continuity evidence. Unknown values must remain unknown rather than silently becoming zero or independent.

The physics specialist's planned ±2-sample alignment nuisance shifts the **whole primary-plus-secondary waveform**, not the secondary component relative to the primary. That is the appropriate distinction: it does not algebraically erase relative arrival timing. In contrast, independent echo-only shifts of ±2 samples at 48 kHz permit ±41.67 μs or ±14.29 mm path adjustment and would erase the entire short-normal-span example. Strongly overlapping pulses may still make a whole-mixture shift practically correlated with secondary delay/amplitude; only the actual waveform experiment can quantify that. An empirical shared direct kernel may also absorb part of an overlapping component, so successful ideal delay identifiability is not evidence that the planned estimator detects it.

These derivations establish what the declared model could learn and which measurements add information. They do not establish source-model identification from real phone recordings, calibrated statistical confidence, or the success of any detector.

Reproduce from repository root with `.venv/bin/python evidence/source-model-identifiability/check.py` followed by `.venv/bin/python evidence/source-model-identifiability/nuisance_checks.py`. They overwrite only their local JSON reports; no held-out mapper input or hardware is used.
