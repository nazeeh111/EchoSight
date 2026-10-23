# Actual backend result viewer

Start `python3 demo/server.py --open` from the repository root. Use **Inspect backend results** on the welcome screen, or open `http://127.0.0.1:8765/results.html` (substitute your chosen port). The existing animated room is a separate simulated demonstration.

Generate a real processing artifact and open its `result.json` with **Open result JSON**:

```sh
python -m echosight demo work/viewer-room --seed 1 --captures 12
```

This command generates and processes synthetic recordings. It does not measure a physical room. You can also import a scene-result JSON retrieved from the local API or produced from your own recordings. Files are read in the page, not uploaded. Standalone inspection does not call the recording API or perform inference. The optional [local processing workspace](WORKSPACE.md), enabled explicitly with `echosight serve --ui`, imports selected originals and orchestrates backend jobs. Neither route initiates device acquisition or certifies imported provenance.

The opt-in workspace also compares a kept previous snapshot with the displayed result through the existing local comparison API. It reports changes in inference and recording support, with incomparable calibration and stale states explicit. See [comparison steps and limits](WORKSPACE.md#compare-successive-results). The standalone inspector remains file-only.

## What is displayed

- Supplied `vertices_m` and `triangles`, directly in metres, right-handed coordinates, Z up. No asset room or simulation truth is used to construct these meshes.
- Selected surface normal/offset, conditional standard deviations, exact capture/candidate IDs and observed/predicted excess delays with signed residuals. Seconds become milliseconds by multiplication by 1000. These are source-buffer intervals, not independently calibrated physical time.
- Rays only when source and receiver poses are supplied. Otherwise only supplied reflection points are drawn. Patches describe reflection support, not physical wall edges, enclosure, objects or safe empty space. Display colors identify patches; they do not encode material/color estimates.
- Alternative hypotheses individually, never unioned with definitive surfaces. Bare planes/image sources have a qualified numerical inspector and no invented mesh extent. Candidate sets may reuse evidence IDs; each displayed entry remains independently selectable. Rank-deficient/unavailable angular uncertainty stays unavailable.
- Material/appearance entries only when their interpretation is complete and bound to this exact result ID and a unique definitive surface. Material comparisons remain conditional on the reference library; appearances are supplied contextual predictions, not acoustic color measurements. Alternative hypotheses do not inherit definitive material estimates.
- Explicit ambiguous, no-result and cancelled states. Cancelled outputs retaining dimensions, guidance or interpretation are rejected. Stale output is labeled for reprocessing; absent freshness information is not presented as current.
- Diagnostics, measurement guidance, supplied provenance and local plane separations. Separations do not establish enclosed room dimensions. No calibrated probability of physical correctness is inferred from standard deviations or reference-library weights.

## Display checks and limits

Imports must use the scene-result v1.0 research contract with `physical_validation: false`; session/result IDs may be absent when the backend does not supply them. This is a bounded rendering validator, not the complete offline JSON Schema validator or an independent scientific audit. Inputs that exceed viewer limits or contradict displayed fields are rejected before replacement. The last usable result is retained when parsing/validation fails. Arbitrary nested metadata has guarded, truncated text presentation.

Maximums: 32 MiB UTF-8 JSON; 64 surfaces per displayed group; 32 hypotheses; 4096 vertices and 8192 triangles per surface; aggregate 100,000 vertices / 200,000 triangles; 32 support records per surface; 32 supplied captures; 64 local separations; 512 diagnostics / 128 guidance entries. Coordinates must be finite and within ±1,000,000 m. These viewer bounds are independent of narrower backend admission rules. Missing WebGL leaves numerical inspection available; it does not enable a substitute geometry claim.

The three bundled examples are byte-for-byte copies of `examples/frontend/{material-room,ambiguous,no-result}.json`, verified by tests. Their existing example metadata preserves source versions, hashes and dense-response omissions. They are actual backend outputs from synthetic recordings, not physical validation or replay archives.

## Verification

```sh
node --experimental-vm-modules --test tests/demo-*.test.mjs
```

26 JavaScript checks pass: ten retained demo tests and sixteen result-viewer checks. They use actual bundled Three.js geometry and bounded-import contracts to cover coordinates/topology, signed delay conversion, resource disposal, missing poses, hypothesis separation, copied-example equality, malformed geometry/statuses, interpretation binding, cancellation retraction and deeply nested metadata. Full-page controller checks also cover unavailable WebGL, preservation of selected evidence on failed import, guarded metadata presentation and asynchronous import ordering. No npm dependencies are required.

Browser checks exercised a fresh complete 1.8 MB CLI result from twelve generated recordings (six surfaces), the three bundled examples, selected echo evidence, a bare-plane hypothesis, invalid import preserving the prior result ID, stale warnings and cancellation without geometry. An independent review's four initial findings and a deep-metadata follow-up were corrected and rechecked. This is software and synthetic-data evidence. Existing measured-room failures, own-device qualification and live acquisition/job integration remain unresolved.
