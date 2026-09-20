# Independent final material and appearance review

**Reviewed commit:** `ab5ea75de446b653fec058103030759fc7fbcdfa`

**Disposition:** both previously confirmed P2 findings are closed. No remaining actionable finding was identified in the bounded material/appearance implementation review.

## Verified fixes

1. **Cancelled scene contract:** the result schema now prohibits `interpretation` entirely when scene status is cancelled, matching the runtime publication function. The original independently constructed cancelled payload containing genuine completed material/color estimates is now rejected by the offline scene validator. Valid runtime cancellation output remains accepted.
2. **Palette probability bounds:** shared colors are accumulated with `math.fsum`; only roundoff above total mass one is corrected. The original nine-profile, recording-derived reproduction now produces exactly `1.0` and passes the interpretation schema. The affected regression checks full, incomplete, missing and slightly incomplete palettes, preserving genuine unassigned mass.

## Follow-up evidence

- `followup-ab5ea75/receipt.json`: exact commit, command exit statuses and SHA256 binding for 15 production-module/schema/test files. All 15 matched the committed bytes.
- `binding-ab5ea75de446.json`: original reviewed-byte comparison. The only changes among the 12 originally reviewed production/schema files were `echosight/interpretation.py` and `schemas/result.schema.json`; both deltas were inspected.
- `followup-ab5ea75/cancel-schema-probe.json`: original cancellation reproduction is no longer accepted.
- `followup-ab5ea75/palette-schema-probe.json`: original palette reproduction is schema-valid with probability `1.0`.
- `followup-ab5ea75/probe-results.json`: all independent full-covariance/prior/view-mixture, palette mass, negative admission, empirical profile fit and controlled raw inverse-distance/polarity checks passed again. Raw maximum band-gain error remains **0.008274 dB** in the controlled synthetic probe.
- `followup-ab5ea75/command-4.log`: four focused regression tests passed, including context/geometry separation and shared cancellation publication.
- `followup_ab5ea75.py`: executable orchestrator for the original probes, affected checks and exact-commit binding. Original failure receipts were preserved as `followup-ab5ea75/before-*.json`.

Earlier independent active-job revision, stale reference rejection, raw export/replay and CLI/HTTP checks remain recorded in `REVIEW.md` and the associated evidence. No full suite was repeated here; the coordinator's clean-checkout lane owns assembled reproduction.

## Scope and limits

This closes the two concrete software contract defects found at `bc46e970e63039c434fab15a2c71b91c0d690be2`. It does not establish universal correctness, real-material identification accuracy, physical probability calibration or optical color measurement. Outputs remain conditional reference-library comparisons and supplied contextual sRGB mixtures. Route identity and physical independence remain declarations/experimental requirements, not properties proven by matching identifiers or hashes.

No production edits were made by this reviewer. A concurrent README-only modification appeared after the follow-up; it was preserved and does not affect the exact committed runtime/schema/test binding above.
