# EchoSight

**hear space. see sound.**

EchoSight combines an acoustic research backend with an interactive room demo. The backend processes lossless recordings into supported 3D surface patches. The room demo is one of the examples we built and tested: a 27-second simulated scan followed by an explorable room model.

| Part | Purpose |
| --- | --- |
| [Room demo](demo/) | Animated phone connection, sound emission, reconstruction, room exploration and echo replay. Uses a supplied 3D model and illustrative estimates, without real phone connections or backend processing. |
| [Acoustic backend](docs/USAGE.md) | Python CLI and local HTTP API for recording import, calibration, geometry, reference-based material comparisons and export/replay. |
| Echo Bot | Optional local Qwen assistant in the demo, served through Ollama. It does not perform acoustic measurements. |

## Room examples

- [Interactive room demo](demo/): the tested scan experience and explorable room model.
- [Room 2 Blender animation](examples/rooms/room_2_final_animated.blend): an additional room example. Download the file and open it in Blender to explore the scene and play its animation. The supplied file is preserved unchanged and is available here on GitHub only.

## Open the demo

From the repository root:

```sh
python3 demo/server.py --open
```

The local server uses Python's standard library. The demo does not require the backend's scientific dependencies. Its confidence labels, echo directions and material/color estimates are simulated. [Model provenance](demo/MODEL.md) describes the room asset.

To enable Echo Bot, start [Ollama](https://ollama.com/download) locally, then install a compact Qwen model if needed:

```sh
ollama pull qwen3:4b
ECHO_BOT_MODEL=qwen3:4b python3 demo/server.py --open
```

The scan and room explorer work without Ollama. No cloud API key is required. [Demo controls, setup and troubleshooting](demo/README.md).

## Run the backend

Use macOS or Linux and Python 3.12 with compatible NumPy/SciPy wheels. Native Windows is unsupported because the local store uses POSIX file locking. The default branch is `backend/implementation`.

```sh
git clone --branch backend/implementation https://github.com/nazeeh111/EchoSight.git
cd EchoSight
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt

# Generate and process twelve synthetic recordings.
python -m echosight demo work/room --seed 1 --captures 12
python -m echosight inspect work/room/result.json

# Start the separate local recording API.
python -m echosight serve --root work/store --port 8766
```

Use a new output directory for each generated backend demonstration. The public recording workflow uses one fixed sound source and surveyed microphone positions. Its results are JSON geometry and evidence; the animated demo does not consume them. See [installation and usage](docs/USAGE.md) for real recording inputs, calibration, material references and replay.

## Checks

With the virtual environment active:

```sh
python -m pip install -r requirements-test.txt
python -m unittest discover -s tests -v
python -m unittest discover -s demo -p 'test_*.py' -v
python -m evaluation.run --output work/held-out
python -m evaluation.run --extended --output work/held-out-extended
```

HTTP tests need temporary loopback ports. Scientific evaluations exit nonzero when their frozen criteria fail; passing software tests does not establish physical accuracy. [Evaluation guide](docs/EVALUATION.md).

## Scientific status

Controlled synthetic demonstrations recover room surfaces. Harder synthetic cases and external measured-room replays retain failures. Physical validation with our phones and laptop remains pending, and full scientific acceptance has not been met. The [current state and evidence](STATE.md) preserve those results.

Surface patches describe observed acoustic support, not complete wall edges or safe free space. Backend material comparisons require supplied reference profiles and can return unknown. Sound does not measure optical color; backend colors use supplied contextual palettes. The demo's visual estimates are separate from those research outputs.

## Documentation

- [Documentation index](docs/README.md)
- [API routes and errors](docs/API.md), [frontend integration contract](docs/FRONTEND_HANDOFF.md), [schemas](schemas/) and [backend result examples](examples/frontend/)
- [Materials and appearance](docs/MATERIALS_APPEARANCE.md), [hardware acceptance](docs/HARDWARE_ACCEPTANCE.md) and [source/license provenance](docs/SOURCES.md)

Keep generated recordings and local experiments in ignored `work/`. Preserve frozen scientific results and their failure evidence in `evidence/`.
