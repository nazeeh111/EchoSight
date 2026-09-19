# Independent assembled review at f5bf0fa

Reviewed exact commit `f5bf0fa412db9479779a7e944e14ea8c4ea983b7` against `0f05dd1`, including support-identity checkpoint `3745665`. Runtime was extracted with `git archive` into `work/review-f5bf0fa/source`; no runtime source was edited. This reviews the assembled changes, not a claim that the complete EchoSight scientific objective has been achieved.

## Findings

### P2: Cancelled controlled results retain derived change claims and the CLI writes them

`echosight/controlled.py:276` and `:289` only change `status` on cancellation. They retain previously appended receiver comparisons and, at the late check, populated `conditional_spatial_changes`. `echosight/cli.py:145` saves that object before returning cancellation exit code 130.

Independent reproduction processes the existing development moved-reflector scenario through 48 actual generated WAVs (four epochs, twelve receivers), yielding four successful one-plane epoch results. With exact cached epoch results and deterministic cancellation after the genuine spatial comparison, the core returns `cancelled` with **one conditional spatial-change claim and twelve receiver-evidence objects**. Raising real SIGINT at that boundary through CLI yields exit130 and writes the same claim-bearing JSON. Cancellation after the first receiver comparison leaves one receiver entry with `repeatable_change=true`. No delay labels or supplied scene geometry entered processing. Caching only avoids processing identical WAVs again for each boundary injection.

The output also validates against `controlled-result.schema.json`; schema validation alone does not catch this. Consumers following status correctly can avoid the claims, and the job store prevents publication, so this is not an HTTP publication bypass. It materially weakens the reusable core/CLI cancellation boundary and invites downstream rendering of an unfinished comparison.

Fix: use one cancelled-result sanitizer at every controlled cancellation return and relevant terminal exits, clearing derived receiver comparisons and spatial changes while retaining raw evidence/provenance and clearly completed epoch records. Add core and CLI late/mid-cancellation regression checks. Consider making the schema require empty comparison fields for `status=cancelled`.

This issue **predates f5bf0fa**. The reviewed controlled diff changes source consistency only; cancellation return bodies were already present. It is an assembled-boundary finding, not a regression attributed to the source admission fix.

### P2: The public pipeline's terminal callback can cancel yet return success with geometry

`echosight/pipeline.py:166` calls the final user progress callback after inference's final cancellation check, then returns without rechecking. An independent probe sets the cancellation predicate when the public callback reports fraction1/message `ok`. `process_session` returns `status=ok` with one surface even though cancellation is already requested before it returns.

This differs from inference's final callback, which is correctly followed by a cancellation check. It affects direct reusable-core callers; the CLI passes no progress callback, and HTTP publication rechecks its event independently. A timing-equivalent external event can also arrive during final metadata assembly. Add a final check after the outer callback and apply the same geometry-clearing semantics used by inference. No need to discard preserved recording evidence. This outer boundary likewise predates the reviewed patch.

## Fresh executed evidence

- `work/review-f5bf0fa/probe.py`, `probe-results.json`, `cli-cancelled.json`: independent recording-based cancellation reproductions above. Four raw epochs were actually processed; cancellation injection uses their exact outputs. The output artifact retains the defect for verification.
- `work/review-f5bf0fa/schema-probe.py`, `schema-probe-results.json`: independent schema/legacy comparison checks. v1.1 cross-session reuse of four capture labels counts four newly scoped supports; missing session scope produces null rather than zero counts. A stripped legacy v1.0 comparison validates and carries tracks into v1.1. Legacy cancelled geometry yields incomparable status and no current tracks. Cancelled controlled claims still pass their schema.
- `focused-tests.txt`: **27 passed**, covering clock trigger/raw fixtures, source contradictions and matching/missing declarations, lossless replay/hash retention, reference-calibration source admission, experimental raw/prepared per-session consistency, and display-comparison cases.
- `cancellation-tests.txt`: **4 passed**, checking all three single-source wrappers, mapper/grid cancellation during ambiguity checks, ordinary processing CLI SIGINT, and experimental multi-source late cancellation.
- `publication-tests.txt`: **2 passed and one environment error**. Controlled cancellation/failed publication and store cancellation/recovery passed. The HTTP test initially could not bind a loopback port in the sandbox; this was not an application failure. The single test was rerun through native escalation and **passed**, logged in `http-publication-test.txt`.

These are **34 unique passing existing targeted checks**, plus the independent probes that deliberately reproduce the two findings. This is not a rerun of the full196-test suite. No classifier study, held-out benchmark, external-data fitting or hardware experiment was repeated.

## Source, physics and boundary assessment

The clock diff contains exactly the one proposed trigger plus comments: retain the failed-affine-fit condition and additionally retry when `abs(alpha_est-1)*pulse_duration_s > 0.5/(high_hz-low_hz)`, still inside the existing5000ppm bound. It supplies the observed estimated rate, not generating truth. One existing refinement chooses the nearest pilot within±1ms and is accepted only for a smaller maximum affine residual. The100µs/5000ppm rejection gates, raw resampling, direct anchoring, candidate extraction and limits are unchanged. Targeted raw direct-null and room checks pass, including below-trigger behavior and cancellation/resource limits. That confirms this bounded repair, not global correct direct identification, calibrated timing coverage or separation of physical sound speed from source clock.

The shared source-consistency helper distinguishes known contradiction from absent/unknown declaration. Ordinary recording processing blocks known within-session contradictions before either mapper and retains decoded evidence and recording hashes, including rejected acquisitions. Reference calibration explicitly blocks contradiction while allowing otherwise usable isolated-reference recordings whose room mapper produced no result. Controlled protocols additionally compare recorder/input-route declarations and native source configuration against the protocol across epochs. Experimental raw processing preserves evidence, and the prepared entry rechecks declarations within each session; differently calibrated source sessions may legitimately have different configurations. Prepared observations remain unauthenticated inputs and do not prove actual recordings or source identity.

The source consistency statements compare operator declarations, not acoustic-center equivalence or speaker routing. Missing declarations remain conditional, not proof of stable hardware. The raw/native tests preserve original byte fingerprints through export/replay. No newly introduced bypass was found in these scoped checks.

Single-source mapper, direct-plane-grid and first-echo wrappers now forward cancellation; final inference cancellation clears surfaces, hypotheses, dimensions, guidance and derived covariance/score. Experimental inference similarly clears derived geometry. Store cancellation prevents completed-result publication and recovery preserves earlier state, as verified above. The two findings identify the remaining direct core/CLI gaps rather than weakening those passed boundaries.

## Limits and disposition

Request fixes and affected rechecks for both findings before calling cancellation behavior consistently verified. No additional blocking source/clock/comparison defect was reproduced in this bounded review. This is not proof of all concurrent cancellation schedules, all malformed inputs, numeric optimum, calibrated covariance or physical validity. Existing measured-data failures, source ambiguities, missed structure and own-device uncertainty are unchanged. The corrected clock trigger is not an ordinary-device accuracy demonstration.

Reproduce from repository root with the project-local interpreter:

```sh
.venv/bin/python work/review-f5bf0fa/probe.py
.venv/bin/python work/review-f5bf0fa/schema-probe.py
```

The raw probe writes only its work directory. Relevant immutable source and reviewer-helper hashes are in `work/review-f5bf0fa/source-hashes.json`. The coordinator has assigned repairs to a separate writer; this review did not edit the runtime.
