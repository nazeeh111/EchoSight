# Independent receiver covariance review

Reviewed **37d355f786e1fa337a0f50f1fda4d6eb3c5eb0f9**, compared with parent checkpoint **ed6d004**, from an isolated `git archive` snapshot at `work/review-37d355f-snapshot`. No implementation, tests, documentation or Git state were modified. The eight scoped source/document/test files were byte-verified against the commit; hashes are retained in `work/review-37d355f-source-hashes.json`.

## Result

**No P1/P2 found in this bounded math/integration review.** The full receiver matrix replaces the scalar receiver budget, retains cross-capsule and reused-source-view terms, reaches the plane and compact-path uncertainty calculations, and is validated before raw recording I/O. The numerical and boundary checks below were independently executed. The coordinator's 177-test result and builder evidence were not used as proof.

## Actual code inspected

Read all of `echosight/receiver_covariance.py`; the diff and surrounding calibration/preparation, `_covariance`, `_parent_subset_alternatives`, `infer_scene_bundle`, and `process_scene_bundle` code in `multisource.py`; receiver derivatives, `_evidence`, `_point_nuisance_covariance`, `_fixed_weight_covariance`, `_point_modes`, and integration in `path_alternatives.py`; relevant unchanged preparation and geometry helpers in `inference.py`/`geometry.py`; `docs/RECEIVER_COVARIANCE.md`; the new receiver tests and analytic multisource fixture. This does not repeat a full review of the existing global association/path search or other experimental work.

## Independent mathematical checks

Script/output: `work/review-37d355f-probes.py` / `.json`.

- Constructed a translated and tilted four-source, four-capsule scene with two planes and a dense anisotropic 12×12 receiver matrix containing positive and negative cross-capsule correlations. Independently finite-differenced each capsule's physical delay, constructed the complete receiver Jacobian by group, and added independent peak noise plus reused direct-reference noise. The resulting ordinary-least-squares sandwich `pinv(J) C pinv(J).T` matches `_covariance` with **3.55×10^-11 relative error**, rank six. The cross-plane block is nonzero (norm **3.49×10^-4 m²**), so this check would not pass a diagonal-only propagation. Reordering all declared group IDs and covariance blocks together leaves the result unchanged.
- Independently differentiated the compact scatter path with respect to receiver position. Maximum derivative disagreement was **1.78×10^-13 seconds/metre**. The full actual-point nuisance matrix matches independently assembled `D C_R D.T` plus timing terms.
- Independently formed the influence of the executed fixed-weight point estimator, `(J.T W J)^-1 J.T W`, and verified its sandwich covariance. Then generated **350 nonlinear actual receiver perturbations** and timing draws, refitted the compact location with the same fixed weights, and compared empirical covariance. Relative matrix disagreement was **5.94%**. This checks the implemented estimator, rather than substituting inverse curvature or an unexecuted generalized-least-squares optimum.
- A common 20 mm translation produces exactly zero variance for a difference of two identically projected capsules. Together with the focused common-mode averaging test, this checks both cancellation and non-averaging of shared error. Correlation is not assumed merely to inflate marginal uncertainty.

The ordinary plane fit is unweighted least squares at the final selected links, so its implemented `pinv(J) C pinv(J).T` propagation is appropriate locally; retained residual inflation never shrinks it. Fixed plane-versus-point comparisons retain one covariance objective, while exported point modes use the actual compact-path nuisance derivative. Source/source and source/speed terms remain unchanged by the patch and are added once alongside the receiver projection.

## Parent gates and validation checks

Script/output: `work/review-37d355f-boundary-probes.py` / `.json`.

- Independently finite-differenced receiver derivatives for **nine** first/second-order paths from three candidate planes. Maximum derivative disagreement was **2.05×10^-13 seconds/metre**. Every propagated marginal matches the corresponding receiver block calculation; intentionally huge legacy scalar standard deviations add nothing under full-matrix replacement.
- Parent compatibility uses `3 * (sqrt(direct/timing/calibration/receiver variance) + sqrt(parent variance))`. Given only the two marginal variances, adding standard deviations bounds unknown correlation by Cauchy–Schwarz. The full receiver matrix also reaches fitted parent-plane covariance. The parent score remains its previously declared fixed timing-normalized engineering score, not a joint likelihood or calibrated probability; the documentation correctly says so.
- Three malformed/full declaration cases (wrong scalar policy, oversized group list, non-PSD matrix) fail through the public raw entry before any recording-read function is called. A rejected observation with undeclared receiver identity still fails calibration coverage. A callback that becomes true during covariance validation returns cancelled rather than falling back to scalar processing.
- Source inspection confirms group count ≤64, square numeric allocation bounded at 192×192, rejection of ragged/string/boolean/nonfinite entries, PSD/symmetry checks, exact group coverage, and reused nominal-pose agreement across captures and observations. Raw sessions additionally retain existing per-session and total-record limits. The PSD tolerance is the documented -10^-12 m² numerical tolerance; it is not an empirical accuracy threshold.

## Focused regression execution

`python -m unittest tests.test_receiver_covariance -v`: **8 passed**, 7.634 seconds. Log: `work/review-37d355f-tests.txt`.

These executed tests cover legacy versus identical diagonal full-matrix equivalence, explicit scalar replacement with differing legacy values, independent shared source terms, mode-specific fixed-weight point propagation, raw WAV transport and prepared replay, malformed declarations, original input/byte preservation, cancellation, and rejected-capture pose inconsistency. They also include 40,000 receiver perturbation draws and 600 actual nonlinear plane refits; these were locally run, not accepted from the evidence report. The raw transport fixture intentionally stubs candidate extraction to isolate covariance transport, as the documentation discloses.

The independent probe initially completed its assertions but failed while writing its summary because a NumPy integer was not JSON serializable. Only the reviewer scratch serializer was corrected to emit a Python integer; the probe was rerun successfully. No implementation change resulted.

## Limits and remaining scientific assumptions

This is local first-order covariance conditional on supplied calibration, selected candidates and an executed estimator. It does not correct biased survey means, wrong echo selection, unmodeled transducer effects or an incorrect path model. The matrix explicitly excludes source/receiver and speed/receiver cross covariance; an acquisition with material common source/receiver survey error is not representable by this contract. The documentation states this limitation and does not claim physical confidence calibration.

No full-suite rerun, new frozen scientific acceptance, hardware recording, signing, installation or native build was performed. No claim of complete global association, reflection-order identification or physical receiver-array qualification follows from these checks. Cancellation is cooperative around bounded numerical work, including the capped eigendecomposition; it is not instantaneous preemption.
