# EchoSight: autonomous backend implementation

Lead a real specialist team to research, design, implement, test and deliver **EchoSight’s complete backend**. This authorizes implementation, not another planning handoff. Preserve my selected Astra model and effort. Make routine decisions yourself and continue through integrated, verified code and a usable handoff.

## What EchoSight is for

**Turn sound and its reflections into a useful, evolving 3D model of physical space using ordinary devices.** A MacBook emits designed sound; initially approximately 3–4 iPhones record the direct sound and echoes. EchoSight should infer where physical structure is, its dimensions and spatial relationships, and what the measurements do or do not establish. The ambition is room-scale acoustic spatial reconstruction, with a compelling demonstration whose geometry is earned from sound.

The intended experience is: arrange devices with a practical calibration procedure → emit and record → process the actual recordings → return spatial structure and its supporting evidence → refine the model as additional measurements arrive. When a meaningful scene change or new viewpoint is supported, show what it changes in the inference. The later frontend should be able to display this directly from backend outputs. An audio spectrum, a single fitted plane, a predefined room with animated echoes, or a visually plausible mesh alone does not fulfill this vision.

Investigate the strongest coherent combination of room dimensions, structural surfaces, interior reflectors or objects, scene changes and measurement guidance. These are opportunities, not predetermined feature tiers or promises that every object is recoverable. Seek richer spatial capability rather than accepting the first sparse result; test what information it requires. If a capability cannot be supported, explain the limiting evidence and the best feasible alternative. Choose and substantiate a concrete useful scenario, such as understanding room layout or locating consequential reflectors, without letting an inherited example silently narrow the project.

Optimize physical information, live reliability, speed, calibration burden, originality, visual explainability and integration simplicity together. Make the demonstration's central claim explicit: what EchoSight learns, which acoustic evidence establishes it, and why that matters to a user.

Improve acquisition arrangements, signals, calibration, inference, representation and features when evidence supports it. Propose useful ideas beyond the inherited feature list; investigate stronger alternatives and add valuable capabilities without routine approval. Explain material departures from acoustic mapping; do not substitute optical reconstruction or a generic AI application. “Perfect” means resolving consequential weaknesses with evidence, not maximizing features, infrastructure or documentation.

Backend only; the frontend comes later. Build integrated software before requesting our physical-device experiments. Use synthetic recordings and suitable external measured data now; prepare later hardware acceptance. Never present software completion as demonstrated accuracy on our iPhones. Do not infer a current deadline from historical notes.

**First action:** open **https://github.com/nazeeh111/EchoSight** using an available browser capability, then verify access and collaborators through GitHub. Ensure **sinha-ritwik** and **littleapple08** have accepted write access or pending write invitations; send only missing invitations. These invitations are authorized, but acceptance belongs to the invitees. Preserve my owner access and ability to invite others. If browser display is unavailable, use the authenticated API/CLI. Report actual status and continue independent local work if access is blocked.

## Starting evidence

Workspace: `/Users/nazeeh/Documents/Codex/2026-09-18/astra-chatgpt-work-open-ended-acoustic`.

Read applicable AGENTS.md and `outputs/research/STATE.md`. Retrieve supporting files selectively from `outputs/research/`:

- Design and alternatives: `BACKEND_REPORT.md`, `PRODUCT_AND_EVENT.md`, `MASTER_FLOWCHART.md`.
- Mathematics/interfaces: `NUMERICAL_CORE.md`, `THREED_CONTRACT.md`, `specialists/design_completion.md`.
- Sources/contradictions: `EVIDENCE.md`, `PRIMARY_SOURCES.md`, relevant specialist reports.
- Executed evidence: `experiments/`, `fixtures/`; raw external material is indexed by manifests in workspace `work/science/` and the research package.
- Environment/recovery: `ENVIRONMENT.md`, `CONTINUATION.md`.

Original packet: `/Users/nazeeh/Downloads/ASTRA_Ongoing_Investigation_Handoff_v2/`.

These are references, not a prescribed architecture. This charter supersedes historical frontend scope, initial-phone-test gates and restrictions on authorized project commits. Governing instructions and native permission boundaries remain applicable.

Interleave research and implementation: identify a consequential uncertainty, compare alternatives, derive or test, integrate, and reopen dependent decisions. Challenge the preferred approach against a serious competitor under comparable conditions. Check load-bearing claims against primary sources and executable evidence. Preserve source versions, access depth, failures and uncertainty; distinguish theory, simulation, published experiments and our measurements. Agent agreement is not independent proof. Avoid repeatedly restarting the literature review.

Keep a short prioritized queue of consequential risks and opportunities in project state. After the first end-to-end result, investigate its strongest failure mode and the most promising capability improvement; implement improvements supported by evidence and recheck affected behavior. Preserve a runnable baseline while exploring. Close a branch when its evidence or benefit no longer warrants the effort. Do not declare completion while an identified, tractable issue materially undermines the selected demonstration; do not expand scope endlessly for speculative gains.

## Engineering and physics

Deliver a reusable processing core, local HTTP API and CLI demonstration covering session/pose/probe definitions, probe generation, recording/upload contracts, lossless import, provenance, quality checks, clock/source diagnostics, response estimation, inference, uncertainty, supported 3D geometry, replay/export and recovery states. A minimal acquisition harness is allowed; a dashboard, styled mobile app or frontend viewer is outside scope.

Own the route from recordings to spatial results, not only an inverse solver fed perfect echo labels. Choose and document a viable iPhone acquisition/import route, source playback contract and required pose information. Expose missing calibration as a diagnostic, and keep raw data available for reprocessing. Include tests that enter through recording import as well as focused mathematical tests.

Give the later frontend versioned schemas/examples, stable IDs, units/coordinates, progress/cancellation, errors and renderable geometry with evidence/confidence. Return partial or ambiguous results honestly. Never hard-code successful geometry or silently replace capabilities with placeholders.

Derive the selected forward model, unknowns, calibration, observable quantities, ambiguities, objective and uncertainty; connect equations to code and numerical checks. Distinguish physical time from source-buffer time; handle clock offsets, rates and warp through validated correction or joint estimation, propagating remaining timing uncertainty into geometry. Check physical forward-model residuals, shared uncertainty and global ambiguities. Separated speakers and receivers require actual propagation geometry, not blindly halving delay-derived distance. These are correctness obligations, not a compulsory solver, peak-labeling scheme or plane-only representation.

Planes alone do not establish physical edges or a closed room; missing echoes do not establish empty or safe space. Keep ground truth/evaluation annotations outside fitting. Test simulator/solver mismatch, held-out cases and appropriate measured data. Measure geometry error, erroneous surfaces, uncertainty and runtime under stated conditions. Keep mathematics, contracts, diagrams and implementation consistent.

Choose EchoSight’s strongest demonstrable contribution by connecting user value to acoustic information, calibration requirements, implementation effort and demonstration evidence. Provide repeatable backend demos and exports distinguishing measured, simulated, replayed, supplied and inferred information. Do not fabricate novelty or winning odds.

Check relevant prior art and current event requirements when they affect claims, reuse or delivery. Prepare a concise demonstration narrative and evidence for the later frontend team. Missing event details must not block independent engineering; external submission, publication and deployment remain separately authorized actions.

## Languages, skills and specialists

Default to Python for scientific computation and backend orchestration. Use JavaScript/TypeScript and minimal HTML where browser acquisition or integration needs them. Add C/C++ for a necessary library or measured performance benefit, checking numerical agreement. Prefer a small maintainable architecture and pinned project-local dependencies over speculative frameworks or multiple services.

Read relevant skills when needed:

- `01`: `/Users/nazeeh/.agents/skills/01/SKILL.md`, for adaptive execution and proportionate verification.
- `scientific-python-local`: `/Users/nazeeh/.codex/skills/scientific-python-local/SKILL.md`, when the project lacks a suitable numerical environment.
- `blender-local`: `/Users/nazeeh/.codex/skills/blender-local/SKILL.md`, optionally for synthetic scene fixtures, geometry/export checks and technical renders. Follow its current runtime guidance. Blender alone is not an acoustic simulator; keep scene truth outside reconstruction. Do not make it a runtime dependency without a concrete reason.
- OpenAI Docs for uncertain Astra/Codex behavior; relevant debugging, review or PDF skills when the actual work warrants them.

Find missing capabilities with `/Users/nazeeh/.agents/skills/codex-offshore-router/SKILL.md`, `/Users/nazeeh/.agents/skills/find-skills/SKILL.md` and current primary documentation. Compare acoustic simulators, datasets and audio/geometry tools with simpler options. Check assumptions, licensing, compute/platform needs and installation behavior; verify a representative task. Justified free project-local dependencies/helpers are authorized. Avoid bulk installations and external instructions that conflict with this charter.

Use real specialist subagents covering acoustics/acquisition/timing; inference/geometry/uncertainty; backend/API/integration; and evaluation/product/demo quality. Adapt team size to actual limits. Keep the adversarial reviewer independent of the reviewed code. Disclose unavailable delegation and continue with labeled review passes.

Assign bounded outcomes, owned files and shared contracts; require code/findings, checks, uncertainties and integration implications. The coordinator owns architecture, integration, state and publication, and keeps useful work moving during delegation. Cross-check timing, units, poses, uncertainty and failure semantics across modules. Resolve disputes with evidence; avoid overlapping writers and keep long logs outside coordinator context. Consult relevant vault knowledge narrowly without copying personal notes into Git.

## Repository and authority

Use the existing private EchoSight repository. Inspect remote and local work; use a dedicated checkout, preferably unused workspace `backend/`. Preserve teammates’ contributions, access and pending invitations. Do not replace the repository, restrict collaboration or change ownership/visibility.

I authorize project branches, ordinary commits/pushes and integration of your own verified work into this repository’s default branch. Push meaningful verified checkpoints and confirm the final remote commit. Never force-push or discard unrelated work. Commit portable code, tests, concise evidence and permitted fixtures; exclude secrets, personal data and restricted/large datasets. Provide licensed retrieval instructions where needed.

Use existing subscription access and free tools. Paid services, spending, credentials/global-configuration changes, global installations, substantial downloads, vault changes beyond the project note authorized below, public publication and deployment need separate authority. Respect native approvals and continue independent work when one branch is blocked.

## Continuation and completion

Use native Goal mode with this objective: **Deliver EchoSight’s verified backend in nazeeh111/EchoSight, with working API/CLI, reproducible evaluation and frontend handoff; physical validation follows later.** Reuse a compatible active goal; create it only if no unfinished goal exists. Do not stop after planning.

Save this charter and maintain concise `STATE.md`: authority, checkout/branch/commit, decisions, evidence/test pointers, active jobs, unresolved issues and next action. Link it from the research state and update at meaningful milestones. Keep detailed evidence outside active context and setup portable.

I authorize maintaining **one EchoSight note** in `/Users/nazeeh/Claude/vault`, following `using-this-vault.md` and reusing a matching note. After repository checkpoints, update concise decisions, verified findings, limitations and links to the repository/charter/state, with date and commit. Preserve unrelated notes and user edits. Do not reorganize the vault, duplicate archives or store secrets. Plain Markdown suffices. If writing is blocked, report it and continue from repository state.

Repository files are authoritative project state; Obsidian is an index; chat summaries are temporary context. Keep proposed, implemented, tested and physically validated claims distinct and linked to evidence. Correct superseded claims; repeated summaries are not independent confirmation.

Treat compaction as potentially lossy. Save consequential decisions when made, not only just before transitions. After a visible compaction or recovery, verify scope, physical conventions, rejected alternatives, last tested commit, active workers and next action against original project files. Resolve contradictions before dependent edits; confidence or a repeated summary is not verification. Avoid reloading the archive or rerunning every test as a ritual.

At completed integration milestones, assess whether a fresh coordinator would reduce stale context. Prepare a concise artifact-backed handoff when needed, before obvious confusion is the only warning. No universal compaction-count or context-percentage threshold is established; do not invent telemetry. If grounding fails or work repeatedly loops, checkpoint and request a fresh task. Ask me to pause the old goal and account for its workers before another writer starts. Continue autonomously within the supported runtime; never imply execution survives runtime termination.

Claim completion only when these hold:

- API/CLI work from recording input to genuine 3D spatial output on suitable nondegenerate test scenes, recovering multiple independent surfaces or equivalent spatial structure, including height-dependent information. Also demonstrate truthful partial, ambiguous and no-result cases. Declare any model/data restrictions; a 2D result extruded to 3D or supplied scene geometry is not acoustic 3D inference.
- Define acceptance criteria before final evaluation; compare the mapper with a simple baseline on frozen held-out cases. Report gains, regressions, false surfaces, missed structure and ambiguous/no-result behavior; use null/clutter controls where appropriate. Distinguish measured annotations from model-generated labels. Investigate consequential external-data failures without tuning to held-out answers or weakening criteria merely to pass.
- Relevant physics, malformed-input, resource-limit, cancellation and export/reload checks pass; performance is measured. Expand verification for actual failures or unresolved risks.
- A fresh reviewer checks consequential mathematics and the assembled backend at an identified commit, not only isolated modules. Resolve material findings and rerun affected checks after consequential fixes; record which final code was verified.
- A clean checkout reproduces setup, tests and demonstration. Include frontend contracts/examples, source/license provenance and later physical-acceptance steps. Use CI only within verified free allowance.
- Final code is committed and verified on GitHub. Clearly separate software results from remaining hardware uncertainty.

If a consequential requirement remains unsupported after justified alternatives and targeted investigation, preserve the runnable work and evidence, finish independent unblocked work, and identify the exact limiting assumption and next decision or experiment. Report the objective as unmet rather than weakening the requirement, selecting only favorable cases or looping indefinitely. Distinguish a scientific limitation from a missing measurement, permission or runtime resource.

Return the repository URL/commit, demonstrated capabilities, exact setup/run/test/demo commands, frontend handoff and remaining limits. Start with GitHub access/invitations, then inspect evidence/environment and implement the first complete input-to-result path. Continue researching and improving consequential weaknesses while delivering the whole backend.
