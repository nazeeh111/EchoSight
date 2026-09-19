# EchoSight backend

EchoSight turns lossless audio recordings at surveyed microphone positions into evidence-linked 3D reflector estimates. A fixed source emits a known probe; receivers need not share clocks. Raw recordings, timing diagnostics, competing explanations, supported surface patches and conditional uncertainty remain available for inspection.

**Implementation in progress.** The first connected synthetic recording-to-geometry path works. Development clutter controls exposed false correspondences that are being addressed; this checkpoint is not final acceptance. No accuracy on our iPhones or MacBook has been demonstrated. The private repository remains private.

## Run locally

Python 3.12 or later with a compatible NumPy/SciPy wheel is required. No paid services or API credentials are used.

```sh
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python -m echosight demo work/demo --seed 1
python -m echosight process work/demo/session.json --output work/demo/reprocessed.json
python -m echosight inspect work/demo/result.json
python -m echosight serve --root work/store --port 8765
```

Run from the repository root. Installation of the package itself is optional; `python -m echosight` works directly. For an installed command, run `python -m pip install -e .` then use `echosight`.

```sh
python -m unittest discover -s tests -v
python -m evaluation.run --development --output work/development-evaluation
```

The HTTP tests bind an ephemeral loopback port. A restrictive sandbox must grant that local capability; a bind denial is not an acoustic failure. Development evaluation records failures and exits nonzero when required criteria fail.

## Inputs and outputs

The simulator writes PCM recordings, a session manifest, a playback probe and separate evaluation truth. Processing takes only the session and recordings. `result.json` contains inferred planes, reflection points, triangles spanning observed support, uncertainty, dimensions where applicable, raw-recording hashes and extraction diagnostics. The truth file never enters fitting. These meshes do not establish physical edges, enclosure or empty space.

The same pipeline is callable as `echosight.pipeline.process_session(path_or_session)` and through the local API. Session input defines metres, right-handed coordinates with z up, supplied acoustic-center positions, sound speed, source-clock uncertainty and exact probe metadata. Missing calibration produces a diagnostic.

Use `python -m echosight compare old.json new.json --output comparison.json` to explain changes in support and associate refined surfaces. This does not declare physical disappearance from missing echoes.

## Project evidence

- [Current state and next work](STATE.md)
- [Implementation charter](docs/CHARTER.md)
- [Module and data contract](docs/CONTRACT.md)
- [Acquisition and later physical acceptance](docs/ACQUISITION.md)
- [Signal model](docs/SIGNAL_MODEL.md), [inference equations](docs/INFERENCE.md)
- [Frozen evaluation criteria](evaluation/acceptance.json), [evaluation protocol](docs/EVALUATION.md)
- [Source and license provenance](docs/SOURCES.md)

Only original code, small evidence and permitted fixtures belong in Git. Generated recordings, downloaded datasets and environment packages belong in ignored `work/` or `.venv/` directories. No deployment or public submission is included.
