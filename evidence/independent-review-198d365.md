# Independent bounded review: experimental multisource at 198d365

Inspected immutable **198d365f3b13f221ac258332eaaccdf96506a641**, compared with **3c37ed7ac1d11ffb9f90a4d69ebaeede6b8ef18f**, in `work/review-198d365-snapshot` created by `git archive`. All snapshot `echosight/*.py` files were byte-verified against the commit after execution. No implementation edits, Git writes, acceptance changes, held-out runs, or uncommitted experiment inspection were performed.

**Three P2 findings; no P1 established.** Ten focused committed tests passed, but do not cover these defects. The findings concern physical-model sufficiency and input/evidence integrity; they do not reinterpret the known source-diversity and hidden-parent scientific limitations as newly discovered implementation bugs.

## P2: parent alternatives reuse one physical path for distinct peaks

**Location:** `echosight/multisource.py:198–205` and `214–219`.

Subset scoring takes the minimum separately for each original selected candidate. The displayed path evidence repeats that independent choice. There is no one-to-one assignment per recording, unlike the initial first-order model. Consequently, a single specular path can be used twice to explain two separately resolved echo candidates in the same recording. Marginal uncertainty allows either candidate to be individually compatible with that path; it does not make the path generate both peaks simultaneously.

**Public-entry reproduction:** `work/review-198d365-alias-probe.py` constructs four noncoplanar source poses, eight receiver positions, two exact corner-parent echoes, and two distinct peaks separated by 120 microseconds around the corner's double-bounce delay. Source diversity rank is three. Calling `infer_scene_bundle` returns `partial`, two retained parents, and a sufficient two-parent explanation with **24 reused same-session/capture/ordered-path assignments**. One reported path predicts 8.070520529857366 ms for both observed peaks 8.010520529857372 ms and 8.130520529857370 ms. Its competing-model score is approximately 252 versus the selected first-order score 560.1815, so it is accepted and influences the retained intersection. The mathematical helper reproduction also refits the first-order parameters and uses its computed covariance; it does not inject an arbitrary inflated tolerance.

Evidence: `work/review-198d365-alias-probe.json` and `work/review-198d365-alias-probe.public.json`. The latter is the actual public numerical-entry result summary, not a mocked private post-check.

**Implication:** the output claims that a smaller physical parent model explains the same selected evidence, but its assignment cannot generate that evidence under the stated specular-path model. This can remove surfaces from the retained intersection using an inadmissible competing model. The preserved original hypothesis and explicit lack of an absence claim limit the impact; they do not repair the false sufficiency statement.

**Action:** solve exclusive candidate-to-path assignment per recording for each parent subset, use it for score and evidence, and handle equivalent path predictions so aliases cannot create extra independent arrival capacity. Preserve any unexplained selected candidates rather than silently reusing a path. Regression should exercise the public entry point and assert uniqueness of physical path support, not just uniqueness of initial candidate IDs.

## P2: duplicate source-session IDs corrupt source-scoped evidence

**Location:** `echosight/multisource.py:244–261`, with output use at `314–326`; raw loading at `350–361` has the same missing cross-session identity validation.

Neither entry point checks that included source sessions have distinct `session_id` values. The fit distinguishes sources internally by list index, but output evidence identifies each observation by session/capture/candidate IDs. Different source poses using the same session ID therefore collide in the public provenance keys, and the confidence source count uses those colliding IDs.

**Reproduction:** `work/review-198d365-input-probes.py` takes the independent analytic four-source room fixture, changes only source session 1's ID to session 0's ID, and calls `infer_scene_bundle`. It still publishes six surfaces with **192 support entries but only 144 distinct `(session_id,capture_id,candidate_id)` keys**. Every plane reports support from three source poses despite four distinct fitted source positions. This is not two candidates competing inside one fit: the identifiers refer to different source poses but cannot be uniquely dereferenced by the result consumer.

**Action:** require unique source-session identities before fitting/recording processing, or define and emit a source-snapshot/revision identifier that makes every evidence key unambiguous. Merely continuing to use an internal index does not fix the output contract. Evidence: `work/review-198d365-input-probes.json`.

## P2: raw-bundle admission bypasses diagnostic and resource boundaries

**Location:** `echosight/multisource.py:338–345`; corresponding numerical top-level access at `230`.

Top-level file reading/JSON parsing and `_empty(bundle, ...)` run before the error handler or cancellation check. `process_scene_bundle(None)` and `process_scene_bundle([])` raise `AttributeError`; a malformed JSON file raises `JSONDecodeError` instead of returning the core's no-result diagnostic. Missing-file errors likewise occur outside the guarded block. The raw bundle is read without a size bound even though individual session metadata is bounded. A 1,200,002-byte top-level bundle is fully read and only then rejected for source count. The example is deliberately small; no large allocation or denial-of-service stress was attempted.

This is a trusted-local experimental core, **not** an exposed HTTP endpoint vulnerability. It is nevertheless a missing bounded-input/error contract for the new reusable recording entry point, and pre-cancelled calls still reach top-level file parsing first.

**Action:** check cancellation and top-level type/schema early; load a bounded bundle byte snapshot inside the diagnostic boundary; validate the session array before processing. Return consistent explicit rejection/no-result diagnostics for bad type, unreadable file, invalid JSON and metadata-size excess. The source/capture count bounds do not bound file parsing itself. Reproduction and results are in the input-probe artifacts above.

## Independent mathematical and recording checks

### Full shared nuisance covariance, including the reference source

`work/review-198d365-covariance-probe.py` constructs two physical planes, four noncoplanar source poses, six reused receivers, correlated full source/speed covariance, independent candidate noise, within-recording shared direct timing and relative clock uncertainty. Independently finite-differenced physical delay derivatives and built the covariance as separate nuisance design matrices, then propagated through the executed ordinary-least-squares influence matrix. Effective speed is deliberately 346 m/source-buffer second.

The code's full plane-parameter covariance and independently calculated result differ by at most **2.34534e-13 m²**. This checks cross-surface, cross-source and reused-receiver terms, not only diagonals or monotonicity under inflated uncertainty. Source-speed covariance is retained; no second copy of independent source/sound/clock priors was added in this model.

Separately perturbed all 13 source/speed nuisance coordinates, refit to fixed observations while moving the reference source with its source-0 perturbation, and compared the resulting physical plane normals/offsets with the analytic propagation. Maximum derivative discrepancy is **9.10667e-7**, and source-0-only discrepancy **5.73355e-7**, within declared tolerances. The reference-source parameterization is not a demonstrated covariance omission: moving that reference changes both the fitted image parameter and its conversion back to a physical plane, whose parameterization contributions cancel. `shared_plane_parameter_covariance_m2` should be understood in its nominal-reference parameterization, not as an independently surveyed physical image-source covariance.

These checks establish local derivatives and propagation under the chosen fixed associations/model. They do not establish coverage after selection, higher-order identification or nonlinear model mismatch. Results are saved in `work/review-198d365-covariance-probe.json`.

### Actual recording entry and clock units

`work/review-198d365-raw-probes.py` independently renders 32 PCM recordings for four sources and eight receiver positions, two reflecting planes, physical speed **343 m/s**, source-clock scale **1.003**, and differing receiver clock scales near **1.004**. It uses `alpha=kappa_receiver/kappa_source` and source-buffer propagation delay `kappa_source * path_length / c`; the bundle supplies `v=c/kappa_source=341.9740777667`.

`process_scene_bundle` accepts all 32 recordings, returns two planes, and recovers the two offsets with errors **0.000135619 m** and **0.000040182 m** in this idealized signal fixture. The renderer uses the existing probe generator but independently constructs physical delays and clock sampling. This is a narrow units/integration check, not a new frozen accuracy benchmark or hardware result.

Immediate cancellation and cancellation during real signal processing return `cancelled`. Replacing the first recording with invalid WAV bytes returns `no_result` and `invalid PCM WAV`, with no surfaces. An over-limit source array rejects. These successful lower-level guards do not repair the top-level parsing issue above. Results: `work/review-198d365-raw-probes.json`.

## Scope, tests and remaining limits

Read the original charter, source-relocation contract/acceptance/freeze inputs, new `multisource.py`, source-relocation renderer/evaluator/baseline, relevant inference helpers and model comparison rule, test sources, and relevant audit documentation. Main API/CLI remains a separate single-source integration; this review does not imply multisource HTTP/CLI readiness. The raw numerical and physical-path checks above did not use held-out seeds or alter evaluation criteria.

Executed `tests.test_multisource` (8 tests) and `evaluation.test_source_relocation` (2 tests): **10 passed**. The tests cover room/height/exclusive initial evidence, hidden/tangential aliases, shared calibration sensitivity, cancellation, survey identity, exact corner alternatives and a genuine extra plane; the reviewer probes extend these in the specific ways reported.

Known limitations remain explicit: greedy bounded initialization/association, a conditional first-order model, finite parent-subset search, no universal reflection-order uniqueness, no measured source-relocation evidence, missing-parent aliases, and conservative abstention for lower-rank source motion. Two-source acceptance and reported development failures remain failures; this review neither changes their gates nor substitutes mathematical unit checks for complete evaluation. No broad backend rerun, external measured-data rerun, hardware validation or final completion assessment was performed.
