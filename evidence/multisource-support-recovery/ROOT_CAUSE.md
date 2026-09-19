# Higher-order seed 1129: bounded support-loss diagnosis

2026-09-19. Production source unchanged. Investigation only; no promotion and no claim of recovered output.

The live mapper reproduces `no_result` with `joint_refit_lost_required_support` on the original saved observation set from `../work/clean-checkout/work/relocation-heldout-de8442b/higher_order_four_sources-1129/mapper-result.json`. The input remained byte-equivalent under canonical JSON serialization. Exact file and implementation hashes are recorded in `refit-trace.json`. `trace_refit.py` observes local state without altering fitting, candidates or gates. Existing raw data were neither generated nor reprocessed. Trace overhead makes its runtime unsuitable for performance claims.

## Specific cause

The greedy joint search selects ten provisional planes, all satisfying existing support requirements. The final two ordinary least-squares refit/reassignment passes cause provisional plane 6 to lose one selected observation at source index 3. Its support changes from [10,11,10,4] to [10,11,10,3]. The support rule requires four observations from every source. `echosight/multisource.py:370` rejects the entire ten-plane model as a result.

The other nine candidates still satisfy that unchanged support rule. For the first six candidates, source-specific counts remain between 9 and 12. Only after the trace artifact was saved, evaluation truth was read: these first six match every room wall, including floor and ceiling, at normal errors 0.127–0.272 degrees and offset errors 1.56–16.10 mm. The failed candidate and the remaining three candidates match no wall. Therefore selecting the nine supported candidates alone is not a valid room reconstruction: the remaining three false candidates must still face the existing parent-subset and hidden-parent/point-path alternatives.

This establishes collateral loss at the global abort. It does not establish that all six walls survive the full existing ambiguity checks when the unstable candidate is removed.

## Proposed isolated discriminating experiment

Subject to coordinator scope agreement, in a source copy under this directory only: after joint refit, remove only candidates that fail the existing per-plane support rule; recompute exclusive assignment and ordinary least-squares refit; repeat until supported or empty, with at most MAX_PLANES candidate removals. Then execute every unchanged covariance, source-diversity, parent-subset and path-alternative stage. No changes to peak extraction, candidate budget, matching gates, source ranks, scores, acceptance thresholds, raw data or truth separation. The existing first-order conditional model remains explicit.

A positive result requires six matched surfaces including floor and ceiling and zero false definitive surfaces in the original seed 1129. The unchanged source-relocation acceptance applies, including the existing 60-second recording-to-result limit (an inference-only replay cannot certify that limit by itself). Preserve the failing two-source recovery and all other old outcomes. Existing hidden-parent controls are mandatory before promotion because dropping provisional candidates can remove an alternative physical parent and incorrectly resolve an ambiguity. Failure here closes this particular repair approach; do not weaken support or relabel misses as success.

Estimated bounded next effort: one small experimental patch and targeted observation replay; if successful, integrate with meaningful support-loss and competing-parent checks and rerun affected frozen relocation controls. No new raw generation is needed for the initial test. Broader synthetic or measured capability is not inferred from a repaired exposed regression.

## Relationship to new two-reference evidence

The two-reference calibration result justifies investigating supplied-source accuracy separately, but it does not provide a room-mapping recording paired with that calibration and therefore cannot demonstrate downstream reconstruction benefit on its own. This support-loss diagnosis supplies separate, new runtime evidence for a tractable mapping defect. It does not reopen the failed joint waveform, held-view guard, density/null or candidate-budget branches.
