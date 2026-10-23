# Software optimization, October 22, 2026

This receipt describes the first optimization pass. The subsequent [actual backend result viewer](RESULT_VIEWER.md) now provides an artifact-based bridge for CLI/API JSON; its separate verification adds sixteen tests. The animated room remains a distinct simulation.

Base: `10929a7`. Changes are local, uncommitted and unpushed. Frozen scientific evidence, thresholds, model assets and the inference algorithms are unchanged.

## Changes

- Recording export checks a manifest checksum against the same bounded byte snapshot that is decoded and preserved. Replacing a recording between the CLI and storage now fails before raw input or an archive is published.
- Echo replay retains its lines, markers, geometry and materials across animation frames. Switching sources releases obsolete resources. Replacing the phone array also releases old geometry, materials and label textures.
- Isolating an object cancels an earlier camera transition and orbit. Leaving exploration restores the complete scan scene, and clearing object selection clears its inspector and hint. Inspector toggles reflect actual state.
- Optional audio no longer blocks model readiness. Download timeout/failure preserves visual controls; late sound joins an active unmuted replay at its elapsed position. Stopped and expired replays remain stopped. Unavailable WebGL no longer breaks the motion control. Fullscreen rejection and labels are handled.
- CI includes Node.js 24 and ten JavaScript regression checks, using the bundled Three.js and controlled loading/audio services without npm dependencies.

## Verification

Final backend suite: **251 tests passed in 892.688 seconds**. Together with 17 demo-server and ten JavaScript tests, **278 automated tests passed**, plus the native capture-core checks and unsigned build. This runtime describes this local run; it is not a performance benchmark.

Passed checks already completed:

- Demo server: 17 Python tests, including local-model failures, malformed requests, request bounds, busy responses and localhost protections.
- JavaScript: ten checks covering stable replay resources over 300 animation updates, disposal, camera isolation, delayed audio, stopped/expired/muted playback, model readiness and audio failure.
- Three scene checks fail against the original source and pass after the corrections. The checksum replacement regression also reproduces the original defect.
- Independent review of the changed backend/demo paths found a late-audio issue, corrected and independently reproduced as fixed by the six audio/loading checks. No additional actionable finding remained in that bounded review.
- Actual browser: guided scan completes into the room explorer; object inspection/isolation/clear, reconstruction navigation, phone-count changes and mobile layout at 390×844 work. The installed local `qwen3:4b` answered a demo question; no browser warning/error was recorded during these checks.
- Native recorder: capture-core checks pass, including 50 stop/append races; unsigned Release build succeeds and is an arm64 executable with no code signature.
- JavaScript syntax and `git diff --check` pass.

The original sandboxed test attempt lacked loopback access and JSON Schema dependencies; it was interrupted and is not acceptance evidence. Final verification uses the pinned test dependencies and allowed temporary loopback sockets. The scientific Python environment is Python 3.12.14, NumPy 2.3.5 and SciPy 1.18.1.

## Reproduce

Install the pinned backend/test requirements in a Python 3.12 environment as described in the repository README, then run from the repository root:

```sh
python -m unittest discover -s tests -v
python -m unittest discover -s demo -p 'test_*.py' -v
node --experimental-vm-modules --test tests/demo-*.test.mjs
acquisition/ios/test-core.sh
acquisition/ios/build.sh
python3 demo/server.py --open
```

Node emits its normal experimental VM-module warning. The scene checks use actual bundled Three.js objects without a GPU; the audio checks use controlled services. They establish allocation/lifecycle behavior, not measured GPU speed, browser autoplay compatibility or real speaker output.

## Remaining product/scientific work

The visual demo uses a supplied room and simulated echoes; it still does not consume live acoustic-backend results. Measured-room recovery retains documented failures, material accuracy is unqualified, and physical iPhone/MacBook validation remains pending. Optical color comes from supplied context, not sound. No device was paired, no microphone was accessed, and no signing/installation was attempted. See [hardware acceptance](HARDWARE_ACCEPTANCE.md), [evaluation](EVALUATION.md) and [current state](../STATE.md). These software improvements do not establish a gap-free acoustic mapping product.
