# EchoSight active implementation state

**Status: baseline research prototype; charter objective unmet and native goal active.** User explicitly rejected the near-completion framing and requested full requirement audit plus continued specialist implementation. [Original charter](docs/CHARTER.md), [continued-work instruction](docs/CHARTER_ADDENDUM.md), [coverage matrix](docs/audit/COVERAGE.md).

Authority: private repo branches/ordinary commits/push/default-branch integration and missing write invitations authorized. No deployment, public publication, paid services, global configuration or credential changes. One existing EchoSight vault index note authorized. Current model/effort unchanged.

Checkout: this directory, branch `backend/implementation`, GitHub's current default. Last pushed/verified code: `1c773367f787a551aec0f15fc244b5fe9290dee3`. Collaborator `Oltans_UI/UX` branch untouched. Prior access check: nazeeh111 owner/admin, sinha-ritwik accepted write, littleapple08 pending write invitation333732214; no duplicates sent.

Verified baseline: 69 tests in a clean GitHub clone; original/extended frozen suites and external-response replay reproduced; independent assembled review at565769a plus bounded review at1c77336. [Reproduction](evidence/final-reproduction.json), [review](evidence/independent-review-565769a.md), [baseline history](evidence/BASELINE_STATE_HISTORY.md). “Final” in historical filenames refers to the earlier verification pass, **not charter completion**.

Physics conventions: n·x=d; reflected source q=s+2(d−n·s)n; excess source-buffer delay=(|r−q|−|r−s|)/(c/kappa). Never halve a bistatic delay. Surveyed acoustic-center poses are supplied. Source physical rate is not established by relative clock correction. Support meshes are not physical edges/enclosure/empty space. Local covariance is conditional on model/path identity. Ground truth stays outside fitting.

Separate evidence: synthetic twelve-view cases6/6 room planes and designated tilted case7/7, zero false in those narrow suites; eight-view misses remain. External data are measured RIRs convolved with probes,20/25accepted5rejected; no measured spatial accuracy. No own-device recordings. Unresolved coherent multipath, source/direct-reference assumptions and wrong-model reliability materially limit the demonstration.

Active specialists and exclusive ownership: physics_audit(signals/simulation/test_signals), inference(inference/geometry/test_inference), backend(storage/API and their tests), evaluation(evaluation modules/new frozen families/measured-data search). Coordinator owns pipeline/evolution/CLI/architecture/matrix/state/commits. Independent reviewer idle until a new assembled milestone; no implementation ownership. No daemon/automation is running.

Prioritized work:
1. Reproduce higher-order phantom planes and wrong-model confidence; implement justified competing interpretations/guards.
2. Stress signal extraction with source distortion, overlapping paths and clock/discontinuity effects.
3. Fix immutable raw decode/hash/store snapshot; verify cancellation publication; implement safe calibration revisions.
4. Find external measured geometry and independently freeze harder simulation families without editing old acceptance.
5. Add controlled repeat-acquisition scene comparison and exact hardware qualification thresholds.
6. Integrate/review/reproduce and push coherent verified checkpoints continuously.

Next coordinator action: finish coverage matrix against specialist evidence; adopt immutable read snapshot into pipeline after backend interface lands; develop controlled-comparison contract after physical priorities are grounded. Preserve runnable baseline and all failure reports. Do not report completion while these tractable gaps remain.
