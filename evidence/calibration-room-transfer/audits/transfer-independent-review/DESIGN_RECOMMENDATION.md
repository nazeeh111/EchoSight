# Smallest correction to the held-path evaluation design

**Recommendation:** add a small evaluation-only geometry preflight to the prospective study's existing `check`/freeze step. Reuse the saved-artifact oracle logic. Do not change `recommend_next_view`, the mapper, extractor, public API or the completed frozen result. This corrects the demonstrated study-design defect; it does not qualify calibration transfer.

## Why the existing recommender does not solve this

`echosight/inference.py:572–612` ranks supplied positions by separation between corresponding *competing geometric hypotheses*. It does not examine every pair of simultaneous room echoes or enforce the held scorer's exact-one rule. It uses fixed 10 mm receiver and 50 µs timing assumptions and explicitly disclaims audibility/accessibility/resolution. Extending it into a physical placement or held-test certification feature would add unrelated product scope.

## Required distinctions

Let `W = 200 µs`, `p_i` denote a predicted excess delay, and `c_i` its observed candidate.

- With perfect predictions and exactly one perfect candidate per physical path, **every pair of simultaneous echo delays must have separation strictly greater than W**. This is necessary and sufficient for the exact-one gate in that ideal complete, clutter-free catalog. Equality fails because eligibility includes the endpoints.
- **Separation strictly greater than 2W = 400 µs** makes the full prediction windows disjoint. This is a stronger sufficient condition against candidate reuse, provided every intended candidate exists inside its own window and no extra candidate enters it. It is not necessary for the perfect-catalog gate. A 300 µs pair passes the ideal gate despite overlapping windows.
- The current extractor separately requires candidate peak indices to differ by **at least 17 samples at 48 kHz, 354.166667 µs**. The unrounded configured duration is 350 µs. This is a necessary retained-catalog spacing rule, not a guarantee that every physical echo with greater separation is detected. Waveform interference, prominence, relative amplitude and repeat consistency remain separate conditions.

The completed study's true pairs at 173.021453 and 196.986783 µs violate the first rule. Its 226.570051 µs pair passes that ideal gate but lies below the extractor spacing. These are distinct limitations; one scalar “resolution” label would obscure them.

## Margins and certification

Declare uncertainty assumptions before choosing or accepting future held positions. Do not choose a margin to make the chosen positions pass.

For a conservative interval model `|c_i − p_i| ≤ e_i`:

1. Own-candidate inclusion requires `e_i ≤ W`.
2. Cross-candidate exclusion is guaranteed when each nominal pair separation is `> W + max(e_i, e_j)`.
3. Retained-peak spacing additionally requires the pair's lower possible peak separation to satisfy the 17-sample rule. A conservative continuous bound is `|p_i−p_j| − e_i − e_j`, with any excluded peak-localization/sample-grid uncertainty added explicitly. Evaluate the final spacing in sample-index units; do not silently equate exact geometric delay with a sampled correlation maximum.

Shared source/speed, receiver and plane uncertainty must preserve correlations. For a modeled delay difference, use `(g_i−g_j) Σ (g_i−g_j)ᵀ` with the full joint covariance and the applicable additional error terms. Separate geometry/prediction error from extraction localization/systematic bias. The current covariance does not bound missing candidates, sidelobes or wrong associations. A declared `kσ` margin is conditional model evidence, not a hard bound or calibrated physical guarantee. If required terms are missing, report the margin check as unknown rather than certify it.

The preflight can certify **ideal catalog feasibility**, and separately **spacing feasibility under declared conditional margins**. It cannot certify audibility, correct extraction, accessibility, room closure or physical accuracy. Even disjoint windows can contain clutter. Keep the actual raw-to-candidate and held-residual gates mandatory.

## Minimal reusable preflight

Given fixed study geometry/source, held positions, source-buffer rate, frozen window and extractor spacing:

1. Compute all intended excess delays and pairwise separations at each held stop, including distance from the direct path and the supported delay range.
2. Run the existing ideal exact-one/exclusivity gate on a complete oracle catalog. Return every failed path and its competing path IDs, with a complete denominator.
3. Separately report minimum sampled-spacing slack and any declared uncertainty-margin slack. Do not change the actual gate or automatically relocate a failed stop.
4. Save this bounded report and hash it into a **new** freeze before authorizing audio generation. Ideal infeasibility blocks that prospective study. The completed freeze remains immutable.

A few table-driven checks suffice: separations at/below/above W, between W and 2W, 17-sample boundary, absent uncertainty, and the present held geometry returning 20/24 under exact truth. No new recordings or mapper runs are needed to implement and verify this preflight.

## Exact scope of a future experiment, only if separately authorized

Retain the current two source-calibration instances, mapping recordings, fitted maps, comparator definitions, original failures and null controls. Prospectively declare four new common held positions, deterministic independent survey/audio streams, unchanged emitter/probe/room assumptions, all residual/runtime/gain criteria and the complete 24-path denominator. Freeze the new positions and streams only after the geometry preflight and independent review; do not replace seeds or select favorable audio.

The narrow follow-up then requires only **eight newly authorized held recordings**, two instances × four stops, extracted once through the existing observation-only path. Evaluate all five already saved maps against the same new held evidence; do not rerun mapping or recalibration. Store this as a separate development experiment with both old and new outcomes visible. The original 19/24 and failed promotion do not change. Any new failure remains a failure; no extractor revival, gate relaxation or public-feature promotion follows automatically.

No execution of that future experiment is recommended or authorized by this design note. Preflight implementation plus this bounded prospective plan is sufficient corrective scope now.

## Coordinator's narrower implementation boundary, reviewed

The proposed first change accepts a declared per-capture ideal delay catalog, applies the identical `<= W` exact-one/exclusivity policy, and reports conflicts, minimum separation and whether the windows are disjoint. This is sufficient for the demonstrated root cause and preferable to expanding the first helper into uncertainty or audibility modeling. Detector spacing and declared uncertainty margins can remain explicit requirements in the prospective protocol.

Require an explicit expected per-capture identity set/count to assess declared completeness. Missing/extra/duplicate identities, nonfinite/bool/negative delays and malformed catalogs must not yield a feasible result. Equal delay values for distinct valid path identities are legitimate conflicting input and must yield infeasible, not be silently deduplicated. A compact exact-arrival example from this completed study must be labelled post-hoc. The helper certifies feasibility of the declared catalog only; it cannot authenticate that the supplied catalog includes every physical echo. No production view recommender change is needed.
