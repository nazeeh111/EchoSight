# Session-scoped support comparison repair

At57e25b2, two declared sessions with the same four local capture IDs reported zero new/lost support. The minimal prepared-result regression fails before the repair; this is a declaration/identity defect, not an acoustic or hardware experiment.

Comparisonv1.1 now computes support deltas on `(session_id,capture_id)` pairs. Missing scope leaves support comparison unavailable, with null counts, rather than guessing recording continuity. Raw scene format remains1.0; prior1.0/1.1 comparisons can carry display tracks. Inputs are not mutated. [Contract](../../docs/TRACKING.md).

The32affected evolution/API/schema/real HTTP/CLI checks pass in8.479s. They include cross-session equal-name collisions, same-session refinement, missing/contradictory identity, old/new carry, stale-state rejection and preserved CLI output after invalid input. This is bounded software validation. Independent3745665support review passes within scope; it also exposed legacy cancelled geometry being reused in comparisons. A follow-up guard now returns incomparable and no tracks for a cancelled current result, with21affected tests passing. Full assembled196tests pass; fresh combined review remains pending.

```sh
.venv/bin/python -m unittest tests.test_evolution tests.test_tracking_integration tests.test_api tests.test_schemas -v
```
