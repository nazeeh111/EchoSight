# EchoSight demo and Echo Bot

From the repository root:

```sh
python3 demo/server.py --open
```

Or double-click `demo/Start.command` on macOS. Python 3.10 or later is enough for this demo; the acoustic backend has separate dependencies. The server binds only to `127.0.0.1`, defaults to port 8765, and needs no Python packages. Use `--port 8766` if the backend or another app already uses 8765.

## Local Echo Bot

Install [Ollama](https://ollama.com/download), start it, then install a compact Qwen model if you do not already have one:

```sh
ollama pull qwen3:4b
python3 demo/server.py --open
```

The server selects an installed local Qwen model. To choose a specific installed tag:

```sh
ECHO_BOT_MODEL=qwen3:4b python3 demo/server.py --open
```

Echo Bot explains concepts and suggests navigation. Suggested actions run only when clicked. The model runs through Ollama on `127.0.0.1:11434`; there are no API keys, cloud requests, shell tools, or access to your files. Chat history stays in the open page and is cleared on reload. Closing the panel keeps the current conversation. If Ollama or the model is unavailable, the scan and navigation shortcuts still work and the panel explains how to restore chat.

The first reply may take longer while Ollama loads the model. Stop dismisses a pending reply. An already-running local model request may finish on the server before another can begin. Responses can be mistaken; Echo Bot is a guide, not an acoustic measurement system.

## The demo

Start a scan for the 27-second sequence: pairing, calibration, a soft 4.5-second sound, then boundaries, objects, materials and color. Three animated scanning beams illustrate reconstruction. The interactive room explorer supports orbit, pan, zoom, camera presets, object inspection, hiding/isolation, and simulated echo replays.

Phones do not actually connect. No microphones are accessed. The displayed room is a prebuilt corrected model, not geometry inferred by this demo. Material/color labels and Medium/High confidence badges are illustrative. Every phone has 5–9 simulated echoes with a constant ±10° angle uncertainty. The [model provenance](MODEL.md) records what was corrected and what remains estimated.

The 420–2100 Hz sweep has smooth fades, a restrained −20 dBFS digital peak, and no clipped samples. Use the header mute button or system volume as desired. Keyboard: Space pauses/resumes the scan, M mutes, R resets the view. These shortcuts do not intercept typing inside Echo Bot.

## Static hosting

The visual demo also works on an ordinary static server. Echo Bot's local model endpoint requires `demo/server.py`; a static website cannot access a Qwen model on someone else's computer. No public Ollama endpoint is exposed.

## Checks

```sh
python3 -m unittest discover -s demo -p 'test_*.py' -v
```

The server tests use a fake Ollama endpoint and require no model downloads. Separate local browser checks verified real Qwen chat, explicit navigation, cancellation, desktop/mobile layout, and the original 27-second scan flow. The GitHub workflow runs backend/server tests and JavaScript syntax checks. Three.js is bundled under its [MIT license](vendor/THREE-LICENSE.txt). Ollama and model weights are separate installations and are not bundled in Git.
