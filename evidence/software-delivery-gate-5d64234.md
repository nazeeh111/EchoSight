# Final software-gate reconciliation

Audited commit: `5d6423486be5fd448a4d7b42fbbaee264eb07c9c`. Read-only reconciliation of the governing charter/addendum, current 43-row matrix, public API/CLI entrypoints, schemas and repaired multi-source evidence. No repeated full suite, broad link audit, data generation or production change.

## Result

No additional known material software defect or missing mandatory public command/schema was established within this bounded audit. Exact-commit independent review and clean-GitHub setup/tests/demo remain required delivery gates; the coordinator already has those in progress. Their absence from the committed snapshot is a pending verification result, not a new implementation task.

The charter objective remains unmet because important spatial requirements still fail. This conclusion must not be converted into software completion implying scientific qualification.

## Main mapping route: wording, implementation, boundary

| Governing requirement | Observed implementation | Assessment |
|---|---|---|
| CHARTER.md:43,45: reusable core, local HTTP API and CLI demonstration; own recording-to-spatial route | `echosight.pipeline.process_session` is the public single-source pipeline; `echosight/api.py:41` selects it for jobs; CLI `process`, `demo` and `serve` enter it. Raw import, calibration revisions, jobs and exports are already reviewed. | The required public route exists. It infers multiple 3D surfaces from raw audio in the declared restricted simulation; it is not merely an echo-label solver. No missing public command identified. |
| CHARTER.md:98: API/CLI must recover multiple independent surfaces including height on suitable nondegenerate scenes; declare model/data restrictions | README's twelve-view command enters the same public pipeline and recovers six simulated room planes including floor/ceiling. Explicit restrictions and failures are published. | Bounded software/demo requirement is met by this route; harder/measured failure is not erased by that fact. A clean-checkout verification at the final commit remains required. |
| CHARTER.md:47: frontend versioned contracts, IDs, units, progress/cancellation, errors, renderable geometry | Existing session/job/result/calibration/comparison schemas and FRONTEND_HANDOFF describe the public route, including covariance limits and evidence links. | No additional mandatory public schema gap identified. No multi-source bundle schema is bundled, and no public job/upload/export contract promises multi-source processing. |
| CHARTER.md:37,39 and ADDENDUM.md:23: implement supported improvements and close known tractable material defects | Support pruning is now in `echosight.multisource`; raw 1129 recovery is repaired, cancellation is tested, all 12 relocation and 15 broader mismatch counts preserved except the six recovered planes. | The numerical improvement is implemented in the actual reusable raw-input engine. It is not only a figure/report. The engine remains an explicitly experimental programmatic route. |

## Multi-source integration judgment

`echosight.multisource.process_scene_bundle(bundle_path)` accepts actual recording bundles and returns geometry. `infer_scene_bundle` consumes derived observations. Neither is wired into the public API job store or a dedicated public CLI command. `evaluation/source_relocation_contract.md` describes the experimental input; there is no stable multi-source public JSON Schema/API lifecycle. The repaired higher-order 1129 gain therefore cannot be advertised as a new capability of the existing public API/CLI.

The charter does **not** literally require every research engine to become a public route, nor does it require physical qualification before building software. In fact it requires integrated software before own-device experiments. Therefore scientific uncertainty alone is not a general reason to refuse useful integration. However, no separate mandatory source-relocation interface is specified, and the existing public route already satisfies the bounded recording-to-3D software demonstration. Promoting the experimental engine now would be an additional interface decision, not a correction of a missing promised endpoint.

If the final demonstration instead names the repaired four-source route as its primary public backend capability, then its API/CLI, durable bundle lifecycle and frontend contract become an actual delivery gap. Either implement that deliberately scoped interface with explicit experimental semantics, or keep the final handoff precise: public fixed-source recording-to-3D mapping plus experimental multi-source Python processing and its reproducible fixture regression. Do not imply that existing `process`, HTTP jobs, tracking or exports automatically support bundles.

No software-only inference can make the two-source rank restriction, physical source mismatch, or external chance-association failures disappear. Those are not missing HTTP plumbing.

## Exact executable delivery and remaining experiment gates

The public setup/test/demo commands already exist in README. The repaired engine has an executable clean-checkout regression command in `evidence/multisource-support-recovery/README.md`: `.venv/bin/python -m unittest tests.test_multisource_support_recovery -v`. This exercises retained recording-derived observations, including recovery and mid-refit cancellation; it is correctly not called raw reproduction. The original raw experiment scripts require retained local inputs and their documented runtime snapshot. That scope limit is disclosed, not a missing runtime command.

Only active final software gates need completion now: independent review of final integrated code, the assigned clean GitHub/full-suite/demo reproduction, then verified remote commit and state/evidence references. Do not repeat these in another lane.

Scientific gates remain separately open: two-source 1103 recovery, harder fixed-source mismatch, two-emitter false planes and measured-room reconstruction. The current joint-reference trial has not shown room-mapping benefit. Its next coherent transfer test requires source/route/speed continuity plus mapping audio and survey errors independent of calibration inputs (or a supported full cross-covariance model). Existing isolated reference WAVs cannot demonstrate a room; unrelated retained room sources cannot legally receive that calibration merely by relabeling metadata. The two-instance transfer proposal is retained but unexecuted. None of those experimental gates authorizes thresholds to change or requires speculative software scaffolding.

A few matrix/state statements still describe older checkpoints or older higher-order misses. Update active summaries after the final verification receipts, retaining the explicitly historical reports. This is delivery bookkeeping, not a newly discovered runtime defect.
