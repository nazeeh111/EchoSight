# Independent bounded validation follow-up

Reviewed immutable commit: **`1c773367f787a551aec0f15fc244b5fe9290dee3`**.
Previously reviewed baseline: `565769a078b3f834de626a5d0697c21f5ceb5e8a`.

**No remaining P1/P2 issue was established in this bounded change.** The new validation rejects malformed coordinate-frame identities and preserves the distinction between an absent frame and a valid, explicitly identified frame.

## Scope and exact changes

I unpacked this commit using `git archive` into `work/review-1c77336-snapshot` and inspected the immutable diff against the previously reviewed commit. It contains only:

- `echosight/storage.py`: optional supplied `coordinate_frame_id` must be a string of 1–160 characters.
- `echosight/evolution.py`: the same validation for supplied result acquisition metadata before comparison.
- Matching session/result schema constraints.
- Two regression tests.

I made no implementation, test, schema or documentation changes. This is a targeted follow-up to the assembled-backend review in `work/review-565769a.md`, not a repetition of the complete scientific review.

## Independent execution

All commands ran from the immutable snapshot using the project Python environment.

- `python -m unittest discover -s tests -p test_storage.py`: **16 passed**.
- `python -m unittest discover -s tests -p test_evolution.py`: **7 passed**.
- Additional independent probes checked `None`, `False`, zero, one, a list, an empty dictionary, a dictionary containing a frame, an empty string, and a 161-character string. All nine were rejected by session validation and result comparison. Pipeline processing exposed `invalid_session` for each malformed supplied frame.
- One-character, 160-character ASCII and 160-character Unicode identities were accepted and comparable when otherwise identical. This agrees with the schemas' character-length requirement.
- An absent frame remains absent in `validate_session({})`. Two raw result objects with absent frame metadata remain `incomparable`, as do absent-versus-explicit and two different explicit frames.
- Processing a valid calibrated session without a supplied frame still generates the deterministic default `session:frame_default`; comparing that result with itself remains `comparable`. Thus the patch does not remove the existing pipeline default or silently equate unidentified raw results.
- Creating a stored session with an invalid dictionary frame raised `ValueError` and did not publish a session directory retrievable through `get_session`.
- Read both JSON schema files and verified that their frame properties exactly specify string type, minimum length 1 and maximum length 160.

The malformed and absent-frame behaviors are intentional and consistent: a supplied invalid value is an error; missing acquisition identity in raw comparison input is an incomparable result; the pipeline may supply its documented session-scoped default.

No broader full-suite, frozen-evaluation or external-data rerun was performed here. Those are separate coordinator checks. The earlier review's scientific and hardware limits remain unchanged.
