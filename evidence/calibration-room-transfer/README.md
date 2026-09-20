# Calibration-to-room transfer: completed, not promoted

The authorized 56-recording study ran once at **5d6423486be5fd448a4d7b42fbbaee264eb07c9c**, using the unchanged [original freeze and protocol](../calibration-room-transfer-plan/). All 94 frozen input hashes matched; all 20 method/case runs completed. The 56 new recordings comprise 24 room mapping, eight withheld and 24 direct-only controls. The 48 original calibration recordings were preserved. These are synthetic recordings, not measurements from our devices.

**Transfer and promotion failed.** Both joint-calibration maps recovered all six room planes, including height, with zero unmatched planes. Each validated only **19/24** withheld paths uniquely. Every method admitted all 12 mapping recordings, and every direct-only control returned zero planes. No public calibration feature was promoted, and no production extraction or mapping policy changed.

| Room seed | Calibration | Matched / unmatched planes | Unique held paths | Mean anchored plane error |
| --- | --- | --- | --- | --- |
| 2821 | Nominal | 6 / 0 | 17 / 24 | 10.777 mm |
| 2821 | One x-reference | 6 / 0 | 19 / 24 | 6.667 mm |
| 2821 | Joint references | 6 / 0 | 19 / 24 | 2.528 mm |
| 2833 | Nominal | 6 / 0 | 19 / 24 | 15.700 mm |
| 2833 | One x-reference | 6 / 0 | 17 / 24 | 23.913 mm |
| 2833 | Joint references | 6 / 0 | 19 / 24 | 2.324 mm |

Joint-grid runs also recover six planes and validate 19/24 held paths. The first-echo baseline recovers no room plane. Joint processing took 0.878 and 0.877 seconds on the recorded machine; this timing belongs to the frozen 0.1 runtime, not a fresh 0.2 measurement. [All 20 original rows, failures and timings](replay/expected-results.json) remain unchanged. Original results SHA-256: `7acbd36695af09e0924cc5e40054ff80cb17c135186784d45eeaa7f093c4bf5b`.

## Why the held gate failed

[Independent review](audits/transfer-independent-review/REVIEW.md) found two distinct limits:

1. The conservative extractor removes visible local maxima through its 17-sample spacing and relative-height screens. Earlier attempts to relax or replace extraction produced false geometry; this study does not establish a safe replacement.
2. The frozen validation design rejects correct truth. Two true held-path pairs are separated by **173.021453 and 196.986783 µs**. Both candidates fall within each prediction's inclusive ±200 µs window. Even perfect planes, poses and all six perfect peaks therefore validate only **20/24**. This post-hoc oracle identifies a gate-design flaw. It does not alter the actual 19/24 outcome or show that calibration lacks utility. Biased predictions can move window edges, so this is not a claim that every mathematically possible output must fail.

**Reporting clarification:** original `withheld.rms_s` and `max_abs_s` use only uniquely validated subsets when `complete` is false. Complete 24-path errors are unavailable. The replay output labels those subset values explicitly and sets complete errors to null. Do not compare different subsets as qualifying accuracy gains. Original JSON and runner bytes are retained.

## Reproduce the saved evaluation

From the current repository root with its Python dependencies installed:

```sh
python evidence/calibration-room-transfer/replay/replay.py \
  --repo "$PWD" --output work/transfer-gate-replay.json
python -m evaluation.held_path_preflight \
  evidence/calibration-room-transfer/ideal-held-catalog.json \
  --output work/transfer-ideal-preflight.json
```

Use new output files. Replay must report 20 matching rows with both transfer and promotion false. The preflight deliberately exits **1**, reporting **20/24** and the four conflicting paths. Its input is a compact post-hoc catalog of the original exact true arrivals. This new evaluation helper detects incompatible declared catalogs before future data collection; it is not a revised scorer for the completed study. Inclusive endpoints, equal-delay conflicts, incomplete/duplicate identities and the distinction between unique ideal candidates and disjoint windows have executable checks.

The [replay package](replay/README.md) recomputes geometry matching and held association from compact saved projections. It does not process audio, refit calibration/maps, independently verify omitted raw bytes or remeasure runtime. Admission, full-observation hashes and timing are retained inputs. Exact projections and omissions are listed in [source identities](replay/source-identities.json).

For full recording-to-result reproduction, see [raw-input setup](RAW_REPLAY.md). The optional 4.45 MB archive contains the original inputs missing from Git; generated query recordings can be recreated by the unchanged frozen runner. No raw audio is added to the repository tree.

## Review and remaining experiment

[Acquisition audit](audits/transfer-acquisition-review/FINDINGS.md) verifies distinct raw inputs, source continuity, survey separation and admission boundaries. [Independent scoring](audits/transfer-evaluation-review/REPORT.md) recomputes all 20 results using a separate matching implementation. [Scientific review](audits/transfer-independent-review/REVIEW.md) checks the full correlated source/speed covariance, actual failures and the oracle. [Runtime comparison](audits/transfer-runtime-review/REPORT.md) finds unchanged geometric arithmetic for these context-free sessions, while explicitly retaining different 0.2 identities, output shape and unmeasured timing.

The promotion attempt is closed. A bounded follow-up would use **eight new withheld recordings**, two instances at four new common positions, with the existing maps, calibration and null controls unchanged. Before generating any audio, freeze positions and independent survey/noise streams, verify all 24 ideal paths, and check declared uncertainty and sampled detector-spacing margins. Keep six planes including height, zero unmatched at 5°/0.10 m, complete 24-path RMS ≤100 µs and maximum ≤200 µs, the original ≤10-second mapping times, and the prespecified gain against both nominal and one-reference calibration. Each comparator must fail the complete gate, or joint must improve complete RMS by at least 1/48000 second and six-wall mean error by at least 3 mm, in both instances without false/missed-plane regression. Any failure remains explicit; no automatic promotion follows. This follow-up is **not executed or frozen**, and cannot replace the original result. [Design requirements](audits/transfer-independent-review/DESIGN_RECOMMENDATION.md) explain margins and the model limits.

Own-device [H0–H6 qualification](../../docs/HARDWARE_ACCEPTANCE.md) and the [74-record material experiment](../../docs/MATERIALS_APPEARANCE.md#planned-physical-qualification-two-known-samples) remain separate. The new synthetic point estimates establish neither physical accuracy nor complete room recovery under the retained harder and measured-data failures.
