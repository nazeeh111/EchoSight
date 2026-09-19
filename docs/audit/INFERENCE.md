# Spatial-inference adversarial audit

This backend is a research prototype. Small residuals and many supporting views do not establish that the first-order, single-source model is correct. This audit reproduces two failures with exact or near-exact fits, implements a bounded higher-order ambiguity guard, and records remaining limitations. No physical-device accuracy is claimed. Development cases were designed independently of the frozen evaluation answers.

## Implemented changes

1. `geometry.reflection_path` constructs an ordered specular path by image-source unfolding, requires interior segment intersections, and independently checks the reflection law at each bounce. Unknown finite extents and occlusion are explicit.
2. The inference post-check compares every recovered image source against two-bounce compositions of two other recovered planes. It uses the full shared image-source covariance, a conservative source-reference contribution, a compatibility gate, and at least seven geometrically valid supporting paths covering at least 80% of that image's supports. Mere algebraic image composition without a physical path is insufficient.
3. A compatible first-order reflector remains a hypothesis, alongside `fewer_surfaces_with_second_order_paths`. Invariant underlying surfaces remain accessible in the latter hypothesis. Consistent with the existing global-ambiguity contract, definitive `surfaces` is empty; the change does not convert fewer output surfaces into claimed successful reconstruction.
4. Guidance compares modest source displacements under the competing physical models. Exactly coincident first-order/double-bounce image sources cannot be distinguished by moving receivers while keeping the source fixed. A source move requires fresh source configuration/pose calibration and a new session. Predicted discrimination does not establish audibility or accessibility.
5. Every surface now states `model_status=conditional_first_order_hypothesis`; local uncertainty names reflection order, multiple emitters and unmodeled transducer response as excluded model errors. This is a limitation, not a guarantee that unsupported models are detected.
6. Optional `effective_speed_m_s` and `source_effective_speed_covariance` accept a joint calibrated source/effective-speed proposal. Effective speed is metres per nominal **source-buffer** second, not a relabelled physical sound speed. Both fields must be present together. Effective speed is representationally bounded to 250–460 inclusive; this is not a claim that all such values describe validated physical temperatures. The finite symmetric positive-semidefinite 4×4 covariance orders source x/y/z (metres), then effective speed (metres/source-buffer second). Its full covariance, including source-speed cross terms, replaces independent source/sound/clock nuisance covariance rather than adding a second copy. Receiver/direct/detector errors remain separate. Guidance, local dimensions and composition checks use the same source block and shared covariance.

## New development evidence

Detailed artifacts: `work/audit-inference/`; immutable baseline copies there correspond to commit `1c773367f787a551aec0f15fc244b5fe9290dee3`. `probe.py` generates inputs independently of the fitter. Truth remains outside session and observations; one-to-one matching occurs only in evaluation. `physical-double-paths.json` verifies actual two-bounce paths, not just image coordinates. `manifest.json` fingerprints the baseline, changed code, tests and results.

| Case, 12 noncoplanar receiver positions | Before, equal-input mapper / direct-plane competitor | After |
|---|---|---|
| Three first-order planes, including ceiling | Both recover 3/3, zero false planes | Unchanged |
| Two corner walls, ceiling, coherent double-bounce echo | Both recover the three real planes plus one nonexistent diagonal plane; the ghost has 12 supports, effectively zero residual and about 6.1 mm conditional offset standard deviation | Both return ambiguity; three real planes remain in the fewer-surfaces hypothesis and the four-plane alternative is preserved |
| Same corner with 15 µs timing noise | Both still report the ghost | Both preserve competing interpretations |
| A genuine diagonal reflector coincident with that image | Four-plane interpretation fits | Both interpretations remain; the algorithm does **not** claim the diagonal plane is absent |
| Only the double-bounce path is observed; parent planes absent from observations | Both infer one false first-order plane | Still unsupported: the guard requires evidence for parent planes and does not invent them |
| Reflections from two simultaneously excited source centers | Mapper produces three extra planes; competitor two, despite essentially zero residual | Still a source-model failure; local covariance does not cover it |
| One ideal isotropic point scatterer | Plane models do not provide definitive geometry | Separate identical-input point-model probe recovers its three coordinates, but this is not an integrated mixed-scene or finite-object capability |

The double-bounce example is not a numerical defect: for source `s=(sx,sy,sz)` and perpendicular corner walls x=0,y=0, the two-bounce image is `q=(-sx,-sy,sz)`. Exactly the same ranges are produced by a first-order plane through the corner with normal parallel to `(sx,sy,0)`. Its existence versus a second-order path is therefore not identifiable from delay-only observations at this one source position. The ordered path check rejects the reverse explanation that would remove a real corner wall using a physically invalid bounce order.

The isolated point comparison uses `|s-p|+|p-r|-|s-r|`, with four starts derived from surveyed positions, no target initialization. It fits the noiseless isolated fixture in seven evaluations. This only shows information under an ideal point-scatter assumption; finite objects, mixed unlabeled echoes and real bandwidth/directivity have not been established.

## Verification and limits

`python -m unittest discover -s tests -p test_inference.py` passes 19 tests. Added checks cover coherent double-bounce ambiguity, preservation of a coincident real-reflector alternative, physically invalid order rejection, missing-parent failure semantics, and the optional joint calibration convention. A numerical finite-difference derivative at fixed physical planes independently verifies the correlated source/effective-speed delay covariance. A separate scene uses effective speed 346 while physical `sound_speed_m_s` remains 343 to catch scale conflation. Invalid covariance and incomplete calibration pairs are rejected.

The original frozen suites are regression evidence only; their previous successes do not resolve the new model failures. Independent harder waveform and measured-data evaluation is owned by the evaluation specialist and must be reported separately. This audit does not count it as passed before those outputs arrive.

Remaining scientific assumptions and highest-priority gaps:

- Higher-order detection requires recovered parent planes and currently considers exactly two bounces. Unknown finite support, blocked segments and higher orders can change which paths exist.
- Unknown multiple emitters can generate coherent false planes indistinguishable from a different first-order scene. A source/effective-speed calibration only qualifies its chosen source model; it does not establish that the laptop is a point source.
- Association is still bounded, greedy, nonconvex and delay-based. Correlated/model-generated clutter is harder than independent random peaks. Local covariance is conditional on selected associations.
- Proposed source moves discriminate specified competing models; multi-source joint scene inference across sessions is not implemented here.
- Planar support hulls remain visibility summaries rather than physical edges, room enclosure, object identity or empty-space evidence.

No completion claim follows from this audit. The current runnable baseline has more honest competing-model output and a correct joint calibration boundary; the remaining mismatch cases materially constrain demonstrations and require further evidence or stronger modeling.

## Measured-data diagnostic, post-fit only

Read-only FLAIR inspection is saved in `work/audit-inference/flair-diagnosis.json` with `flair_diagnosis.py`. The independent laser annotations enter this diagnostic only after fitting, never as a solver prior. Two sidewall annotations have 20–21 of 24 nearest extracted candidates within 25 mm of their forward predictions (median 12–13 mm). Floor and ceiling have only two each within that band (median 64 and 85 mm). A fitted floor has 23 supporting captures and 19 mm residual RMS but approximately 58 mm offset disagreement with the laser plane versus a 5.6 mm conditional reported standard deviation. Several unmatched fitted planes have 17–24 supporting captures spanning all four array placements. Thus simply increasing support count, checking numerical rank, or exposing unaffected parent planes cannot establish correct measured reconstruction. Source response/calibration, reflection filtering, higher orders and model/association error remain active competing causes; the diagnostic does not select or tune to a laser answer.

A follow-up covariance validation regression checks the matrix actually returned after symmetrization. Entrywise near-symmetry alone can hide an indefinite symmetric matrix if the PSD test reads only the original lower triangle. The validator now checks eigenvalues after symmetrization. Read-only model-subset analysis in `work/audit-inference/invariant-model-analysis.json` also records a dependency-cycle counterexample: simultaneously deleting every higher-order target can leave a model lacking its required parent reflectors. Partial invariant geometry therefore needs consistent-subset enumeration before extending the current conservative global-ambiguity output; this is not yet claimed as implemented.

Portable summaries and exact code fingerprints are retained under `evidence/audit-inference/`; detailed development scripts remain in local `work/audit-inference/`. The new physical-path unit tests and independent raw-waveform stress runner reproduce the central higher-order ambiguity rather than relying on narrative agreement.
