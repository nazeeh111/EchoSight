# Bounded charter coverage-gap audit

Code inspected and executed: **57e25b2e5db31b93713f6c7c657caceab153839e**, 2026-09-19. Read `docs/CHARTER.md`, `docs/CHARTER_ADDENDUM.md`, current `docs/audit/COVERAGE.md`, public contracts and live recording/API/CLI/inference/evolution code. No main files changed; this report is the only persistent audit artifact. Temporary raw fixtures were removed after execution. No hardware, microphone, external data fit, new held-out answer or candidate-catalog experiment was used.

This is a bounded gap inventory, not a new complete independent approval of previously reviewed code. The author previously contributed to some inference/evolution implementation. Scientific recovery failures, wrong source/path models, unqualified confidence and missing own-device measurements are already accurately identified in the matrix and are not repeated here as new findings.

## 1. P2: cancellation does not consistently remove unfinished geometry or reach the baseline

**Fixable software defect; recommended first because the repair is small and cancellation is an explicit charter obligation.**

`echosight/inference.py:423–429` constructs `out['surfaces']` before remaining candidate, higher-order and mirror checks. Its `_Cancelled` handler at lines520–521 changes status and diagnostics but retains these surfaces and any intermediate hypotheses. The public core can therefore return cancelled output containing definitive geometry that never completed the model checks. `echosight/cli.py:113–124` saves that JSON before returning130. A caller who checks status can avoid displaying it, but the output boundary should not place unchecked geometry in the definitive surface collection at all.

Separately, `echosight/pipeline.py:128–129` calls `infer_baseline` without cancel/progress; `inference.py:530–532` explicitly passes `None,None` into the otherwise cancellable `_run`. A Ctrl-C during baseline inference sets the CLI's event but does not reach the solver; the CLI can finish successfully and save geometry.

Minimal executed raw reproduction used a newly generated room fixture `simulate_session(..., seed=39017, capture_count=12)`, never its truth annotations. An in-process wrapper set the real cancellation predicate at the start of `_second_order_explanations` and called the original implementation. Actual output:

```json
{"status":"cancelled","surface_count":6,"hypothesis_count":1,"dimensions":[],"diagnostics":["refinement_budget_reached","cancelled_by_caller"]}
```

For baseline, a wrapper set the same predicate at `_run` entry and invoked the original solver. Actual output:

```json
{"cancel_requested":true,"result_status":"partial","surface_count":6,"predicate_calls":110}
```

The HTTP store's existing publication lock still prevents an accepted job cancellation from publishing a new current result. This finding does **not** assert that store protection is broken. It concerns the public numerical/CLI result and baseline cancellation propagation, omitted by the matrix's broad “progress, cancellation ... implemented” description.

**Minimal repair:** forward optional cancel/progress through `infer_baseline`; on cancellation clear definitive surfaces/dimensions and either remove interim hypotheses or explicitly mark them unverified without qualifying them as final alternatives. Preserve observations, raw hashes and diagnostics. Add two interruption-point regressions and a CLI save/exit check. Do not rerun scientific acceptance merely for a transport fix unless other numerical changes are made.

## 2. P2: cross-session comparison confuses session-scoped capture identities

**Fixable product/evidence accounting defect; recommended second.**

The frontend contract expressly permits cross-session comparison when a common surveyed frame/source/probe is declared (`docs/FRONTEND_HANDOFF.md`, “Evolving the map”). The store requires capture IDs to be unique only within a session. Nevertheless `echosight/evolution.py:167–179` computes gained/lost support using only `capture_id`; lines183–185 do the same for `new_capture_ids`. It ignores the result session and recording identity. Separate valid sessions commonly use names like `phone_1` or `0`, so different recordings can be reported as unchanged evidence.

Executed minimal reproduction used the existing simple comparison fixture, four support IDs `0`–`3`, identical calibration/frame, sessions `session-a` and `session-b`, distinct result IDs and distinct recording SHA256 values on every observation. The corresponding plane moved by1cm. Actual output:

```json
{"status":"comparable","new_capture_ids":[],"additional_support_count":0,"additional_support_capture_ids":[],"lost_support_capture_ids":[]}
```

Geometric display association is still reasonable, and the result does not claim physical scene change. The error is the displayed explanation of which acoustic evidence changed. This is not a request for global object identity or a scientific change detector.

**Minimal repair:** keep geometry continuity separate from evidence continuity. Namespace capture references by session and bind to available recording identity; retain explicit references in gained/lost support output. At minimum, do not report different-session matching local IDs as the same measurement. Where the same exact waveform is reused across sessions, report reuse rather than call it new independent support. Missing fingerprints need an explicit weaker/unknown evidence-identity status, not inferred independence. Preserve same-session append/reprocess behavior, update the comparison schema/example, and test same local IDs with different bytes, shared exact waveform bytes, and ordinary append-only refinement. No own-device experiment is needed.

## 3. P2 boundary gap: ordinary mapping ignores known contradictory source declarations

**Tractable acquisition-consistency gap, distinct from the unresolved physical source-model problem; recommended after the two direct transport/accounting defects.**

The native decoder preserves `source_declaration.configuration_id`, `.probe_id` and `.route_id` from the hash-bound package. These remain operator declarations, not authenticated facts. `echosight/controlled.py:217–237` correctly checks their known contradictions across captures/epochs. Ordinary `pipeline.py:87–114` checks package continuity and exact waveform reuse, then proceeds under a single fixed calibrated source without checking known source-declaration contradictions across its own captures. The acquisition evidence remains visible, but there is no diagnostic that these records no longer declare one common source configuration/route. The pipeline is shared by the public API's session jobs and ordinary CLI processing.

Executed reproduction: generated twelve independent raw room waveforms with new seed39017; wrapped each exact decoded waveform in a valid native Float32 package using the existing software fixture helper. Source configuration and source route declarations alternated between `source-left`/`source-right` and `route-left`/`route-right`. Native timestamps/continuity remained valid. The actual decoder, waveform extractor and ordinary mapper returned:

```json
{"status":"partial","surface_count":6,"accepted":12,"configurations":["source-left","source-right"],"routes":["route-left","route-right"],"diagnostics":["refinement_budget_reached"]}
```

The waveforms were deliberately unchanged when the declarations changed. This proves the missing consistency check, **not** that these six planes are physically false or that labels authenticate a changed speaker. Different configurations can also be acoustically equivalent. The important point is that the current ordinary path silently combines mutually different known declarations while its point-source calibration assumes one qualified source setup. This omission is separate from the matrix's correctly disclosed inability to discover an undeclared second emitter from sound.

**Minimal repair:** define a per-session source-consistency admission rule shared with the existing controlled checker. Known conflicting source configuration/probe/playback-route declarations should produce an explicit diagnostic and withhold the unsupported single-configuration inference, or require a separately defined calibration that actually supports those configurations. Do not select an arbitrary majority or erase any raw recording. Unknown declarations should remain unknown; legacy WAV remains an operator-declared route and should not silently gain qualification. Do not conflate source playback route IDs with receiver microphone route IDs. Test equal known declarations, all unknown, known conflicts, mixed legacy/native evidence and reprocessing/export preservation. This will not detect undeclared distributed emitters, calibrate an acoustic center, or fix existing measured reconstruction failures.

## Reproduction outline

Run with the project `.venv/bin/python` from repository root. The relevant executed logic is below; each temporary directory is disposable and no truth file is loaded.

```python
import copy, tempfile
from pathlib import Path
from unittest.mock import patch
from echosight.evolution import compare_results
from tests.test_evolution import result
from echosight.simulation import simulate_session
from echosight.storage import load_session, read_recording
from echosight.pipeline import process_session
from echosight import inference
from tests.test_acquisition import capture_bytes

before, after = result(), result(2.01)
for sid, item, digest in [('session-a', before, 'a'*64), ('session-b', after, 'b'*64)]:
    item.update(session_id=sid, result_id=sid+'-result')
    for observation in item['observations']:
        observation['recording_sha256'] = digest
print(compare_results(before, after)['correspondences'])

with tempfile.TemporaryDirectory() as directory:
    session = load_session(simulate_session(Path(directory)/'sim', seed=39017, capture_count=12))
    for i, capture in enumerate(session['captures']):
        samples, rate = read_recording(capture['recording_path'])
        assert rate == 48000
        def mutate(manifest):
            manifest['source_declaration']['configuration_id'] = 'source-left' if i%2 == 0 else 'source-right'
            manifest['source_declaration']['route_id'] = 'route-left' if i%2 == 0 else 'route-right'
        raw, _, _ = capture_bytes(samples, mutate)
        path = Path(directory)/f'{i}.zip'
        path.write_bytes(raw)
        capture['recording_path'] = str(path)
        capture.pop('sha256', None)
    normal = process_session(session)
    print(normal['status'], len(normal['surfaces']), normal['diagnostics'])

    state = {'cancelled': False}
    original = inference._run
    def baseline_entry(*args, **kwargs):
        state['cancelled'] = True
        return original(*args, **kwargs)
    with patch('echosight.inference._run', side_effect=baseline_entry):
        baseline = process_session(session, cancel=lambda: state['cancelled'], method='baseline')
    print(baseline['status'], len(baseline['surfaces']))

    state['cancelled'] = False
    original_ambiguity = inference._second_order_explanations
    def ambiguity_entry(*args, **kwargs):
        state['cancelled'] = True
        return original_ambiguity(*args, **kwargs)
    with patch('echosight.inference._second_order_explanations', side_effect=ambiguity_entry):
        cancelled = process_session(session, cancel=lambda: state['cancelled'])
    print(cancelled['status'], len(cancelled['surfaces']))
```

## Coverage assessment

The matrix correctly keeps the overall objective unmet and distinguishes software execution, synthetic recovery, measured-RIR failures and missing own-device validation. These three gaps should be added as bounded operational/admission tasks; none requires new literature or devices. Fixing them would not establish practical room reconstruction, reliable general path-order identification or calibrated physical uncertainty. The negative candidate-catalog contrast remains closed. Source-clock work is owned separately and was not changed or re-evaluated in this audit.
