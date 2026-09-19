# Independent exact integrated-commit follow-up

Verdict: no actionable material finding in commit `5d6423486be5fd448a4d7b42fbbaee264eb07c9c` for the integrated support-pruning repair. The prior independent candidate review remains applicable without repeating its mathematics or broader probes.

## Immutable identity and runtime scope

`git show 5d6423486be5fd448a4d7b42fbbaee264eb07c9c:echosight/multisource.py` has SHA-256 `b61f4742927c8270a5133526bddbff5080b806242f6ff2e08310bc9499622085`, identical to the reviewed isolated V2 module. The only production/runtime change relative to prior checkpoint `c3de891` is that file. No dependency or schema change was added. The integrated module, tests, fixtures and frozen acceptance file in the working tree were confirmed identical to their bytes at this commit before executing tests. Repository status was clean when checked.

Detailed file hashes and the observation fixture's complete key inventory are saved in `integrated-5d64234-identity.json`. The original acceptance hash remains `626166532905ca48a53639f6521df93aecc6f2bcf8dd77618bd20b8272fd35f7`.

## Integrated tests and fixture isolation

The recording-derived observation fixture is byte-identical to the previously reviewed fixture. It contains recording observations, calibration, poses, timing and provenance; it contains no evaluation surface geometry or path-order labels. Evaluation geometry resides in the separate evaluation JSON and is loaded by the test only after `infer_scene_bundle` returns. Existing fixed matching limits remain 5 degrees and 0.15 m. The recovery test checks the original six-plane, two-horizontal, zero-false result and unchanged source support/unknown-extent behavior.

The added cancellation test wraps the real optimizer, requests cancellation after the first ordinary least-squares refit, and verifies no additional fit occurs and no surfaces/hypotheses are returned. It exercises the newly introduced cancellation boundary without substituting numerical fit results.

Direct local execution on the verified commit bytes:

```sh
.venv/bin/python -m unittest tests.test_multisource_support_recovery -v
```

Both tests passed in 8.342 seconds. Full output is retained in `integrated-5d64234-tests.txt`. This is an integrated regression check, not an independent clean environment reproduction; another worker owns that full-suite task.

## Claims and retained evidence

Read the integrated recovery README/RESULT, mismatch README/rerunner/manifest/results/completion record, STATE changes and coverage changes. The current summary distinguishes repaired exposed synthetic evidence, inference-only replay, raw verification already performed by the builder, unchanged historical failures and absent own-device validation. Historical candidate-stage reports retain their historical integration status; the current README and STATE identify integration explicitly.

All files in the mismatch package match the committed MANIFEST hashes. Its results contain 15 comparisons, all with `surface_outputs_exactly_equal=true`, consistent with the completion record and current documentation. These are inspected independent-evaluator results, not a second local rerun by this reviewer. The rerunner uses archived original/V2 modules and loads truth after both fits. Preserved measured unmatched surfaces, source-model false surfaces, two-source failure and failed overall spatial acceptance are not hidden or converted to success. Frozen criteria are unchanged.

No unreviewed runtime addition, fixture truth leakage or material mismatch between current claims and supplied evidence was found. Global optimality, post-selection uncertainty coverage, broad reflection-order identification and physical accuracy remain unestablished, as in the initial review. Remote hash verification is the coordinator's reported result; this review independently verifies the local Git object and executed bytes at the exact commit above.
