# Supported-room recovery after a failed candidate refit

The isolated candidate recovers all six room walls in the retained higher-order seed 1129, including floor and ceiling, with zero false definitive surfaces. Original code returns no_result after one non-wall candidate loses one supporting view. All eleven other retained frozen relocation cases have unchanged matched/false counts. No production edits have been made.

## Executed evidence

- `refit-trace.json`: unchanged original inference reproduces the abort. One candidate changes source support [10,11,10,4] to [10,11,10,3]. Six true room candidates retain 9–12 views per source.
- `experiment-freeze.json`: first candidate SHA256 b1ac9e0e34f542d8f890797fd109db29ea4c3dbca7698bf30edb6abef28754ce and unchanged acceptance SHA256 626166532905ca48a53639f6521df93aecc6f2bcf8dd77618bd20b8272fd35f7 frozen before comparison.
- `experiment-results.json`: both methods replay the same saved observations for all twelve original cases. Only seed1129 changes. This excludes raw extraction time. The coordinate-frame control returns calibration_needed for both inference-only methods, which differs from its raw-entry acceptance status and is not a new regression.
- `raw-check-results.json`: original and frozen first candidate both process the actual retained recordings for1129 and raw control1193. The full input hashes are unchanged.1129changes0matched/0false/3.903s to6matched/0false/5.247s;1193both no_result and pass.
- `v2-freeze.json`: candidate b61f4742927c8270a5133526bddbff5080b806242f6ff2e08310bc9499622085 adds cancellation checks per prune pass and per fit, plus a comment adjustment. Arithmetic and gates are unchanged. The first candidate and evidence remain untouched.
- `raw-check-v2-results.json`: final candidate actual recordings repeat1129six matched, two horizontal, zero false,5.196s versus original0matched/0false/3.844s. Both1193raw controls return no_result and pass. All hashes unchanged. These are observed local runtimes, not hardware accuracy or broad performance guarantees.
- `regression-test-results.json`: the real recording-derived fixture fails the original code at0matched versus6required and passes the candidate. Candidate run4.734s. Only unused response-display arrays were removed from the fixture; candidates, timing, amplitudes, poses, shared covariance and waveform provenance remain unchanged. Truth is separate and loaded only after inference.

## Candidate behavior and integration files

`production-candidate.patch` changes only the final joint refit/support block. It removes unsupported provisional candidates, recomputes exclusive assignments, refits and repeats until the surviving model meets the original support rule or becomes empty. Each failed pass strictly reduces the candidate count, so at most ten candidates can be removed. A diagnostic records the removed count. Covariance, source-rank discrimination, parent-subset comparison and hidden-parent/point alternatives then run unchanged. Cancellation is checked each pass and fit.

The final1129result keeps the nine surviving first-order candidates as an explicit hypothesis and a six-parent higher-order explanation as a competing hypothesis. Only the six invariant room parents are definitive. The three remaining non-wall first-order candidates are not promoted. Removing candidates can in general remove alternative physical explanations; unchanged hidden-parent and fixed/tangential-source controls show no regression in this bounded evaluation, not universal reflection-order identification.

Ready for coordinator integration after independent review:

1. Apply `production-candidate.patch` to `echosight/multisource.py`.
2. Copy `test_multisource_support_recovery.py` to `tests/` and the two files under `fixtures/` to `tests/fixtures/`.
3. Run the meaningful regression plus affected multi-source/path/cancellation checks and selected final assembled gates.

## Limits retained

The new result repairs a concrete all-or-nothing software failure on an exposed synthetic regression. Two-source1103still returns ambiguous with no definitive surfaces and fails the original four-wall/height recovery requirement. It does not repair two-emitter aliasing, harderstress30true/48miss/0false or measured-room failures. The new two-reference calibration result supplies no directly paired room-mapping recording and is not used to claim this gain. No closed waveform/null/candidate-budget approach was reopened, no raw data generated, and no criteria or thresholds changed.
