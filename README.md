# EchoSight

EchoSight is a local Python backend that turns lossless audio recordings into supported 3D reflector patches. A known sound probe, one fixed source and surveyed microphone positions drive the public recording → API/CLI → geometry → export/replay workflow. Version **0.2.0** adds reference-based material comparisons and contextual color distributions.

| Capability | What it returns |
| --- | --- |
| 3D mapping | Planes, supported meshes, reflection rays, dimensions and conditional uncertainty; partial, ambiguous and no-result states |
| Materials | Recording-derived spectral features compared with your reference profiles, or an explicit unknown result |
| Colors | A probability mixture of supplied material palettes, with missing probability mass retained; these are contextual predictions |
| Sessions | Immutable recordings, calibration/context revisions, asynchronous jobs, progress, cancellation and recovery |
| Integration | Local HTTP API, CLI, versioned JSON schemas, examples and raw-data export/replay |

The twelve-view room demo reconstructs six surfaces, including floor and ceiling. The separate material demo learns two synthetic reference filters and identifies three of six room surfaces; the others remain unknown. These are controlled software demonstrations. Harder synthetic and external measured-room cases still fail, and our iPhones/MacBook have not been physically validated. Sound does not measure optical color. [Evidence and remaining limits](STATE.md) stay visible.

**Verified:** [244 tests and both recording demos](evidence/reproduction-ab5ea75/) pass from a clean GitHub checkout. [Independent review](evidence/material-appearance/FINAL-ab5ea75-REVIEW.md) covers the delivered runtime.

## Install

Use macOS or Linux and Python 3.12 with compatible NumPy/SciPy wheels. This repository is private; clone with an account that has access. No paid services, API keys or runtime dataset downloads are required.

```sh
git clone --branch backend/implementation https://github.com/nazeeh111/EchoSight.git
cd EchoSight
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
```

Run all commands from the repository root with the virtual environment active. The package can run directly; `python -m pip install -e .` optionally installs the `echosight` command. Native Windows is unsupported because the local store uses POSIX file locking.

## Run

```sh
# Generate and process twelve simulated room recordings.
python -m echosight demo work/room --seed 1 --captures 12
python -m echosight inspect work/room/result.json

# Learn reference profiles, map an independent room and exercise unknown controls.
python -m evaluation.material_development --output work/material-demo
python -m echosight inspect work/material-demo/room-result.json

# Process a session with its original recordings.
python -m echosight process work/room/session.json --output work/reprocessed.json

# Start the local API; leave this terminal running.
python -m echosight serve --root work/store --port 8765
```

Use a new output directory for each generated demonstration. Results are JSON containing renderable geometry; this backend does not include a graphical viewer. The local API binds to loopback and is intended for trusted local clients.

The [installation and usage guide](docs/USAGE.md) covers acquisition, session creation, HTTP uploads/jobs, calibration, materials/colors, export/reload and troubleshooting with runnable commands. For your own materials, first collect known-reference recordings and build profiles with `material-reference`; the [material and appearance guide](docs/MATERIALS_APPEARANCE.md) explains the required inputs and limits. There is no built-in catalogue of assumed building materials or colors.

## Verify

```sh
python -m pip install -r requirements-test.txt
python -m unittest discover -s tests -v
python -m evaluation.run --output work/held-out
python -m evaluation.run --extended --output work/held-out-extended
```

HTTP tests bind temporary loopback ports. Scientific evaluations preserve every case and exit nonzero when their frozen criteria fail. The [evaluation guide](docs/EVALUATION.md) separates those comparisons from software tests and the controlled material development demo.

## Integrate

- [API routes and error contracts](docs/API.md)
- [Frontend handoff: geometry, materials, colors and state](docs/FRONTEND_HANDOFF.md)
- [JSON schemas](schemas/) and [actual frontend examples](examples/frontend/)
- [Session/data contract](docs/CONTRACT.md), [signal model](docs/SIGNAL_MODEL.md) and [inference equations](docs/INFERENCE.md)
- [Native iOS acquisition harness](acquisition/ios/README.md) and [later hardware acceptance](docs/HARDWARE_ACCEPTANCE.md)
- [Current state](STATE.md), [requirement coverage](docs/audit/COVERAGE.md) and [source/license provenance](docs/SOURCES.md)

Surface boundaries summarize observed support, not physical edges or safe free space. Material weights are conditional on the supplied library, not qualified physical confidence. Raw recordings and evidence remain available, and imported results are quarantined until recomputed. Experimental multi-source inference is a separate Python route, outside the public fixed-source API/CLI.

Generated recordings, environments and downloaded data belong in ignored `work/` or `.venv/`. Frozen failures and review evidence remain in Git so that limitations can be reproduced.
