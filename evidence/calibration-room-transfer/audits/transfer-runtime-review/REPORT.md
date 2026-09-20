# Frozen runtime applicability and portable evidence

Static comparison: frozen runtime `5d6423486be5fd448a4d7b42fbbaee264eb07c9c` versus delivered 0.2 commit `ea74a9e726f105e3606478c5d8aeb48d4c0cf0ef`. No solver, renderer, calibration, raw-processing or test suite was run for this review. The only numerical execution was the explicitly requested saved-output gate replay.

## Applicability

Eleven of the original 17 runtime modules are byte-identical: `__main__`, acquisition, calibration, controlled, evolution, geometry, multisource, path_alternatives, receiver_covariance, signals and simulation. Six changed, and delivered 0.2 adds interpretation.py and material_features.py. The required evaluation/metrics.py, evaluation/path_interpretations.py and both requirements files are unchanged. Full comparison is saved in runtime-diff.patch.

| Changed module | Relevance to this context-free geometric experiment |
| --- | --- |
| inference.py | Only cancelled-result cleanup additionally removes interpretation. No geometric inference arithmetic changed. |
| pipeline.py | Fitting whitelist and no-context progress span stay unchanged. Acquisition is deep-copied; optional interpretation context is attached only after geometry fitting. The new post-fit interpretation call returns not_configured without context. Added module import, copying and interpretation bookkeeping can change timing. |
| __init__.py | Version changes from 0.1.0 to 0.2.0. |
| storage.py | Adds optional interpretation validation/revision/profile operations and archive context binding. Frozen sessions omit interpretation context; their load path retains the same numerical inputs. |
| cli.py, api.py | New context/profile/inspection surfaces. Neither interface drives the frozen worker. |

The original worker directly loads sessions and calls process_session/infer_first_echo. It uses no interpretation context. Numerical extraction, clock fitting, candidate generation, geometry, covariance and the baseline/first-echo routines relevant here are unchanged by this diff. This supports **structural applicability of the geometric finding**, not a claim that the study ran on 0.2. The exact freeze rejects 0.2 because six file hashes and the runtime file set differ. Result IDs/provenance/output shape differ because the implementation fingerprint hashes all runtime modules, the version changed, and interpretation is added. The fixed 10-second timing gate cannot be transferred to 0.2 without measurement. Cancellation after withheld extraction still precedes geometric fitting; the added cancelled-field cleanup does not change its extracted observations.

## Exact raw replay closure

input-inventory.json verifies all **94 original frozen input hashes** in the isolated 5d64234 checkout. None is a symlink. Total is 13,339,822 bytes. Git at that commit provides 22 files (624,681 bytes). The supplemental closure is:

| Supplemental input | Files | Bytes |
| --- | ---: | ---: |
| Original x/y reference WAVs, seeds 2821 and 2833 | 48 | 12,582,144 |
| Their session/reference/calibration/manifest/truth files | 20 | 87,255 |
| Frozen transfer run.py/settings.json/PROTOCOL.md and original run_v2.py | 4 | 45,742 |
| Original freeze.json and static-check.json receipts | 2 | 13,444 |
| **Exact overlay total** | **74** | **12,728,585** |

The exact paths are supplement-paths.txt. The 48 reference WAVs are required even though this experiment consumes saved calibration values: verify() hashes them and check() verifies their manifest identities. Saved joint fits, protocol and original freeze are among the 22 Git-provided files. A derived observation package cannot replace those inputs while satisfying the original freeze.

The runner computes ROOT from its path; it must reside at `<checkout>/work/calibration-room-transfer/run.py`. A standalone folder or plain source archive lacking Git objects is insufficient for check(), which executes git show against the frozen commit. No need to commit or redistribute the 56 newly generated experiment WAVs: the exact renderer can regenerate them in a new complete checkout. Never execute original run_v2.py as setup; it is retained frozen provenance, not permission to regenerate the older experiment.

Suggested exact replay, **not executed by this reviewer**:

```sh
git clone --branch backend/implementation <repository-url> transfer-replay
git -C transfer-replay checkout --detach 5d6423486be5fd448a4d7b42fbbaee264eb07c9c
# Extract the 74-file original overlay into transfer-replay, preserving relative paths.
cd transfer-replay
python work/calibration-room-transfer/run.py check
python work/calibration-room-transfer/run.py render --approved-freeze a995d28014c4c055003d34db193f5657a08d185a281d09ff1d7e667e5405da40
python work/calibration-room-transfer/run.py run --approved-freeze a995d28014c4c055003d34db193f5657a08d185a281d09ff1d7e667e5405da40
```

Use a Python environment with the declared dependencies; the actual local check below reuses the existing pinned environment, with no installation. Do not invoke freeze again. Render and run refuse existing output trees to preserve original/partial runs. For fully offline source delivery, a Git bundle of the frozen commit can replace the clone; no bundle or raw overlay archive was created in this review. Existing reachable Git objects occupy 4,113,113 bytes; that is not a measured bundle size.

## Small portable saved-output replay

portable/ contains 20 projected fits, four projected surface truths, original raw manifests and execution/freeze receipts, unchanged expected-results.json, provenance/omission inventory, and executable replay.py. The gate functions are exact excerpts of frozen score(), withheld_metrics() and summarize(); evaluation/metrics.py is loaded from a checkout only after verifying its unchanged hash. Expected results are read after computation. This is an evaluator reproduction, complementary to the separate independent review in work/transfer-evaluation-review; it is not a second independent algorithm.

Executed from /private/tmp with the existing pinned reproduction Python, --repo pointing at the separate work/material-reproduction/checkout, and output written to this directory's replay-result.json. **All 20 rows, benefits and decisions matched**, exact for discrete values and within relative 1e-10 / absolute 1e-12 for floats. Transfer and promotion remain false. run-receipt.json contains the exact command, checkout hash and package/result identities. No inference, calibration, renderer, full suite or timing rerun occurred.

Full-fit hashes and original full-observation hashes identify omitted bytes. The builder checked full observations against those hashes locally. A clean machine can verify package integrity and recompute projected geometry/withheld arithmetic, but cannot verify the omitted audio, re-admit recordings, rederive the calibration, recover dense responses or newly measure runtime. Original admissions and processing seconds are recorded inputs. The original incomplete withheld RMS is explicitly labeled unique-only subset error, with complete error null.

Both joint room fits recover six planes without false planes but pass only 19/24 unique held-path associations. The independently reviewed post-fit window-design issue prevents interpreting failed promotion as proof calibration has no value: some ideal path pairs are closer than the frozen candidate window. The frozen failed gate is retained unchanged. Exact package byte count and compressed archive hash are in package-receipt.json.
