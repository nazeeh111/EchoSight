# Controlled material demonstration review

Result: fresh demo passes all eight declared gates. Independent saved-output checks recover six room planes under the 5-degree/0.10-m one-to-one rule, with three correct synthetic filter estimates (two flat, one low-pass) and three explicit unknowns. This is a review of the coordinator's demo by the interpretation implementation author; the separate fresh runtime/math reviewer remains necessary.

Executed from the repository root with the existing pinned environment:

```sh
.venv/bin/python -m evaluation.material_development --output work/material-demo-review/fresh-demo
.venv/bin/python work/material-demo-review/verify.py
```

Both commands completed successfully. `demo.txt`, `verify.txt`, `verification.json` and all fresh raw/results remain beside this report. The run used software version 0.2.0, Python 3.12.14, NumPy 2.3.5 and SciPy 1.18.1. Room result ID: `result-266aa1638e2b40209c32`; implementation SHA256: `f1338951803defafa12155b87ce0e15b74fbc76bcd662ca5433cee28a730bb9c`.

## Evidence boundaries checked

- The renderer writes known synthetic planes/filters to separate truth files. The processing sessions contain supplied source/receiver/probe calibration and recordings, without room planes or query material labels. Reference labels are explicitly supplied training labels. The demo reads generating query truth only after all processing outputs have been saved.
- A second recording-to-result computation of the existing room inputs and both reference-profile rebuilds ran with Path file access guarded to reject every `truth.json` read. All outputs/profile dictionaries matched the original saved outputs exactly. The guard observed 35 permitted file accesses. This is a concrete runtime check in addition to reading the call chain.
- All 56 original manifest entries (48 WAVs and eight session/truth files) retain their hashes. Context-bearing manifests are new files; originals are not rewritten. Exact identities appear in `verification.json`.
- Each estimated material has at least the declared three valid views; all six surface rows retain the full evidence denominator. Probabilities describe a conditional mixture over usable views. Unknown surfaces still have one/two eligible views but do not satisfy minimum_views. They are not silently discarded from reporting.
- The three available color outputs equal the supplied palette mixture: 0.8 for the declared swatch and 0.2 unassigned. These are provided contextual priors, not acoustically recovered optical colors. Unknown material surfaces have no colors and unassigned mass one.
- The reused reference keeps its one inferred plane and exactly one interpretation row, with zero valid material views and no color output. The wrong-profile control keeps all six original room planes and six unknown material/color entries. The null control has no geometry or material output.

## One finding and its resolution

The initial runner's reused-reference gate used `all(...)`, which could succeed vacuously if interpretation rows disappeared. Current output was nonempty and correct, so this was an acceptance-test gap rather than an observed material-inference failure. The coordinator strengthened the gate to require one reference plane, identical reused geometry and exactly one interpretation row. I verified the exact source delta and evaluated the revised condition against the already saved outputs: it passes. No raw rerun is needed for this gate-only change.

Initial runner SHA256: `5597e5ca433b4a10e392fdc3b67bb1c6dc3cf64d281a4574aed00cca19f1a8f0`.
Revised runner SHA256: `2527c478c9d5ca3c1d18c0d5416fb71922237a94a2c9a26c51f812bda67659ce`.
`gate-followup.json` proves reconstructing the original source by reverting only this check yields the original hash. Runtime source files remained unchanged during the fresh demo (`code-delta.json`). Detailed result/context/profile hashes are in `verification.json`.

## Limits

The classes are two supplied synthetic reflection filters, not measured construction materials. The one-dB profile regularization, cutoff 16, minimum three views and palette priors are explicit development settings. The observed unit conditional class weights do not establish physical certainty, calibrated probabilities or unseen-material performance. References and query use the same stated transducer chain, route and point-source/inverse-distance simulation assumptions. This is a working raw-input integration demonstration, not a new blind scientific benchmark or device qualification. Six room planes do not imply six material identifications, closed physical boundaries, empty space, or optical color recovery.

No unresolved material finding was established within this bounded demo review. No production files, legacy scientific cases or full suite were edited/rerun by this lane.
