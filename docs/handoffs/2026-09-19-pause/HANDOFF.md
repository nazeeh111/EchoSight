# EchoSight shutdown and exact continuation

User explicitly stopped implementation on2026-09-19 and requested a fresh Astra task. This packet preserves current files and evidence; it does not claim the backend complete or any physical accuracy. Read `goal-pause.json` for the final native pause receipt. No old work continues after this task.

## Repository and verification levels

Repository: https://github.com/nazeeh111/EchoSight (private). Checkout: `/Users/nazeeh/Documents/Codex/2026-09-18/echosight-autonomous-backend-implementation-lead-a/backend`. Branch/default: `backend/implementation`; upstream `origin/backend/implementation`. Local HEAD and directly verified remote HEAD both `27bb6a42f06924b66711360ddb24bc3bfc24a6b3`; ahead0/behind0. Nothing staged at interruption. Teammate `Oltans_UI/UX` was not touched.

- Full assembled review: `f5bf0fa412db9479779a7e944e14ea8c4ea983b7`,34 targeted checks, two inherited P2 cancellation defects found. `evidence/independent-review-f5bf0fa.md`.
- Repair code: `5f778a887817761b9db0626256698c5f678b497f`;201 full tests65.132s,51 input hashes unchanged;17 focused checks13.470s. `evidence/completion-cancellation/`.
- Independent repair follow-up at exact5f778a8:12 cases, both P2s closed, no further P1/P2 in scope. `evidence/independent-review-5f778a8.md`.
- Pushed/reproduced checkpoint: `e457e1488e43518d902e4adbb7aad5ed18f4d5ce`; clean GitHub checkout201tests64.733s plus raw demo/export/replay. `evidence/reproduction-e457e14/`. Existing pinned venv was reused; this was not another fresh dependency download.
- Latest27bb6a4 adds evidence/docs only; Git comparison confirms no change to echosight/tests/schemas frome457e14. It was pushed before shutdown and directly reverified during shutdown. It did not receive a separate full run, which would merely repeat unchanged code. The dirty calibration repair below is excluded from every prior full-suite/review claim.

## Exact unfinished repair and dirty inventory

At interruption only one tracked production file was modified: `echosight/calibration.py`. Three untracked files: `schemas/calibration-reference.schema.json`, `schemas/calibration-result.schema.json`, `tests/test_calibration_contract.py`. No staged files. Shutdown additionally edits `STATE.md` to correct stale status and adds this handoff directory; no production edits were made during shutdown.

The active repair adds a bounded canonical supplied-reference/acquisition snapshot, explicit per-recording verified/not-processed/not-available hash states, a stable calibration input identity, and v1.1 reference/result contracts. It must preserve the existing optimizer, source admission, physical conventions and frozen gates. It excludes filesystem paths/arbitrary annotations and distinguishes supplied reference geometry from inferred structure. Inspect the current diff rather than reimplementing from this description.

Completed targeted command: `.venv/bin/python -m unittest tests.test_calibration_contract tests.test_calibration tests.test_mapping_admission_cancellation.ReferenceCalibrationAdmissionTests -v` logged18 passes5.522s in `work/calibration-boundary-audit/contract-first.txt`. Six were duplicate discovery of an imported TestCase, so this is12 unique checks. Afterward the worker changed only the import to a module and added `provenance.setdefault('recordings',[])`; these final bytes are UNTESTED. The first new round-trip test previously failed as intended with `KeyError: calibration_input`, in `contract-before.txt`.

Pending: missing/empty/malformed probe and rejected-output schema boundaries; actual proposal/rejection examples; docs/CALIBRATION.md; final affected checks, assembled suite and fresh review. No production commit of this repair is authorized as verified yet. `work/calibration-boundary-audit/build_schema.py` is a working schema-generation helper, not a runtime dependency; inspect whether it merits retention. `evidence/calibration-contract/` exists but is empty. No new dependencies, endpoint or cooperative cancellation mechanism is intended.

`inventory.json` has exact SHA-256/size for all four dirty files, current relevant work artifacts,20 raw development recordings, and pre-shutdown STATE. `snapshots/` preserves exact small bytes; `git-diff-production.patch` preserves the tracked patch. Originals remain in place. Do not reset/clean/stash/overwrite them. All other ignored research/raw data remain untouched, indexed by existing manifests.

## Workers and processes

Native inventory: inference interrupted after state collection; evaluation and independent_review completed; physics_audit completed and then interrupted to prevent queued work. No active specialist remains. The earlier acoustics/backend names are historical, not current live workers. `workers-processes.json` records ownership and exact command sessions. All known root commands and worker43988 completed; no running test was interrupted. Approved read-only process inventory found no EchoSight job. No continuation automation was installed.

A protocol draft was assigned verbally but not created: `work/joint-reference-trial/` does not exist. No new joint fit, protocol freeze or raw case was started. Do not assume a chat assignment is executed evidence.

## Status and retained failures

Software is a reusable raw-recording core/local API/CLI with immutable raw storage, clock/source admission, covariance, geometry/alternatives, refinement, controlled comparisons, cancellation/recovery, replay/export and frontend contracts. Minimal native iOS Float32 recorder has unsigned-build/injected software evidence only. The public calibration artifact contract remains unfinished. Full charter objective is unmet.

Synthetic: original narrow twelve-view suites recover multiple independent surfaces including height, but harder13case stress retains30true/48miss/0false. Frozen12case path comparison atde8442b fails: old38true/8false/0miss; update38true/4false/0miss; grid29true/1false/9miss. Two-emitter aliases remain. Clock repair across1248 paired recordings removes three>50ppm errors and one null false echo; seven recordings gain misses, five gain false candidates. All24 paired spatial counts remain124matched/25false/0miss. These are different cohorts, not inconsistent counts.

External measured replay: FLAIR24responses plus laser reference fails, main0definitive/10miss, grid2matches/8unmatched. Survey-only40RIR dEchorate fails:1room match+2unmatched, wrong-receiver control4unmatched. Pose/metadata uncertainty, limited source diversity and chance associations remain. RIR convolved with generated probe is hybrid replay, not our devices. Preserve `evidence/reproduction-659/`, `evidence/measured-multisource-de8442b/` and linked reviews.

Own devices: zero physical validation. No microphone/device launch, installation or signed hardware run. Exact later experiments/thresholds/consequences remain in docs/HARDWARE_ACCEPTANCE.md; do not request them before independent tractable work is finished.

Unresolved science: distributed emitters can imitate wall shifts; wrong direct paths and conditional timing covariance remain; source/receiver survey bias, overlap/higher-order/diffraction mismatch, unseen parent geometry and limited practical viewpoints prevent general reliable reconstruction. More abstention does not satisfy recovery.

Closed/unpromoted branches: expanded18peak catalog helps wrong receiver geometry more than true geometry; joint waveform extractor improves overlap but adds null errors; held-view null guard sacrifices required real surfaces; seven-repeat bootstrap undercovers; source-warning suppression withholds24true surfaces; density clutter guard's small gain did not warrant complexity. Do not reopen without new independent evidence. No criteria were weakened.

Source-reference V1/V2 is complete, not a running experiment: V1 rejects12 including4single controls; V2 admits4single controls and2opposite-phase x cases, rejects6others. One valid single source fails orthogonal transfer229.479µs RMS/282.680µs max. Prospective joint information predicts2.51cm axis SD,2.952cm under worst paired-timing sensitivity, not fitted accuracy. Independent review checks166 archive payloads,288 retained WAV hashes and3raw replays. Paired x/y simulations reused clock/noise draws, so do not claim independent timing coverage. Only after finishing this repair may a separately frozen two-fit development test on existing V2 pairs be considered; no new seeds/families are justified yet. See source-calibration review for full training/held covariance terms and stop conditions.

## Physical conventions and authority

Metres, right-handed,z-up; supplied acoustic centers are calibration. Plane n·x=d, image q=s+2(d−n·s)n. Excess source-buffer delay=(|r−q|−|r−s|)/(c/kappa); never halve bistatic delay. Relative clocks do not identify absolute source rate. Joint source/effective-speed covariance replaces independent budgets and retains cross terms. Reused receiver errors stay correlated; reference errors shared across train/held require cross terms. Support meshes are not physical edges/enclosure/empty/safe space. Ground truth stays outside fitting; confidence is conditional on models, not physically calibrated certainty.

Existing authority: backend-only Python/local free tools, ordinary project branches/commits/pushes/default integration, justified free local dependencies, and one existing EchoSight vault index. Preserve owner/admin, collaborators and unrelated work; never force push. No paid services, credential/global configuration changes, global installations, substantial downloads, deployment, public publication or external submission without separate authority. Old access status: sinha-ritwik acceptedwrite; littleapple08 pendingwrite invitation333732214 at initial verification, not queried anew. Do not duplicate invitations. Vault index `/Users/nazeeh/Claude/vault/echosight.md` is current throughe457e14, not authoritative code state.

## Reconciliation and exact next action

Stale STATE said remotee457e14, native goalactive and an experiment draft underway. Live Git shows27bb6a4; all workers stopped; draft path absent. These are corrected in STATE. CHARTER_ADDENDUM/COVERAGE historical active-goal language is superseded by explicit user shutdown and pause receipt. No filesystem AGENTS.md was found at checkout/ancestors; current task supplied AGENTS instructions directly. New task must check applicable instructions again.

The source-calibration independent checksum manifest names two `.log` files that exist locally but were excluded by ignore rules from27bb6a4. JSON/report/probe counterparts are committed. Exact logs are preserved and hashed here; a later evidence checkpoint must reconcile this packaging gap explicitly, without rerunning science to fabricate replacement evidence.

Astra and effort were never changed. App tools did not expose the setting and native computer-use policy denied Codex access; the user then explicitly confirmed **High**. Preserve **Astra (gpt-6-astra), reasoning effort high**. This setting is user-confirmed, not inferred from tool defaults.

Next single task: finish the existing calibration provenance/result-contract repair in its four dirty files; inspect final two untested edits, exercise meaningful rejected-probe/rejection boundaries, produce actual examples/docs, and run the focused command above. Do not start a solver/experiment. Then full relevant suite, immutable reviewed commit, affected fixes, coherent push/remote verification and clean GitHub reproduction. Use nonoverlapping builder/reviewer ownership; no old writer should be resumed. The ready-to-paste continuation is NEW_SESSION_PROMPT.md.

Deferred only: acoustic reflection/absorption/spectral evidence→material probabilities→plausible appearance/color from material+geometry/context→five-perspective adjudication. Optical color is not measured by acoustic frequency. Keep acoustic false color separate. Unknown/broad distributions are required when evidence is weak; interpretations cannot overwrite raw recordings, geometry, uncertainty or provenance. No premature scaffolding, ML dependency or guessed five-role definitions.
