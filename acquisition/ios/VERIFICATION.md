# Native acquisition software evidence

This record concerns software checks only. No iPhone recording, microphone permission request, app launch, signing, installation or deployment occurred.

## Checked implementation

The native source is `Sources/CaptureCore.swift`, `Sources/NativeRecorder.swift` and `Sources/App.swift`; macOS injected tests are `Tests/CoreTests.swift`. See [README.md](README.md) for reproducible commands and remaining limitations. Generated logs and recordings stay under ignored `build/`; the unsigned build log is ignored `build-log.txt`.

[verification.json](verification.json) records the checked source SHA-256 hashes, tool versions and concise results without machine-specific paths or generated binary data.

Observed with Xcode 27.0 (27A266a), iPhoneOS 27.0 SDK, Apple Swift 6.4, and the repository NumPy/SciPy environment:

| Check | Observed result |
| --- | --- |
| Generic iOS Release build, signing disabled | Build succeeded; arm64 Mach-O app executable |
| Signature inspection | Not signed, as intended |
| Shared collector/exporter injected tests | Passed, including 50 stop/append races and exact Float32 bit checks |
| Native elapsed-clock checks | Correct fractional Mach tick scale accepted; nonmonotonic/inconsistent/coarse clocks and cumulative drift rejected |
| Save retry helper | Injected encoding and disk-write failures retained evidence; successful retry reused identical encoded bytes |
| Fresh synthetic supplied-waveform bridge | 93,120 frames at 48 kHz, all decoded sample values equal to input |
| Acoustic extraction before/after native export | Entire observation object equal; five echo candidates |
| Backend package admission | Clean exact and supplied waveform eligible; gap, overlap, host regression, inconsistent elapsed-time and invalid/missing timestamp controls ineligible |
| Published native manifest schema | Every generated manifest valid; unavailable timestamps explicitly encoded as JSON null |

The bridge report is `build/bridge/report.json`; its native compilation/test log is `build/bridge/native-tests.log`. The unsigned build log ends with `BUILD SUCCEEDED`. The compiler never executes AVAudioEngine; injected tests call the collector/exporter directly.

## Problems encountered and resolved

- Xcode initially attempted a default global module cache. Explicit project-local derived-data, module-cache and SDK-stat-cache paths fixed the build without changing global configuration. The initial log remains in `build/initial-build-log.txt`.
- The backend independently rejected a clean fixture whose normal stop detail was empty. Normal stop now always has a nonempty event detail.
- Independent review found that the nominal exact fixture used a 1 ms host interval for four 48 kHz samples. The fixture now uses the correct interval, and native/backend elapsed-clock checks reject materially inconsistent monotonic timestamps. Both checks retain the engineering-bound limitation documented in the README.
- Coordinator review found failed saves could be overwritten by starting a new capture. A pending save now retains evidence and blocks Start until a successful Retry save. Crash recovery before durable save remains unsupported.
- Independent review found Swift's synthesized optional encoding omitted unavailable timestamps, although the published contract requires explicit null. CaptureBlock now encodes those keys explicitly; injected Swift and cross-language schema checks cover this case without changing WAV samples.

These findings improve the contract and implementation; they are not evidence that a phone honors requested rates, provides raw ADC samples, avoids audio processing, or achieves acoustic geometry accuracy. Physical acceptance remains pending.
