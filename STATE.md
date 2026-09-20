# EchoSight authoritative state

## Current delivery

**Version 0.2.0 is delivered and verified.** Runtime/tests/schemas/evaluation checkpoint: **ab5ea75de446b653fec058103030759fc7fbcdfa**, confirmed on GitHub. A [separate clean GitHub checkout](evidence/reproduction-ab5ea75/) passes **244 tests in 70.255 seconds**, both recording demos, CLI profile creation, context-bound identity, raw export/replay and offline schemas. [Fresh independent review at that exact commit](evidence/material-appearance/FINAL-ab5ea75-REVIEW.md) closes both material-output contract findings. Later delivery commits update documentation, examples and receipts only; the verified code remains the checkpoint above. Full scientific acceptance remains unmet.

The latest user instruction activates material and color implementation, superseding their earlier deferral. Product-level adjudication remains deferred. Scope is governed by the [charter](docs/CHARTER.md) and [addendum](docs/CHARTER_ADDENDUM.md); the [coverage matrix](docs/audit/COVERAGE.md) retains scientific requirements and their evidence. The broader goal awaits authorization for the frozen calibration-to-room experiment: it needs56new controlled synthetic recordings, excluded by the current no-new-datasets instruction. The authorization question is pending; no independent implementation or review assignment remains. The previous goal's pause and stopped workers were verified before this continuation.

Repository: private [nazeeh111/EchoSight](https://github.com/nazeeh111/EchoSight), default branch `backend/implementation`. Ordinary project commits, pushes and integration are authorized. Preserve owner/collaborator access, teammate branch `Oltans_UI/UX` and all unrelated work. No force push, paid service, global installation, public deployment or credential change. One existing EchoSight vault note is an authorized index; repository files are authoritative. Use the requested Astra/High settings.

## Implemented scope

- Lossless recording import, quality/admission checks, clock/source calibration diagnostics, fixed-source 3D inference, support meshes/rays, conditional uncertainty, dimensions and explicit partial/ambiguous/no-result states.
- Local HTTP API and CLI, revisioned calibration/context, immutable raw inputs and jobs, progress/cancellation/recovery, raw export/reload/recomputation and frontend schemas/examples. Experimental multi-source inference remains a separate Python route.
- Version 0.2.0: recording-derived four-band apparent reflection features; labeled reference-profile builder; conditional material comparisons with full predictive covariance; supplied contextual color mixtures. Missing/overlapping/out-of-domain/reused evidence stays unknown. Geometry is unchanged by interpretation inputs. Profiles, provenance and palettes travel through API/CLI, revisions, identity and replay. There is no factory material library or acoustic measurement of optical color.
- [Native iOS recorder](acquisition/ios/README.md) exports delivered Float32 and route/buffer/interruption evidence. Its unsigned build and injected checks are software evidence. No device launch, microphone qualification or process-death recovery before durable save is claimed.

[Install/use](docs/USAGE.md), [API](docs/API.md), [frontend handoff](docs/FRONTEND_HANDOFF.md), [materials/colors](docs/MATERIALS_APPEARANCE.md).

## Verification and handoff

[Material evidence](evidence/material-appearance/) preserves the initial findings and fixes. The reviewer independently checked non-diagonal likelihoods, unbiased covariance, raw inverse-distance gains, palette arithmetic, negative admission paths, current-job snapshots, cancellation and replay. Cancelled scenes cannot publish interpretation, and rounded color mixtures stay within schema bounds without filling genuinely missing palette mass. No known actionable software finding remains from this review.

[Clean reproduction](evidence/reproduction-ab5ea75/) fetched the exact remote commit into a separate checkout and used the previously installed pinned Python 3.12.14/NumPy 2.3.5/SciPy 1.18.1 environment. It ran the full suite once. The raw room demo returns six surfaces. The controlled material demo returns three correct synthetic-filter estimates and three material unknowns across six surfaces; null, reused-training and out-of-domain controls pass. Both ordinary and context-bearing replay preserve all12 raw hashes, geometry, result identity and interpretation exactly. The CLI-built profile equals the demo profile. The tree stayed clean. This is software/simulation evidence, not a blind material benchmark or physical qualification.

README, [install/use](docs/USAGE.md), API and frontend guides cover the final routes. The [actual material frontend example](examples/frontend/material-room.json) comes from the clean checkout; only dense response arrays are omitted, with omissions listed. It passes the offline schema. No dependency or external dataset was added. No outstanding implementation assignment, review finding or test server remains. The coordinator owns the final evidence-only checkpoint and remote hash confirmation.

Independent unblocked software work is complete within the selected public backend scope. Next experiments are the frozen calibration-to-room transfer and later physical H0–H6 gates below, plus the [planned material qualification](docs/MATERIALS_APPEARANCE.md#planned-physical-qualification-two-known-samples). That material experiment defines74 recordings, reference/query separation, unknown controls, geometry/coverage/drift/time limits and failure consequences before measurements; it has not been executed. Keep all scientific failures visible and closed approaches closed without new evidence.
## Scientific evidence and limits

Software completion does not establish physical accuracy. Every comparison below retains its original criteria, code version and raw-input provenance.

| Evidence | Observed result and boundary |
| --- | --- |
| Original synthetic room cases | Twelve-view scenes recover height-dependent room structure; eight-view cases have misses. [Evaluation](docs/EVALUATION.md) |
| Frozen fixed-source path comparison | Updated mapper: 38 true, 4 false, 0 missed; 10/12 cases pass. Both two-emitter cases retain two false wall copies. [Report](evidence/path-interpretation-evaluation/REPORT.md) |
| Harder 13-case synthetic stress | 30 true, 48 missed, 0 false. Conservative abstention does not fulfill recovery. [Prior reproduction](evidence/reproduction-659/) |
| Experimental source relocation | Support-pruning repair improves existing raw case1129 from 0 to 6 true/0 false, including height; all12 cases improve34→40 matches with0false, other11counts unchanged. Two-source1103 still fails. Independent15case replay preserves geometry and failures. [Repair/review](evidence/multisource-support-recovery/), [exact review](evidence/multisource-support-review/INTEGRATED-5d64234-REVIEW.md) |
| External measured FLAIR responses | Main0definitive/10miss; grid2matches/8unmatched. Hybrid replay is not our hardware measurement. [Coverage](docs/audit/COVERAGE.md) |
| External dEchorate multi-source | 40RIRs: 1roommatch+2unmatched; wrong-pose control4unmatched. Diagnostic echo-refined poses are not independent calibration. [Study](docs/audit/MEASURED_MULTISOURCE.md) |
| Calibration provenance/schema | Interrupted repair closed at38ce3ff: exact supplied inputs/hash availability, stable identity, v1.1 proposal/rejection schema and five replay examples. [Contract](docs/CALIBRATION.md), [independent review](evidence/independent-review-38ce3ff.md) |
| Two-reference calibration | Both existing single-source controls pass frozen reference gates; all4dual pairs reject. Full correlated covariance retained. No room transfer success. [Trial](evidence/joint-reference-trial/), [independent review](evidence/independent-review-joint-reference.md) |
| Materials and appearance | Controlled synthetic profiles and supplied palettes only; no measured building-material accuracy, calibrated probabilities or optical sensing. Three of six demo surfaces remain material unknowns. |
| Our devices | No physical validation. [H0–H6 acceptance experiments](docs/HARDWARE_ACCEPTANCE.md) remain later work. |

The frozen [calibration-to-room transfer plan](evidence/calibration-room-transfer-plan/) remains unexecuted: two source-matched room realizations, two null controls, independent mapping surveys/audio; six planes including height and0unmatched at5°/0.10m, withheld100µsRMS/200µsmax and10s processing. Existing isolated references cannot establish this transfer. Its static review does not authorize a new dataset or imply execution.

Closed approaches stay closed without new evidence: larger peak budgets, joint waveform extractor/null guard, seven-repeat bootstrap confidence, and source-warning suppression. They failed retained recovery/null/coverage criteria; see [candidate budgets](docs/audit/CANDIDATE_BUDGET.md), [estimators](docs/audit/ESTIMATORS.md), [timing covariance](docs/audit/TIMING_COVARIANCE.md) and [source models](docs/audit/SOURCE_MODELS.md). Do not repeat completed reviews or retune exposed cases.

## Load-bearing conventions

Metres, right-handed coordinates, z up; supplied surveyed acoustic centers are calibration, not inferred geometry. A plane satisfies n·x=d; its image source is q=s+2(d−n·s)n. Excess source-buffer delay is (|r−q|−|r−s|)/(c/kappa), never half a bistatic delay. Receiver/source clocks do not establish absolute physical source rate. Shared source/effective-speed and survey covariance must retain cross terms.

Support patches do not establish physical edges, enclosure, empty space or safety. Conditional covariance excludes wrong physics, selection and systematic transducer bias. Generating truth never enters fitting. Exact waveform copies cannot supply independent evidence; different hashes alone do not establish physical independence. Material weights are conditional on profiles and usable views; rejected-view coverage is separate. Appearance is supplied context, not optical measurement. Full scientific charter acceptance remains unmet while the recorded spatial failures remain.
