# Independent bounded pruning review

Verdict: no actionable material defect found in the bounded prune/refit change reviewed below. This is a code-change review and focused synthetic verification, not physical accuracy validation or a repetition of the assembled backend review.

## Reviewed artifact and requirements

- Base implementation: `e372158`, `echosight/multisource.py`.
- Candidate: `work/spatial-finish/experimental_multisource_v2.py`, SHA-256 `b61f4742927c8270a5133526bddbff5080b806242f6ff2e08310bc9499622085`.
- Patch: `work/spatial-finish/production-candidate.patch`, SHA-256 `09adaa8586d6630447212bcade64bb3dc9937630a3fff525c33c07a9ce9c135b`.
- Read charter and addendum, original acceptance criteria, live assignment/support/covariance/ambiguity pipeline, candidate patch, recorded raw comparison and builder regression evidence.
- Original acceptance SHA-256 observed: `626166532905ca48a53639f6521df93aecc6f2bcf8dd77618bd20b8272fd35f7`. No criteria or production files modified.
- Repository HEAD advanced to `c3de891` during review through coordinator activity; this report identifies the isolated candidate precisely. Later integrated exact-commit verification remains separate.

## Direct observations

The change preserves `_supported` thresholds, exclusive Hungarian assignment, and two least-squares refinement passes per retained set. Failed candidates are removed monotonically. Each changed retained set receives fresh assignment/refit passes, and links are rebuilt before checking support and computing covariance. The retained indices are contiguous; covariance and parent-model interpretation both consume the same final retained set and links. Empty assignment sets no longer invoke least-squares fitting.

A nonterminal iteration removes at least one candidate. With the existing ten-plane cap, the loop can execute at most ten bodies; the worst single-removal sequence fits 110 planes across the two passes. Cancellation is checked on loop entry and before each individual refit. Individual least-squares calls retain the existing bounded 35-evaluation setting. The change does not guarantee global model optimality or calibrate selection uncertainty, and existing outputs continue to state those limits.

## Independent executed checks

Commands, from repository root:

```sh
.venv/bin/python work/review-spatial-pruning/probe.py
.venv/bin/python work/review-spatial-pruning/run_suite.py
```

`probe-results.json` records the retained recording-derived fixture run with instrumented production functions:

- Nine fitted candidates after one unsupported candidate is pruned, with 343 exclusive links; every retained candidate passes unchanged support requirements.
- Assignment recomputation reproduces the exact covariance links. Covariance is finite, symmetric, positive semidefinite, 27 by 27, and full rank 27. Minimum eigenvalue is approximately `6.16e-6`.
- Downstream parent-model analysis receives exactly those parameters, links and covariance. It retains six definitive conditional surfaces and the alternative interpretation diagnostics. Selected score `-1494.686` remains better than null score zero.
- Input fixture bytes are unchanged. Runtime approximately 5.05 seconds on this execution.
- Cancellation triggered only after actual pruning returns `cancelled`, clears geometry/hypotheses and covariance.
- Executing the exact changed loop AST with controlled assignment outcomes verifies a ten-to-one cascade (nine pruned, 30 assignments, 110 refits), all-ten removal, and entirely empty assignments (zero refits). These are control-flow probes, not acoustic performance evidence.

`run_suite.py` loads the isolated candidate as the real `echosight.multisource` module before importing tests. All 13 selected tests pass: the complete existing multisource suite plus the late joint cancellation regression. These cover analytic 3D room surfaces, exclusive evidence, hidden-parent ambiguity, tangential source motion, shared calibration covariance response, equivalent physical-arrival capacity, genuine extra reflectors, input rejection, and geometry clearing on late cancellation.

The probe harness needed corrections for its initial fixed candidate-count cancellation trigger, AST lookup, and NumPy JSON conversion; final saved scripts/results pass. The initial suite selector named a nonexistent class and was corrected to the existing exact cancellation method. None of these was a product defect.

## Limits and integration disposition

The builder's raw-recording comparison and original/candidate regression results were inspected; this review locally replicated inference from the retained extracted observations, not signal extraction from those raw WAVs. Wider raw mismatch regressions remain the coordinator's separate work. No measured-data or own-device accuracy was established. Covariance checks establish correct dimensions, support, finite propagation and existing sensitivity behavior, not frequentist coverage after selection. The pre-existing bounded two-pass assignment/refit heuristic and model-ambiguity search remain conditional methods.

The candidate is suitable for integration subject to the coordinator's remaining raw regressions and exact integrated-commit verification.
