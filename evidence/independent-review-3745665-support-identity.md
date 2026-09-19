# Independent support-identity review

Reviewed exact commit `3745665352f59bc88e432b1f703054ab29398ce1` against `0f05dd1`, using an immutable `git archive` in `work/review-3745665-snapshot`. No live implementation changes were inspected or made. No P1/P2 finding remains in the support-identity delta itself. The coordinator subsequently expanded this review to the legacy cancelled-result boundary; one inherited P2 was reproduced there, as detailed below.

## Evidence and result

An independent minimal two-result reproduction, without importing the builder's fixture, verifies the consequential change: two sessions both naming their recordings `0` and `1` previously returned zero new recordings and zero additional support. The reviewed implementation returns two additional references scoped to session B, two lost references scoped to session A, and two new recording references. It still reports no established physical scene change. Reprocessing the same session under a different result ID returns zero additions; appending recording `2` returns exactly one.

The custom probe executed 13 successful comparisons covering cross-session local-name reuse, same-session reprocessing/append, either/both missing identities, acquisition-level fallback with absent/null/matching top-level identity, and both v1.0 and v1.1 carry through subsequent v1.1 comparisons. Every result passed the published comparison schema. All successful calls preserved both input results and the supplied comparison byte-equivalent as JSON values. Fifteen malformed identity, contradictory top-level/acquisition scope and duplicate capture cases rejected with `ValueError`.

A real CLI subprocess accepted a saved v1.0 comparison, emitted v1.1, preserved the original display label, and retained the existing output bytes when the next input contained contradictory session declarations. The exact parent implementation was independently loaded from Git to establish the before/after behavior; its bytes are retained with the probes.

The focused evolution and tracking integration test run exercised 20 distinct tests. Nineteen passed immediately; the HTTP test initially failed only because the sandbox denied binding its local socket. A separately authorized rerun of that single HTTP test passed. This also verifies three API comparisons, schema-version propagation, scoped counts and stale carry rejection. Other focused checks cover births, deaths, empty intermediates, calibration incompatibility, coordinate-origin invariance, malformed geometry, complete track carry and CLI output preservation. No full-suite rerun was performed.

## Contract assessment

The source at `echosight/evolution.py:16` resolves declared session identity from the top-level or acquisition object and refuses disagreement. The set key at line 27 now includes session identity. Support deltas at lines 200–214 and recording deltas at lines 218–221 therefore preserve local capture namespaces. Missing scope produces unavailable support comparison with null counts and empty delta arrays; it does not suppress otherwise valid geometric continuity. Incompatible geometry also leaves support comparison unavailable.

The v1.1 schema requires the new scope/status/reference fields while continuing to validate legacy v1.0 comparison outputs. Runtime carry intentionally consumes only bounded, revision-bound complete `current_tracks` state from either version; old support counts do not propagate into newly calculated support evidence. Existing API and CLI entry points pass the comparison through without discarding the new fields. The frontend and tracking documentation describe the required consumer migration, nullable counts, local-ID namespace distinction and physical-identity limitation consistently with observed behavior.

Scope is the documented top-level/acquisition session identity of an ordinary single-session result. These are caller declarations, not authentication, content uniqueness or physical independence. Arbitrary unsupported extension fields are not a second identity authority. A caller can deliberately forge result IDs or display labels; this change does not claim to authenticate carry state. JSON Schema verifies structure, while runtime verifies cross-entry uniqueness and scope consistency. The checks do not establish acoustic accuracy, physical object identity, unrelated experimental multi-source comparison support or global sequence identity.

## Supplemental P2: refuse cancelled results at the comparison boundary

**Location:** `echosight/evolution.py:134–174`, especially the calibration-only eligibility decision at line 164. `_validate_result` accepts `cancelled` as a bounded status string, but `compare_results` never prevents it from participating in geometric association and support deltas.

This is a real legacy output path, not an invented unauthenticated payload. The exact reviewed inference at `echosight/inference.py:521` can return selected surfaces after cancellation before its ambiguity checks finish. A public cancellation predicate timed to the selected-surfaces stage reproduces it with the existing coplanar fixture: completed inference returns `ambiguous` with zero definitive surfaces; the same inference interrupted at that stage returns `cancelled` with one provisional plane. The probe does not monkeypatch the fit, geometry, or runtime source. It decorates the actual returned objects with ordinary pipeline-style session/acquisition metadata and compares them.

Comparing a completed noncoplanar previous scene to that cancelled coplanar scene currently returns `comparable`, one continued display track and eight additional support references. Reversing the inputs also continues a track from the cancelled result. The parent implementation also returns a correspondence, confirming that the eligibility defect predates this patch. The newly corrected scoped counts do not cause it.

Treat either cancelled input as ineligible for continuity and support comparison. Returning `incomparable` with an explicit cancellation reason is suitable; do not then construct display tracks from provisional cancelled geometry. Ordinary empty `no_result` scenes can still intentionally end continuity, so this finding does not justify a blanket rejection of every unsuccessful scene. Fixing future inference cancellation publication is necessary but does not protect saved legacy exports or pure-core callers at this boundary.

Executed reproduction: `work/review-3745665-cancelled-probe.py`; exact output: `work/review-3745665-cancelled-probe.json`. It uses immutable commit code and loads the exact parent evolution bytes to confirm attribution. The supplemental source hash file identifies inference, pipeline and fixture bytes inspected. This finding concerns unfinished interpretation reaching the frontend's versioned continuity/evidence interface, not physical identity authentication. No new acoustic experiment or broad-suite run was needed.

## Exact artifacts and reproduction

- `work/review-3745665-probes.py`: executed independent reproductions.
- `work/review-3745665-probes.json`: detailed cases, exact parent commit and SHA-256 hashes of the inspected source/schema/docs/tests.
- `work/review-3745665-parent-evolution.py`: exact prior implementation used for the before/after reproduction.
- `work/review-3745665-tests.txt`: focused run, including the actual sandbox bind failure.
- `work/review-3745665-http.txt`: successful single HTTP rerun.

Inspected code is `echosight/evolution.py`, its unchanged API/CLI comparison entry points, `schemas/comparison.schema.json`, relevant result schema fields, `tests/test_evolution.py`, `tests/test_tracking_integration.py`, and the tracking/frontend changes against original charter requirements. The hash manifest identifies the exact inspected bytes. Archived copies and restoration instructions are under `evidence/support-identity/independent/`; the review is also copied to `evidence/independent-review-3745665-support-identity.md`.
