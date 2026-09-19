# EchoSight active implementation state

**Baseline research prototype. Charter objective unmet; native goal active.** Scope: [charter](docs/CHARTER.md), [continued-work instruction](docs/CHARTER_ADDENDUM.md), [coverage matrix](docs/audit/COVERAGE.md). Preserve selected Astra model/effort. No software evidence establishes our iPhone accuracy.

Authority: private project branches, ordinary commits/push/default-branch integration and missing collaborator invitations authorized. No paid services, public deployment, ownership changes or global installs. One existing EchoSight vault index authorized. Checkout is this directory; branch/default `backend/implementation`. Last verified remote commit **eb1c26730f7f6ee2224c0ee17acb772ba250d505**. Teammate `Oltans_UI/UX` untouched. GitHub access: nazeeh111 owner/admin, sinha-ritwik accepted write, littleapple08 pending write invitation333732214; no duplicate invitations.

## Load-bearing conventions

Plane n·x=d; reflected source q=s+2(d−n·s)n; excess source-buffer delay=(|r−q|−|r−s|)/(c/kappa). Never halve bistatic delays. Surveyed acoustic centers are supplied. Relative source/receiver clocks do not identify physical source clock. Optional joint source/effective-speed covariance replaces separate source/speed/rate budgets. Support meshes are not physical edges, enclosure or empty space. Local covariance is conditional on model and path identity. Truth stays outside fitting.

## Executed evidence and current limits

- Software:659099f reproduced95tests in clean GitHub clone; raw recording core/API/CLI, bounded import, immutable provenance, revisions, cancellation/recovery/export, empirical reference-calibration proposal and higher-order alternatives. [Reproduction](evidence/reproduction-659/checks.json).
- Synthetic: original8/12-view regressions pass. New13-case stress acceptance **fails**: conservative higher-order abstention removes false planes but also necessary recovery; overlapping/finite-panel structure still missed. [Stress](evidence/reproduction-659/stress.json).
- External measured: FLAIR24 measuredRIR hybrid replay with independent laser reference **fails** spatial acceptance. Main mapper ambiguous/no definitive planes. Matched grid baseline2, unmatched8. This is not own-device acquisition. [FLAIR](evidence/reproduction-659/flair.json). dEchorate affine retry accepts21/25 but retains one suspect direct path; source/direct-model discrepancy unresolved.
- Own devices: none measured. No hardware accuracy established.
- Scientific: higher-order/source aliasing, chance associations, finite reflectors/diffraction, waveform model bias and wrong-model uncertainty remain material.

[Independent review659](evidence/independent-review-659099f.md) verified prior persistence repairs and found3P2 issues. Current review-fix checkpoint includes missing calibration direct/rate variance, duplicated held-out pose/raw rejection and composed higher-order/mirror/rank diagnostics. Coordinator also repaired origin-dependent comparison and effective-speed mismatch handling. Targeted evidence linked in matrix after execution. Prior state history: [audit](evidence/AUDIT_STATE_HISTORY.md), [baseline](evidence/BASELINE_STATE_HISTORY.md).

## Active work and ownership

- Coordinator: acquisition backend integration, API/replay/schema checks, state and frequent verified commits. Native package decoding already passes38focused tests; injected Swift exports interoperate. Uncommitted work is not an accepted checkpoint.
- inference: minimal native iOS collector/exporter under acquisition/ios; unsigned generic build and injected-buffer tests, no microphone/signing/install/launch.
- physics_audit: independent acquisition timing/format/continuity review. Waveform plus null-guard branch closed without promotion because it loses necessary surfaces; evidence archived next.
- evaluation: isolated same-path compact-point versus plane alternative and shared-uncertainty controls; no production edits or new held-out tuning.
- independent_review: immutable be5c70a follow-up on three198P2 fixes. No other writer or daemon/automation.

## Prioritized next actions

1. Finish exact native-export to backend API/CLI/replay bridge, malformed/resource checks, schemas and independent review; commit/push coherent verified acquisition checkpoint.
2. Resolve physical missing-parent and point-scatterer competing models using equal selected observations, preserving all failures and existing frozen criteria.
3. Recheck affected source-relocation regressions only after justified model changes; no physical or general object-reconstruction claims.
4. Keep measured FLAIR and stress failures explicit; do not promote filters that trade away required recovery merely to reduce false surfaces.
5. Update full charter matrix, clean reproduction and frontend handoff at coherent milestones; all own-device qualification remains pending.

Do not declare completion or request device experiments while independent software work remains. Save consequential findings before compaction; inspect active workers and authoritative files after recovery. No claim execution survives runtime termination.


## Controlled integration checkpoint

Independent [0eb9fdd follow-up](evidence/independent-review-0eb9fdd.md) resolves all3review findings;35focused tests and independent probes pass. Controlled recording comparison now has raw API/CLI routes, stored revision snapshots, source/route declarations, separate job results, cancellation, crash recovery, no-trust replay semantics, schemas and examples. Candidate/reference/clock and shared differential timing budgets are retained; duplicate raw recordings cannot count as independent repeats. Dense nested response arrays are explicitly omitted for bounded output and can be reprocessed from original recordings. Four-fixed-phone demonstration remains unlocalized;12static receiver development can localize one moved reflector. Hardware criteria prepared in docs/HARDWARE_ACCEPTANCE.md; no hardware requested.

Scientific branch status: physical parent-subset alternatives remove8false moved-source planes across2development higher-order cases while preserving genuine panel7/7; missing-parent falseplane remains. No new held-out run yet. Simple density-aware clutter alternative rejected: new analytic development controls baseline38/100false in uniform/clustered null vsalternative36/100; roomclutter60true+4false vs60+3. Null-calibration specialist is testing search-aware held-view permutation, not editing baseline. Full-waveform covariance study rejects naiveHessian;7repeat bootstrap still undercovers and is not promoted as95%uncertainty. Evidence remains experimental, not physical validation.

Source-relocation experimental checkpoint:10 focused mapper/fixture checks pass. Rules and equal-input development reports preserved in evidence/audit-multisource/. Next: first frozen12case raw held-out evaluation at the immutable commit containing this state. Acceptance hash remains626166532905ca48a53639f6521df93aecc6f2bcf8dd77618bd20b8272fd35f7. No API promotion or physical claim.


## Immutable198d365 evaluation

Clean GitHub checkout passes120tests ([log](evidence/reproduction-198/tests.txt)). First frozen source-relocation raw held-out evaluation **fails** ([fullreport](evidence/reproduction-198/relocation-heldout.json)); exactcode stayedunchanged. Preserve all cases and criteria. Four-source room/panel recovery succeeds, but missing-parent cases producefalseplanes and2sourcegatewithholdsrequiredgeometry. Multi-source remains experimental. [Independent controlled review3c37ed7](evidence/independent-review-3c37ed7.md):16focusedtests plus independent falsechange, covariance, snapshot, export/reload andpublicationcrash probes; no P1/P2established. Multisource review198running separately.

New bounded acquisition investigation: existingphyphoxroute remainsprovisional; WebAudio deliversfloat32 that integerconversioncannotpreserveexactly. NativeiOSmeasurement-mode harness feasibility is being compared withoutmicrophoneuse/signing/deployment; no actualphoneclaim. Potentialbackendwork: exactFloat32PCM plus hash-bound deliveryclock/interruption/route manifest. Specialistassignmentstillproposalstage. Nullalternative nowreducesrandomclutter butretainsonefreshnullsurvivor andcoherentmultipath; no firstordercertification.


## Reviewed experimental repairs, next checkpoint

Independent198d365 review found3P2s: reused physical paths in alternatives, duplicate source-session identities and unguarded raw-bundle admission. Repairs enforce exclusive matching over coincident-arrival groups, reject duplicate identities and bound/type-check raw JSON.14focusedchecks pass in isolated198snapshot with only these repairs overlaid; higher-order development still6/6bothseeds andpanel7/7. Raw held-out198failure remains unchanged evidence, not silently overwritten. Fresh repaired-commit review next.

Working-tree ownership: coordinator has uncommitted acquisition.py/storage/pipeline Float32+hash-bound native manifest support (38focusedchecks), contract/tests; inference owns acquisition/ios/ minimal recorder and is no longerediting multisource afterfreeze. Evaluation owns isolated unobserved-parent/point-alternative investigations; physics owns isolated closed-or-closing waveform/null comparisons; independentreview awaits identifiedfixcommit. Native mic/signing/deployment not authorized by this implementation phase and not performed. No daemon/automation.

## Acquisition integration in progress

Native Float32 package import, raw API processing to six simulated surfaces, exact export/reload and interrupted-byte preservation pass targeted software checks. Independent acquisition review reproduced host/sample clock inconsistency; backend/native owners fixed it with a broad documented gate, reviewer rechecked9clockcases and19,928Float32patterns. No hardware used. Native recorder adds pending-save retry after alive-process disk failure; review of that new state remains pending. Formal offline schema checks now exercise published examples and real outputs; corrected controlled cross-schema references to canonical versioned IDs. New test-only dependencies are pinned in requirements-test.txt. Experimental point/missing-parent alternatives remain separate uncommitted work; new raw12case evaluation specification frozen before generation. Renderer specialist awaits identified integrated commit before evaluating.

Acquisition checkpoint gate: isolated eb1c267+acquisition overlay passes136tests in32.513s, including actual raw native-packageHTTP→six simulated surfaces and formal offline schemas. Native owner frozen; unsignedbuild/Swift bridge/save-retry checks pass. Sources and evidence: evidence/acquisition-integration/. Nextcommit excludes path-alternative experimental edits; immutable review/cleanGitHubreproduction next. No own-device claim.
