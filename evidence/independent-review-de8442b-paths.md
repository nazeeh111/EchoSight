# Independent review: competing path interpretations

Reviewed commit: **de8442b2dd088c036d2b92eaeaf29a1273785795**. Review used an isolated `git archive` snapshot at `work/review-de8442b-paths-snapshot`; no main files were edited. Scope: `echosight/path_alternatives.py`, its assembled experimental multisource call/error path, relevant physical-ray and covariance helpers, portable tests, current charter and `docs/audit/PATH_ALTERNATIVES.md`. The reviewer did not implement the reviewed path-alternative module. New held-out recordings, answers and results were neither read nor fitted.

## Findings

**No actionable correctness defect was established in the reviewed patch.** This is a bounded code/numerical review, not proof of global search completeness, physical accuracy or unseen raw-data acceptance. The restrictions below remain consequential scientific limits; the reviewed output mostly states them explicitly.

## Evidence and mathematical checks

1. **Same selected evidence.** The post-fit check resolves the original `(session_id, capture_id, candidate_id)` links, rejects repeated recordings/missing candidates, and requires all selected records. It does not reassign arrivals or improve a score by dropping hard records. The refitted plane, compact model and candidate parent model use the same frozen full delay covariance. The plane comparison is conservative: alternatives must beat the smaller original/refitted plane score, plus absolute and marginal-residual gates. Scores are labeled engineering compatibility, not a posterior or penalized model-selection probability. Existing source-diversity and recovered-parent decisions are composed before the new check.

2. **Compact model and physical nuisance covariance.** Independently differentiated the complete broken-path observable over four sources, one shared speed and twelve reused receiver positions, with a newly generated correlated positive-semidefinite calibration. New analytic seed 49117 yielded relative covariance error **6.17e-10** against the implementation. Independently computed the influence of the executed fixed-weight estimator and its sandwich covariance; relative error was **5.31e-11**. The selected compact point was recovered to numerical precision. This verifies that the plane covariance is a comparison weight, while reported point uncertainty uses point-specific source/speed/receiver/timing propagation.

3. **Small-error uncertainty experiment.** A separate new analytic seed 50119 supplied common and independent source-position errors, shared speed error, reused receiver survey error and independent timing noise. Four hundred nonlinear fixed-weight refits had covariance within **5.52% relative matrix difference** of the predicted sandwich. This is a conditional, small-error simulation check, not physical or selection-aware coverage.

4. **Two-reflection degrees of freedom and gauge.** Independently generated 48 two-bounce observations at four noncoplanar source positions and twelve receivers. The fitted rotation-axis operator had five parameters and numerical rank five. Translating its axis-center coordinate 51 m along the axis changed image positions by only **3.22e-15 m**, verifying elimination of that unobservable coordinate. The physical decomposition produced full ordered ray vertices. Independent incidence, unit-direction reflection-law and geometric-length checks were below **3e-15**; a deliberately incompatible receiver configuration did not pass the compatibility gate. These ray checks did not simply call the implementation's validator again.

5. **Global/local ambiguity distinction.** A newly generated coplanar point fixture recovered both globally mirrored locations, despite full local rank at either mode. Existing tests additionally cover rank-deficient covariance and search-boundary modes with null covariance. A local full-rank Jacobian alone is therefore not used as proof of global uniqueness. Reported uniqueness remains conditional on the bounded returned modes.

6. **Bounds, cancellation and publication.** Record/surface caps precede fitting. Optimizer residuals and physical-parent loops check cancellation; the post-fit result mutation is deferred until all searches finish. The assembled cancellation branch clears definitive surfaces. Post-fit value/key/type/linear-algebra errors clear definitive surfaces and mark retained hypotheses unverified. The focused tests exercise these cases, including malformed selected evidence and acquisition admission. The numerical prepared entry remains an explicitly trusted-input interface rather than authentication of independent recordings.

## Executed checks

From the isolated snapshot, using the repository Python environment:

```sh
PYTHONPATH=. /absolute/path/to/backend/.venv/bin/python -m unittest tests.test_path_alternatives tests.test_multisource -q
```

**28 tests passed in 22.983 seconds.** Exact log: `work/review-de8442b-paths-tests.txt`.

Independent scripts and outputs:

- `work/review-de8442b-paths-probes.py`, `.json`, `.log`: covariance, actual ray law/order, gauge and incompatible-path checks.
- `work/review-de8442b-paths-extra.py`, `.json`, `.log`: new global mirror fixture and 400-draw nonlinear shared-nuisance experiment.

Each script imports the immutable snapshot explicitly. The first output records exact module hashes:

- `path_alternatives.py`: `e54f653edab911da213583282e002d38a0545f6f5f98d2bd8e0fd33b74081e9e`
- `multisource.py`: `104478b5519d5e15ab80b723d9e0ddf904276c339f453646d67ece0a0d845f43`
- `geometry.py`: `e9d278cab1ca44d0e785e69c067441764b9dd6688cd5e27483bc254bd9c237ce`

## Remaining limits

- The parent search is explicitly a bounded rotation-axis family for intersecting planes. Parallel parents compose to a translation, which is not represented by the zero-angle early-return branch. This is a search/capability limitation, not evidence that a surviving plane has no two-reflection explanation. The existing first-order conditional labels and `global_optimality_proven=false` must remain. A useful documentation refinement would name the parallel-parent exclusion directly.
- Point search has 32 starts, a 30 m box and a 1 cm minimum-merging tolerance; parent search has three optimizer starts and 180 decomposition angles. Neither establishes exhaustive global modes or absence of a competing explanation. Near-indistinguishable modes and unsearched regions remain unresolved possibilities.
- Compatibility uses the plane's fixed covariance and engineering gates. It is not a likelihood ratio with nuisance marginalization, a degrees-of-freedom penalty, or calibrated false-alarm control. A five-coordinate parent fit has more flexibility than a three-parameter plane. The safe output consequence is withholding a challenged interpretation, not declaring hypothetical parents real.
- Point covariance is local and conditional on selected paths, supplied uncertainty and the compact geometric model. Material-dependent phase, finite object size, multiple emitters, waveform-selection effects and wrong calibration are outside that covariance. The declared mismatch/raw evaluation must determine performance on those cases; this review did not inspect its unseen results.
- Physical parent vertices establish geometric possibility only. Finite extent, occlusion, material reflectivity and actual wall/object existence remain unestablished. No physical-device experiment was performed.
