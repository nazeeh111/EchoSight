# Independent retained mismatch regression

Original multisource SHA256 `55e060183836b11b9976fe0f2187c3b97101687ff34d35d65c6319489e66f6aa`; V2 SHA256 `b61f4742927c8270a5133526bddbff5080b806242f6ff2e08310bc9499622085`.

All 15 prespecified original/V2 comparisons completed. Every definitive surface output is exactly equal between methods, including evidence, geometry and uncertainty. No added false/unmatched plane, missed plane or numerical geometry regression appeared. Input hashes and all loaded runtime source hashes remained unchanged. See `freeze.json`, `completed.json`, `results.json` and the 30 saved geometry outputs. This is direct local execution from retained processed recordings; no new data generation, parameter changes, raw extraction or physical validation occurred.

The complete latest source-diagnostic V4 fresh set was used: six families at both 2441 and 2459, without selecting favorable cases. Single-room and receiver-filter cases each retain six matched surfaces; near-reflector cases retain seven; direct-null cases retain zero. Dual-phase cases preserve six true plus four/three false planes. Dual-room cases preserve six true plus two/three false planes. These remain scientific failures.

The measured 40-response nominal arm preserves one matched and two unmatched planes. Its wrong-receiver-permutation control preserves four unmatched definitive planes. Silence preserves no geometry. Unmatched measured planes are not proven nonexistent by incomplete room annotations. Existing spatial acceptance remains failed. The nominal, shuffled and silence observations were loaded directly from their separate saved outputs, preserving their respective supplied poses without recomputing permutations or editing metadata.

No claim about complete raw processing runtime is made. Direct-null and silence inference-only replays return `calibration_needed` with zero geometry, identically in both versions; this does not replace their raw admission-route status checks. Frozen historical criteria/results are unchanged; geometry scoring uses the existing 5-degree/0.15-m one-to-one rule.

## Cancellation check

The new fixture regression initially lacked cancellation coverage; existing multisource tests cancel at entry. A targeted runtime probe uses the same retained 1129 observations and requests cancellation immediately after the first ordinary least-squares refit returns. It wraps the actual optimizer, without replacing numeric results. Original code runs 19 further refits and returns `no_result`; V2 performs zero further refits and returns `cancelled` with empty surfaces and hypotheses. `check_cancel.py` and `cancellation-results.json` preserve the executable evidence. This checks responsiveness at the newly added per-fit boundary, not interruptibility inside an active SciPy optimization.

Recommendation before integration: include this compact fixture-based cancellation test beside the recovery regression. No further raw generation or whole-suite repetition is needed for this finding. The initial probe assertion expected a cancelled status from both versions; the inherited original early-return behavior falsified that expectation. The retained final probe records both outcomes and asserts the required behavior on V2.

The fixed-source runtime was unchanged and was not redundantly tested. The 12-case frozen source-relocation regression is recorded separately in the parent evaluation folder; this 15-case comparison adds coherent-source, nearby-reflector, filter, null and measured-data coverage for the changed multisource module.

## Compact package and rerun

This compact pack preserves the full 15-case metrics and frozen input identities, plus exact original/V2 modules. The 30 redundant detailed geometry outputs remain in the originating task's `work/evaluation-finish/mismatch/` directory; they are not duplicated here. Raw recordings/processed input arrays are not bundled.

`run.py` is the exact original execution record. For a fresh local rerun, use `replay.py --repo /path/to/backend --output /path/to/new-empty-directory` with the backend Python environment. The output directory must not exist. The repository must retain `work/source-model-diagnostic/run-v4/fresh/` and `work/measured-multisource/` with the files identified in freeze.json. This rerunner imports the preserved original/V2 modules, so the live repository's multisource.py may already contain the integrated change. Remaining dependency versions/source hashes are captured in the new freeze; compare these with the original before attributing differences. This is not a self-contained clean-GitHub raw reproduction.
