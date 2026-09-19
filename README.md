# EchoSight backend research prototype

**Active development:** this is a runnable baseline, not a completed charter. The [requirement coverage audit](docs/audit/COVERAGE.md) separates implemented mechanisms, missing capabilities and validation limits.

EchoSight turns lossless audio recordings at surveyed microphone positions into evidence-linked 3D reflector estimates. A fixed source emits a known probe; receivers need not share clocks. Raw recordings, timing diagnostics, competing explanations, supported surface patches and conditional uncertainty remain available for inspection.

The frozen twelve-view synthetic benchmark recovers all six room surfaces, including floor and ceiling, and a seventh tilted reflector in its designated case, with zero false surfaces. Eight-view cases have documented misses. Harder multipath cases and external measured-room spatial acceptance still fail. Measured response replay is not demonstrated measured3D accuracy. **Our iPhones and MacBook have not yet been physically validated.** See the [evaluation evidence](docs/EVALUATION.md) and [current verification state](STATE.md).

## Run locally

Python 3.12 or later with a compatible NumPy/SciPy wheel is required. No paid services or API credentials are used.

```sh
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python -m echosight demo work/demo --seed 1 --captures 12
python -m echosight process work/demo/session.json --output work/demo/reprocessed.json
python -m echosight inspect work/demo/result.json
python -m echosight refine-demo work/refinement --seed 1
python -m echosight export work/demo/session.json --output work/survey.zip
python -m echosight replay work/survey.zip --store work/replay-store --output work/replayed.json
python -m echosight serve --root work/store --port 8765
```

Run from the repository root. Installation of the package itself is optional; `python -m echosight` works directly. For an installed command, run `python -m pip install -e .` then use `echosight`.

```sh
python -m pip install -r requirements-test.txt
python -m unittest discover -s tests -v
python -m evaluation.run --output work/held-out
python -m evaluation.run --extended --output work/held-out-extended
```

The HTTP tests bind an ephemeral loopback port. A restrictive sandbox must grant that local capability; a bind denial is not an acoustic failure. Evaluation records all cases and exits nonzero when required criteria fail. `--development` runs the separate development cases. Core runtime is macOS/Linux; the local store uses a POSIX ownership lock. No cloud services or runtime datasets are needed.

## Inputs and outputs

The simulator writes PCM recordings, a session manifest, a playback probe and separate evaluation truth. Processing takes only the session and recordings. `result.json` contains inferred planes, reflection points, triangles spanning observed support, uncertainty, dimensions where applicable, raw-recording hashes and extraction diagnostics. The truth file never enters fitting. These meshes do not establish physical edges, enclosure or empty space.

The same pipeline is callable as `echosight.pipeline.process_session(path_or_session)` and through the local API. Session input defines metres, right-handed coordinates with z up, supplied acoustic-center positions, sound speed, source-clock uncertainty and exact probe metadata. Missing calibration produces a diagnostic.

Use `python -m echosight compare old.json new.json --output comparison.json` to explain changes in support and associate refined surfaces. This does not declare physical disappearance from missing echoes.

For later physical acquisition, `python -m echosight probe work/playback --channel left --period 1` creates one continuous stereo playback WAV and its manifest; the other channel is silent. This command does not play audio. Preserve source routing and survey microphone positions. The [minimal native iOS recorder](acquisition/ios/README.md) exports exact delivered Float32 samples with buffer timestamps and interruption evidence; its unsigned build and injected-buffer checks are software evidence only. The phyphox fixture remains provisional. [Hardware acceptance steps](docs/HARDWARE_ACCEPTANCE.md) remain required. Four phones across three placements, or three phones across four placements, can supply twelve surveyed views in a static scene.

Imported archive computations are quarantined as unverified artifacts. Replay recomputes from original recordings instead of trusting stored geometry. Session IDs are immutable within a store; use a new replay-store directory when importing the same archive again.

For repeatable acoustic-change controls:

```sh
python -m evaluation.controlled_development --output work/controlled-demo --receivers 4 --scenario moved
python -m echosight controlled work/controlled-demo/protocol.json --output work/controlled-demo/result.json
```

Four fixed phones support unlocalized repeatable change in this synthetic example. A separate twelve-static-receiver development case supports conditional reflector displacement. See [controlled protocol](docs/audit/CONTROLLED.md), [API](docs/API.md) and [fixed later hardware acceptance](docs/HARDWARE_ACCEPTANCE.md). These are bounded software capabilities, not physical validation.

## Project evidence

- [Current state and next work](STATE.md)
- [Implementation charter](docs/CHARTER.md)
- [Module and data contract](docs/CONTRACT.md)
- [Frontend handoff and repeatable demonstrations](docs/FRONTEND_HANDOFF.md)
- [Acquisition and later physical acceptance](docs/ACQUISITION.md)
- [Signal model](docs/SIGNAL_MODEL.md), [inference equations](docs/INFERENCE.md)
- [Frozen evaluation criteria](evaluation/acceptance.json), [evaluation protocol](docs/EVALUATION.md)
- [Source and license provenance](docs/SOURCES.md)

Only original code, small evidence and permitted fixtures belong in Git. Generated recordings, downloaded datasets and environment packages belong in ignored `work/` or `.venv/` directories. No deployment or public submission is included.
