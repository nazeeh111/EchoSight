# Install and use EchoSight

EchoSight is a local backend for processing lossless recordings into supported 3D reflector patches. The public CLI and HTTP workflow uses one fixed source and surveyed receiver positions. It produces JSON and raw-data archives; a graphical room viewer is not included. Synthetic room reconstruction works on the documented demo. Harder synthetic and external measured-room cases still fail, and our devices have not been physically qualified. See [current status](../STATE.md).

## 1. Install

Use macOS or Linux, Git, and Python 3.12 or later with compatible NumPy/SciPy wheels. Clone with an account that has access to the private repository:

```sh
git clone --branch backend/implementation https://github.com/nazeeh111/EchoSight.git
cd EchoSight
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python -m echosight --help
```

Run the commands below from this repository root with the virtual environment active. `python -m echosight` does not require installing the package itself. No runtime service, API key, external dataset, or paid API is needed. Windows is not a supported native runtime because the store uses POSIX file locking.

To run the software checks, install the test dependencies separately:

```sh
python -m pip install -r requirements-test.txt
python -m unittest discover -s tests -v
```

HTTP tests need permission to bind temporary local ports. The [evaluation guide](EVALUATION.md) covers scientific benchmarks separately; passing software tests is not measured room accuracy.

## 2. Run the room demo

```sh
python -m echosight demo work/demo --seed 1 --captures 12
python -m echosight inspect work/demo/result.json
```

`demo` generates twelve independent simulated recordings and processes them. This case produces six supported room surfaces, including floor and ceiling. Open `work/demo/result.json` for geometry, evidence and diagnostics. `work/demo/session.json` describes the inputs; its recording paths are relative to that file. The separate `truth.json` is used only for evaluation and never supplied to the mapper.

To rerun only processing:

```sh
python -m echosight process work/demo/session.json --output work/demo/reprocessed.json
```

These files are JSON results, not an interactive 3D viewer. A viewer can use each surface's `vertices_m` and zero-based `triangles`, plus the linked reflection rays. [Frontend handoff](FRONTEND_HANDOFF.md) explains rendering, units and evidence IDs.

## 3. Prepare your own recordings

Generate the exact playback file and its manifest before recording:

```sh
python -m echosight probe work/playback --channel left --period 1
```

This writes `probe.wav` and `probe.json`; it does not play sound. Play the complete WAV as one continuous buffer at its nominal rate. Left-channel playback is stereo with a silent right channel; the recordings you import must be **mono**. Preserve both probe files. Do not replace their metadata with an empty `probe` object.

Keep the source position, orientation, route and gain fixed. Record at distinct, stationary microphone positions in one static scene, including different heights. Survey the speaker and microphone acoustic centers in metres, using one coordinate frame with z upward. Twelve stops are the demonstrated synthetic configuration, not a promise that any twelve physical recordings will reconstruct a room. A laptop channel is not automatically a physically valid point source.

The [native iOS recorder](../acquisition/ios/README.md) exports an original `.echosight.zip` containing Float32 audio and acquisition evidence. Its unsigned build and injected-buffer tests do not establish installation or microphone behavior on a phone. Follow [acquisition](ACQUISITION.md) and [hardware acceptance](HARDWARE_ACCEPTANCE.md) before making measurement claims. Standalone mono PCM/Float32 WAV is also supported, with sample continuity explicitly unverified. M4A/AAC and stereo recordings are rejected.

Place original recordings in `work/my-room/raw/`. The following creates a session template using the exact probe metadata. It deliberately leaves unknown positions as `null`:

```sh
python - <<'PY'
import json
from pathlib import Path

root = Path('work/my-room')
recordings = sorted(p for p in (root / 'raw').iterdir()
                    if p.is_file() and p.suffix.lower() in {'.wav', '.zip'})
if not recordings:
    raise SystemExit('Put original WAV or capture ZIP files in work/my-room/raw first.')
session = {
    'schema_version': '1.0',
    'session_id': 'my-room',
    'coordinate_frame_id': 'my-room-survey',
    'source_position_m': None,
    'probe': json.loads(Path('work/playback/probe.json').read_text()),
    'captures': [
        {'capture_id': f'capture-{i:02d}',
         'recording_path': p.relative_to(root).as_posix(),
         'receiver_position_m': None,
         'provenance': 'measured'}
        for i, p in enumerate(recordings)
    ],
}
destination = root / 'session.json'
with destination.open('x') as stream:
    json.dump(session, stream, indent=2)
print(destination)
PY
```

Edit `work/my-room/session.json`: replace the null source and receiver positions with your surveyed `[x, y, z]` values. Set `source_position_std_m` and each capture's `receiver_position_std_m` to justified survey uncertainties; omitted values default to 0.01 m and are not automatically valid for your setup. Review the sound-speed and source-clock assumptions in the [session contract](CONTRACT.md) and [session schema](../schemas/session.schema.json). The template declares actual recordings as `measured`; keep simulated or replayed data labeled accordingly. It refuses to overwrite an existing session file.

```sh
python -m echosight process work/my-room/session.json --output work/my-room/result.json
python -m echosight inspect work/my-room/result.json
```

Read recording-level diagnostics even if processing finishes. Import permits more formats/rates/durations than acoustic processing: processing requires 16–96 kHz, at most 30 seconds, and a probe band compatible with the delivered rate. Recordings must contain the complete probe. Original native ZIP evidence is checked again during processing; relabeling a capture cannot repair an interruption or contradictory source declaration. Exact waveform copies cannot provide independent positions. [Import and processing limits](API.md#jobs-recovery-and-limits) give the full bounds.

## 4. Use the local HTTP API

The API exposes the same processing pipeline. In a separate terminal, activate the environment and start it from the repository root:

```sh
python -m echosight serve --root work/api-store --host 127.0.0.1 --port 8765
```

Keep that terminal running. In your original terminal, this complete standard-library client uploads the demo's original recordings, polls a job, saves its result and downloads an archive. Run the demo in section 2 first. To use your own prepared session instead, change `session_path` to `work/my-room/session.json`.

```sh
python - <<'PY'
import json
from pathlib import Path
import time
import urllib.request

base = 'http://127.0.0.1:8765'
session_path = Path('work/demo/session.json')
output = Path('work/api-demo')
output.mkdir(parents=True, exist_ok=True)

def request(method, route, body=None, headers=None, raw=False):
    if isinstance(body, dict):
        body = json.dumps(body).encode()
    req = urllib.request.Request(base + route, data=body,
                                 headers=headers or {}, method=method)
    with urllib.request.urlopen(req, timeout=30) as response:
        data = response.read()
    return data if raw else json.loads(data)

spec = json.loads(session_path.read_text())
payload = {k: v for k, v in spec.items()
           if k not in {'captures', 'session_id', 'revision', 'created_at', 'replay'}}
session = request('POST', '/v1/sessions', dict(payload, captures=[]))
route = '/v1/sessions/' + session['session_id']
fields = {'capture_id', 'receiver_position_m', 'receiver_position_std_m',
          'provenance', 'device_id', 'receiver_pose_group_id', 'notes'}
for capture in spec['captures']:
    metadata = {k: v for k, v in capture.items() if k in fields}
    audio = (session_path.parent / capture['recording_path']).read_bytes()
    request('POST', route + '/recordings', audio,
            {'X-Capture-Metadata': json.dumps(metadata)})
job = request('POST', route + '/jobs', {})
ids = {'session_id': session['session_id'], 'job_id': job['job_id']}
(output / 'ids.json').write_text(json.dumps(ids, indent=2))
deadline = time.monotonic() + 120
while job['status'] in {'queued', 'running'}:
    print(job['status'], job['progress'], job.get('message', ''))
    if time.monotonic() >= deadline:
        raise SystemExit('Still processing; use ids.json to poll or cancel the job.')
    time.sleep(0.5)
    job = request('GET', '/v1/jobs/' + job['job_id'])
if job['status'] != 'completed':
    raise SystemExit(json.dumps(job, indent=2))
result = request('GET', route + '/result')
(output / 'result.json').write_text(json.dumps(result, indent=2))
(output / 'session.json').write_text(json.dumps(request('GET', route), indent=2))
(output / 'session.zip').write_bytes(request('GET', route + '/export', raw=True))
print(result['status'], len(result['surfaces']), 'surfaces; saved to', output)
PY
python -m echosight inspect work/api-demo/result.json
```

Each run creates a new API session. `work/api-demo/` holds the latest downloaded outputs and IDs; preserve an earlier run before replacing those local copies. Downloaded `session.json` contains paths relative to the server's store, so use its ZIP archive for local replay. The CLI session from section 2 or 3 references your local raw files directly.

Use the saved IDs with `GET /v1/jobs/{job_id}` to poll or `POST /v1/jobs/{job_id}/cancel` with `{}` to request cancellation. `GET /v1/jobs/{job_id}/result` retrieves that completed job's immutable output. A `completed` job can still have a scene status of `no_result`; progress measures work, not confidence. Stop the server with Ctrl-C when finished. Only one process may open the same store. The service accepts trusted local clients and rejects browser Origin requests; browser integration needs the design described in [API.md](API.md).

## 5. Interpret and preserve results

| Output | How to use it |
| --- | --- |
| `surfaces` | Supported 3D patches with geometry and linked echo evidence. A patch boundary is not a measured wall edge. |
| `hypotheses` | Qualified alternative explanations; do not merge them into definitive geometry. |
| `observations` and `diagnostics` | Recording admission, timing/candidate evidence and reasons for missing structure. |
| `uncertainty` | Conditional uncertainty under the fitted model; it excludes unmodeled hardware and wrong path/source explanations. |
| `partial`, `ambiguous`, `no_result` | Inspect the missing support or competing explanations. None establishes empty or safe space. |
| `stale=true` | The API result predates the current session revision. Submit a new job. |

Export a local session and replay it in a new store:

```sh
python -m echosight export work/demo/session.json --output work/room.zip
python -m echosight replay work/room.zip --store work/replay-room-1 --output work/replayed-result.json
```

CLI `export` imports and **reprocesses** the session before archiving original recordings and its computed result. API export archives the stored session and available result. An archive preserves current inputs, not the store's full revision history. Imported computations are quarantined; replay recomputes from original audio. Use a fresh replay-store path when importing the same session again, because an existing session ID cannot be overwritten. You can also replay `work/api-demo/session.zip` using this command's archive argument.

## 6. Refine a session and correct calibration

For local files, preserve the old result, add genuinely new recordings and surveyed poses to the same session, then process into a new result file. Keep source/probe/coordinate-frame declarations consistent. For API sessions, upload new captures to the same session and start another job. Old job results remain available; existing session results become stale after input changes.

A runnable synthetic refinement example:

```sh
python -m echosight refine-demo work/refinement --seed 1 --initial-captures 4 --captures 12
python -m echosight compare work/refinement/initial-result.json work/refinement/result.json --output work/refinement/comparison.json
```

The comparison describes changes in inferred support, not physical object removal. For three or more comparisons, carry the previous comparison with `--previous-comparison previous-comparison.json` to retain display tracks. [Tracking](TRACKING.md) defines calibration compatibility and the version 1.1 comparison contract.

For an API calibration/pose correction, first GET the session's current `revision`, then PATCH `/v1/sessions/{session_id}` with that `expected_revision` and the new `calibration` and/or existing capture poses. Submit a new job afterward. A revision conflict requires reloading, not overwriting. Original recordings cannot be replaced by PATCH. The [calibration PATCH example](API.md#correct-calibration-and-reprocess-preserved-recordings) defines the exact body.

Optional empirical calibration uses separate reference recordings and a surveyed reference plane:

```sh
python -m echosight calibrate-reference calibration-session.json reference.json --output calibration.json
```

Prepare those two inputs using [CALIBRATION.md](CALIBRATION.md). This command writes a proposal or rejection and never changes a session automatically. Inspect the held-out evidence before applying a proposal. Apply its source position, effective speed and joint covariance together. The current mapper assumes calibration is independent of mapping audio and receiver survey errors; reusing calibration recordings or correlated surveys does not satisfy that assumption. The reference plane is supplied calibration, not recovered room geometry.

## 7. Material profiles and contextual appearance

Interpretation is a separate optional layer after geometry. It compares recording-derived surface features with your supplied, labeled reference profiles. It does not ship a universal building-material classifier. Colors are contextual predictions from supplied palettes, not colors measured by sound. See [MATERIALS_APPEARANCE.md](MATERIALS_APPEARANCE.md) for the controlled demonstration, evidence requirements and limits.

For your own known reference sample, first process its raw session and identify the supported surface in the result:

```sh
python -m echosight process reference-session.json --output reference-result.json
python - <<'PY'
import json
from pathlib import Path
result = json.loads(Path('reference-result.json').read_text())
for surface in result['surfaces']:
    print(surface['surface_id'], len(surface['support']), 'supporting observations')
PY
```

Create `reference-provenance.json` with the supplied label's provenance, for example `{"kind":"supplied","note":"Operator-supplied identity of the known reference sample."}`. Replace `SURFACE_ID_FROM_RESULT` below with the selected ID:

```sh
python -m echosight material-reference reference-session.json --surface-id SURFACE_ID_FROM_RESULT --material-id known-reference --label "Known reference sample" --route-id declared-route --provenance reference-provenance.json --regularization-std-db 1 --output profile.json
```

This reprocesses the original recordings, then requires at least five independent valid feature observations for that surface. It saves empirical feature statistics, training hashes, route/probe/angle compatibility and declared assumptions. It can reject an apparently supported surface when the recording features are inadequate. The example's `--regularization-std-db 1` declares an added 1 dB regularization assumption; it is not a measured error estimate or automatic qualification. The default is zero, and a singular covariance is rejected.

Optionally pass `--appearance palette.json`. A palette has explicit provenance and probabilities, such as:

```json
{
  "provenance": {"kind": "supplied", "note": "User-supplied contextual palette, not an optical measurement."},
  "colors": [{"color_srgb": "#8A6B47", "probability": 0.75}]
}
```

That example assigns only 0.75 of its color mass; the remainder stays unassigned. No default color is inferred from a material's name. Palette data can also be added to a profile before including it in a context, provided the complete context passes validation.

Build a context file containing the profile and explicit operating criteria:

```sh
python - <<'PY'
import json
from pathlib import Path
context = {
    'schema_version': '1.0',
    'route_id': 'declared-route',
    'profiles': [json.loads(Path('profile.json').read_text())],
    'maximum_squared_distance': 16,
    'minimum_views': 3,
}
Path('context.json').write_text(json.dumps(context, indent=2))
PY
python -m echosight process query-session.json --interpretation-context context.json --output interpreted-result.json
python -m echosight inspect interpreted-result.json
```

Use independently recorded query audio and a compatible declared route/probe/angle range. The cutoff and minimum-view settings above are explicit operational choices, not calibrated confidence levels. A one-profile library compares only against that one reference; it cannot exclude materials missing from the library. Out-of-domain, reused-training, weak or otherwise unsupported evidence stays unknown. Inspect evidence coverage separately from the normalized conditional material probabilities. Missing palette mass remains unassigned in appearance output.

`inspect` includes each surface's material and appearance status, conditional probabilities, coverage and contextual colors, while the full result retains feature records and diagnostics. `--interpretation-context` on `process` affects only that run and preserves the input session file. To make exports/replay carry it, store the same object as `interpretation_context` in the session JSON. On `demo`, the option is also saved in the generated session manifest, but the ordinary legacy room simulator is not a material-training benchmark.

API users can include context during session creation or revision-checked PATCH, then run a new job. Setting it to null clears it. `POST /v1/sessions/{session_id}/material-reference` builds a profile from a chosen current nonstale result using the same builder; [the API contract](API.md#conditional-material-and-appearance-context) provides request and error details. Context changes preserve geometry fitting, raw recordings and prior jobs while changing the new result's identity.

## 8. Troubleshoot

| Symptom | Next step |
| --- | --- |
| `No module named echosight` | Run from the repository root with the intended virtual environment active. |
| Missing NumPy/SciPy or no compatible wheel | Check the Python version and platform; install the pinned requirements into that environment. |
| `missing_calibration`, `no_result`, or rejected observations | Inspect result diagnostics, actual source/receiver poses, exact probe metadata, delivered sample rate, duration and native interruption evidence. Do not add invented geometry to make the result pass. |
| API connection refused | Check the server terminal, host and port; start `serve` and leave it running. |
| Local bind denied | Grant the sandbox local-loopback capability. This is a runtime permission failure, not an acoustic result. |
| HTTP 400 / 413 | Read the error body; correct malformed metadata or an input exceeding the [documented limits](API.md#jobs-recovery-and-limits). |
| HTTP 403 from a browser | The local API rejects browser Origin requests. Use the documented local client or an explicitly designed proxy. |
| HTTP 409 / store already open | Reload a changed revision, wait for an active job, use a new import store, or stop the other store owner, according to the error. Never delete active state to bypass it. |
| HTTP 404 for a result after import | The archived computation is quarantined. Start a new job to compute a local result. |
| Job `interrupted` after restart | Inputs remain stored. Start a new job; unfinished jobs do not silently resume. |
| Shell reports success but the room is incomplete | Inspect scene status and diagnostics. Successful execution is distinct from successful acoustic reconstruction. |

CLI invalid input returns exit 2; cooperative cancellation returns 130. `process` can exit 0 with `partial`, `ambiguous`, or `no_result`, so inspect the saved JSON. `calibrate-reference` returns 2 for a rejected proposal. Preserve raw inputs and failed results when investigating a problem.

## Additional interfaces

The fixed-source Python interface is `echosight.pipeline.process_session(session_or_path, cancel, progress)`. The [multi-source Python interface](../echosight/multisource.py) is experimental; moving the source within a public single-session recording set does not enable it. [Controlled acoustic change](audit/CONTROLLED.md) has a separate declared recording protocol and CLI/API route. Both retain their documented scientific limits.

For integration details use [frontend handoff](FRONTEND_HANDOFF.md), [API reference](API.md), and the [schemas](../schemas/); for capability evidence and unresolved work use [coverage](audit/COVERAGE.md).
