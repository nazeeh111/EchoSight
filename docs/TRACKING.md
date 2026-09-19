# Carrying display tracks across result revisions

Comparison now returns `current_tracks` for every current surface, including newly supported surfaces. Pass the preceding comparison when comparing the next pair of **raw** results. This preserves display labels across three or more revisions without copying labels into the scientific results.

This is declared display state, not authenticated measurement evidence or persistent physical-object identity. Matching uses the existing one-to-one plane continuity gates in a compatible surveyed frame. It does not prove that two supported patches are the same physical wall, that missing echoes establish disappearance, or that an observed change has a particular cause. No input result or prior comparison is mutated.

## Interfaces

Python:

```python
from echosight.evolution import compare_results

comparison_ab = compare_results(result_a, result_b)
comparison_bc = compare_results(
    result_b, result_c, previous_comparison=comparison_ab
)
```

HTTP: `POST /v1/compare` accepts the existing `previous` and `current` objects and an optional `previous_comparison` object. The existing bounded comparison-body limit applies. A malformed or stale carry object returns HTTP 400.

CLI:

```sh
python -m echosight compare result-a.json result-b.json --output comparison-ab.json
python -m echosight compare result-b.json result-c.json \
  --previous-comparison comparison-ab.json --output comparison-bc.json
```

CLI result inputs use the existing per-result byte limit; the prior-comparison file is limited to 1 MiB. Invalid carry state fails before saving output, preserving an existing output file.

A comparison contains:

```json
{
  "schema_version": "1.0",
  "previous_result_id": "raw-1",
  "current_result_id": "raw-2",
  "status": "comparable",
  "current_tracks": [
    {"surface_id": "fit-2", "track_id": "fit-0"}
  ],
  "tracking_state_source": "previous_comparison"
}
```

This fragment illustrates the added fields; the complete comparison also includes correspondences, support changes, calibration gates and interpretation limits. The formal complete contract is [comparison.schema.json](../schemas/comparison.schema.json).

## Binding and uniqueness

A supplied prior comparison must have schema version `1.0` and status `comparable`. Its `current_result_id` must equal a nonempty `previous.result_id`. Its `current_tracks` array must cover **exactly** the previous result's surface IDs, including surfaces born at that prior step. Every entry has exactly `surface_id` and `track_id`; both identities must be unique across entries. IDs are strings of 1–160 characters, and at most 128 entries are accepted by the processing core. The HTTP route retains its narrower 64-surface limit.

Result surface IDs and effective starting track IDs must also be unique and bounded. A supplied optional `track_id` cannot be null. When prior display state is supplied, an explicit track label on a previous surface must agree with it; a contradiction fails instead of silently choosing one identity. Result IDs and status labels, when supplied, must also be bounded strings.

These checks bind the carry object to a declared revision; they do not authenticate it. A caller can intentionally choose display labels. Geometry association and measurement provenance remain separately derived from the results. Formal JSON Schema checks structure and exact duplicate entries; the runtime additionally checks cross-entry track/surface uniqueness and complete coverage against the previous result.

## Continuity, births and missing surfaces

For a matched surface, the previous comparison's track ID continues through the existing one-to-one correspondence. Without a carry object, compatible two-result matching retains the previous surface's explicit `track_id`, or its `surface_id`, as before. Current-result labels do not override a match or create a link to missing history.

A newly supported surface receives a deterministic `track-birth-…` label bound to this comparison and its geometry. It does not reuse the raw surface ID as a historical identity. All previous track labels, including unmatched ones, are reserved while assigning births. If a generated birth label collides with a reserved or already assigned label, a deterministic nonce produces a different label. There is no random identifier state or hidden database.

An unmatched previous surface ends continuity. Only current surfaces appear in the next carry map. After an empty intermediate result, a later surface is a birth, even if its geometry or raw surface ID resembles a much earlier one. There is no hidden-history lookup, split/merge tracking, missed-detection bridging or global reidentification. Deterministic labels are scoped to the declared comparison sequence, not guaranteed unique across independently constructed histories or deliberately reused revision identifiers.

An incomparable result receives fresh local labels covering its current surfaces but makes no correspondences. Its comparison must not be carried as continuity state; an attempted carry is rejected. A caller can begin a new two-result comparison when it has compatible calibrated results.

## Verification

```sh
python -m unittest tests.test_evolution tests.test_tracking_integration tests.test_api tests.test_schemas -q
```

Tests cover four raw revisions, births, missing/empty intermediates, stale/incomplete/duplicate/conflicting state, identifier limits, deterministic birth collision handling, no input mutation, real HTTP and CLI round trips, malformed CLI-state output preservation and the published schema. Existing coordinate-origin invariance and calibration-change refusal remain covered. These are display-state integration tests, not new acoustic accuracy evidence.
