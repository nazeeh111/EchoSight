# Evaluation audit: baseline is a prototype

The earlier synthetic success and collinear external abstention did not establish measured spatial capability. A new, bounded external dataset now exposes real geometric information and consequential false associations. A separately frozen simulator exposes higher-order false planes. Existing acceptance files and reports remain unchanged.

## Requirement matrix

| Charter obligation | Executed evidence | Status and next action |
|---|---|---|
| Multiple sound-derived 3D surfaces, including height | FLAIR source 0: 24 fixed measured responses with independent laser geometry. Receiver-position singular values: 4.54, 1.64, 0.91 m. | Baseline returns three matching planes, including the floor, but seven unmatched planes. Spatial acceptance fails. Diagnose association and source-response failures. |
| Independent measured reference | FLAIR laser point cloud; acoustic-free plane annotation | Material improvement over the earlier collinear dEchorate fixture. The partial point cloud limits reference coverage; an unmatched plane is not automatically proof of a nonexistent surface. |
| Simulator/solver mismatch and null controls | Exact second-order image lattice, independent fractional-delay renderer, overlapping paths, finite panel, edge-path surrogate, two emitters, nonlinear distortion, clock warp and diffuse clutter | Baseline produces 25 false planes across 13 new cases. Harder acceptance fails. Higher-order ambiguity is consequential. |
| Finite interior structure | Finite panel with geometric specular-visibility checks | Both panel cases recover six room planes but miss the panel. Small-object reconstruction and physical extent recovery remain unsupported. |
| Realistic diffraction | Weak edge-scattering paths | This is explicitly a path surrogate, not validated wave-equation diffraction. Full diffraction remains an evidence gap. |
| Honest uncertainty | Two of three matched FLAIR planes fall outside reported 95% local offset intervals | Conditional covariance omits real bias. It is not calibrated physical confidence. |
| Serious competitor with equal inputs | Main method and direct-plane grid consume identical observations in every case | Main method wins some comparisons; both fail measured reliability. Earliest-echo fitting is only the simple baseline. |
| Frozen, reproducible evaluation | New acceptance files and input selection written before acoustic processing; immutable baseline archive | All failures remain. Later fixes produce regression evidence on seen cases, not fresh blind tests. |

## Dataset and provenance

[FLAIR's primary Zenodo record](https://zenodo.org/records/17037517) provides 270 measured responses and independent laser-calibrated room geometry. API metadata confirms CC BY 4.0, a 115,821,339-byte MATLAB file and upstream MD5 `41e06a449ff39d271e32b3b82ab29341`.

The file contains separately compressed variables. HTTP range requests retrieved only **8,457,668 bytes**. Before any fit, we selected source 0 and 24 microphones from the first four 15-microphone placements. The subset also includes 4,982 laser points spanning the room. This provides useful 3D receiver diversity. Raw data remain outside Git.

`evaluation/flair_subset_manifest.json` preserves source version, license, exact byte ranges, per-range SHA-256, selected receiver indices and the subset hash. Future retrieval verifies those pinned range hashes. Partial compressed streams omit their trailing checksum, and the full upstream MD5 was not locally verified. The report states this limitation. MATLAB column-major decoding was checked against SciPy's standard writer; all four audit-harness checks pass.

`flair.py` fits planes to laser points using seeded RANSAC, a method that repeatedly tests geometric fits while rejecting outliers. It writes `truth-laser.json` **before acoustic processing**. The mapper receives device poses and probe recordings, never laser points, room planes or expected echo labels. The six dominant reference planes include floor, ceiling and four walls; their point residuals are approximately 5–13 mm. Further annotations represent secondary surface layers. Incomplete scanning and automatic annotation can omit physical surfaces.

The predeclared measured criterion requires at least three matching planes, height information and no unmatched planes. It failed and remains failed. The measured responses are convolved with our probe and saved as PCM recordings. This is a hybrid replay of measured room responses, not recordings from our phones. Transform gains and parent hashes are retained. Actual phone processing, speaker behavior and clock performance remain untested.

Other checked options were [MeshRIR](https://www.sh01.org/MeshRIR/), whose single-source subset contains a 3D robot grid but needs further room-reference inspection; [RAF](https://github.com/facebookresearch/real-acoustic-fields), with independent photogrammetric geometry and CC BY-NC 4.0 licensing but 21.6 GB of split archives; and additional dEchorate arrays, whose calibration and generated echo labels limit independence. No bulk download or model installation was performed. FLAIR's small subset was the strongest tractable option.

## Immutable baseline results

The baseline was archived from `1c77336`. The full commit, source hashes and `EVALUATED_COMMIT` marker identify the evaluated code. New frozen evaluation scripts were copied into that archive, which remained unchanged during execution. A preceding live-tree exploratory run is preserved under `work/audit-*-first`; it included uncommitted guards and is not presented as immutable validation.

| Family | Main baseline outcome | Direct-plane grid outcome |
|---|---|---|
| Second-order paths, seeds 601 / 607 | 6 true + 4 false each | 3 true + 7 false; 2 true + 8 false |
| Overlap, 613 / 617 | 6 of 7 true, no false planes each | 3 true + 2 false; 5 true, no false planes |
| Finite panel, 619 / 631 | 6 of 7 true each; panel missed | 6 of 7; 4 of 7; no false planes |
| Edge surrogate with higher orders, 641 / 643 | 5 true + 5 false; 6 true + 4 false | 3 true + 7 false; 2 true + 8 false |
| Two emitters separated by 18 cm, 647 / 653 | 6 true + 4 false each | 6 true + 4 false; 4 true + 6 false |
| Source nonlinearity, 659 | 6 of 6 true, no false planes | Same |
| Nonaffine clock, 661 | No result | Same |
| Diffuse null, 673 | Ambiguous; no definitive planes | One false plane |
| FLAIR laser reference | Three matches; seven unmatched | Two matches; eight unmatched |

The new suite uses rotated rooms and twelve random 3D receiver positions. Its image lattice is

`q_j = 2 m_j L_j + (-1)^p_j s_j`, with reflection order `sum(abs(2m_j - p_j))`.

Order two yields 25 images including the direct source. Independent fractional-delay rendering and finite-panel ray geometry have numerical checks. Edge paths are explicitly approximate. Scene truth and visibility labels never enter fitting.

Portable results are in `evaluation/reports/stress-baseline-1c77336.json`, `flair-baseline-1c77336.json` and `flair-laser-reference.json`. Full recordings and processing outputs can be regenerated under `work/`. More honest abstention can reduce false claims without satisfying the recovery criteria. This audit does not declare the charter complete.

## Reproduction and next action

```sh
python -m unittest evaluation.test_audit_harness
python -m evaluation.flair_subset --destination work/flair-data
python -m evaluation.flair --subset work/flair-data/subset.npz --output work/flair-evaluation
python -m evaluation.stress --output work/stress-evaluation
```

Freeze a corrected code checkpoint before comparison. The tractable problem is distinguishing physical higher-order paths and validating associations. Source qualification is a separate requirement because a distributed speaker or weak direct path can shift apparent reflectors. Develop fixes on independent development cases, then rerun preserved failures. Do not relax criteria to manufacture a pass or feed optical reference geometry into acoustic inference.

A further diagnostic checks all returned baseline planes against the retained laser points without feeding results back into fitting. Two unmatched planes are at least 3.16 m and 3.30 m from every retained point. Thus the failure is not explained solely by omitted small surface annotations. Other unmatched estimates include tilted ceiling-like planes and sparse intersections; the report does not claim that all seven represent nonexistent physical surfaces. Direct-reference timing residuals against supplied poses range from −0.060 to +0.118 ms, with a 0.047 ms median. Grossly wrong direct timing is therefore not the sole explanation. These diagnostics are in `evaluation/reports/flair-point-compatibility.json` and `flair-direct-diagnostic.json`.

## New experiment: calibrated source relocation (frozen, not yet evaluated)

`evaluation/source_relocation_acceptance.json` freezes twelve new cases before their recordings are rendered or the joint mapper is run. Development uses only seeds 1001 and 1003; new held-out seeds begin at 1103. Existing stress and FLAIR cases and criteria stay unchanged. Room, second-order, finite-panel, hidden-parent corner, fixed-source, tangential-source and frame-mismatch cases test whether moving the emitter adds information that repeated receiver recordings cannot supply.

The hidden-parent fixture keeps a true ceiling echo plus a two-wall reflection, while omitting those walls' first-order echoes. A corner image `(-sx,-sy,sz)` can look exactly like reflection in a diagonal plane for one source. Changing x/y source position changes that equivalent plane. Moving only along the corner intersection or repeating the source leaves it invariant. Unit checks establish this identity independently of fitting. Generic motion can reject this particular alias; it does not prove universal uniqueness against every higher-order or distributed-source model.

The default frozen design has twelve receiver poses reused at four source positions, with an additional two-source case. The generator preserves shared receiver survey errors, correlated source survey error, and a single common effective speed. Sessions contain no room geometry, image sources or echo labels. `truth.json` is evaluation-only. The proposed bundle interface is documented in `evaluation/source_relocation_contract.md`.

Acquisition burden is material. A separate development-only `--receiver-count 4` option uses four fixed noncoplanar phones at four source placements, giving sixteen recordings. It does not alter the frozen twelve-receiver cases. Seed 1001's four-phone geometry has centered singular values 2.022, 0.683 and 0.280 m. This confirms three-dimensional arrangement, not successful reconstruction.

A simple comparator, `evaluation/source_relocation_baseline.py`, fits each source independently from identical observations and retains planes agreeing within 5 degrees and 0.15 m in at least 75% of source sessions (minimum two). It keeps one medoid plane's uncertainty rather than incorrectly reducing shared survey uncertainty. It can preserve an invariant phantom or fail when individual sessions remain ambiguous. The serious competitor is the joint plane-grid initializer, using the same observations and physical scorer as the joint mapper.

At fixture freeze, two independent numerical/import tests pass. No new held-out source-relocation results exist yet. Example development commands:

```sh
python -m unittest evaluation.test_source_relocation
python -m evaluation.source_relocation_simulation --output work/relocation-dev --family room_four_sources --seed 1001
python -m evaluation.source_relocation_simulation --output work/four-phones-dev --family room_four_sources --seed 1001 --receiver-count 4
```
