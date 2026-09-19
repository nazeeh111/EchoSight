# Minimal iPhone capture harness

This is a small acquisition utility with Start, Stop and Export controls. It saves delivered mono Float32 samples without changing their values, plus timestamps, route/session observations and interruption evidence. It is **not yet qualified on an iPhone**. Its unsigned build and injected-buffer tests do not establish microphone behavior, timing accuracy, lack of OS processing, or raw ADC access.

The existing phyphox route remains available. This native route adds observable buffer timing and explicit session/interruption metadata without requiring a phone-accessible HTTPS server. Signing, installation and physical acceptance are separate pending work. There is no audio playback, network service, background-recording entitlement or mapping viewer here.

## Build and software checks

Run from the repository root on macOS with Xcode and the repository Python environment, including `requirements-test.txt` for the bridge's formal JSON Schema check. No extra Swift dependencies are required. These commands do not launch the app, request microphone permission, sign or install anything.

```sh
acquisition/ios/test-core.sh
acquisition/ios/build.sh > acquisition/ios/build-log.txt 2>&1
file acquisition/ios/build/Products/Release-iphoneos/EchoSightCapture.app/EchoSightCapture
codesign -dv acquisition/ios/build/Products/Release-iphoneos/EchoSightCapture.app
PYTHONPATH=. .venv/bin/python acquisition/ios/bridge.py
```

The `codesign` command deliberately reports `code object is not signed at all` and exits nonzero. The build uses a generic iOS destination, deployment target iOS 17.0 and project-local output/module-cache directories. It does not require a signing team. Verified with Xcode 27.0 (27A266a), iPhoneOS 27.0 SDK and Apple Swift 6.4. A different installed SDK has not been tested.

`test-core.sh` compiles only the Foundation/CryptoKit collector and exporter for macOS. It checks exact Float32 bit patterns including signed zero and subnormals, WAV counts, stop/append admission races, a partial final block, duration/block limits, missing/gapped/overlapping sample timestamps, host-clock regression/inconsistent elapsed time, cumulative drift, native tick scaling, nonfinite samples, format changes, interrupted export and retries after injected encoding/write failures. Fifty injected stop/append races are exercised per run. These checks do not execute AVAudioEngine or prove real-time callback performance.

`bridge.py` generates a fresh deterministic synthetic room session, supplies its first recording to the same Swift collector/exporter in 511-frame blocks, then independently decodes the resulting ZIP through the backend. It verifies exact sample values, ZIP members/CRC, WAV hash, continuity eligibility and equality of the complete extracted acoustic-observation objects. Clean and five invalid-timestamp packages exercise backend admission. Every generated manifest is checked against the published schema, including explicit JSON null for unavailable sample and host timestamps. To use an existing synthetic session instead:

```sh
PYTHONPATH=. .venv/bin/python acquisition/ios/bridge.py --session work/first-demo/session.json
```

The bridge requires a capture explicitly marked `simulated`, 48 kHz, at most 20 seconds and exactly representable Float32 samples. It rejects silent conversion. Injected manifests identify `injected-buffer-test`, `not-a-phone-measurement` and `no-physical-playback`. A generated manifest is contract evidence, not an actual phone capture.

Generated artifacts are ignored by Git:

- `build-log.txt`: unsigned iOS build log.
- `build/Tests/capture-core-tests`: macOS injected-data test executable.
- `build/fixtures/*.echosight.zip`: clean, interrupted and supplied-waveform packages.
- `build/bridge/report.json`: sample/observation equality and admission results.
- `build/bridge/native-tests.log`: Swift compilation/test output for that bridge run.
- `build/bridge/synthetic-input/`: generated WAV/session data and separate simulation truth; truth is never passed to processing.

## Runtime and recording contract

The app requests microphone permission only after Start. It asks AVAudioSession for record/measurement mode, 48 kHz and mono, then inspects the actual activated session and input-tap format. It accepts delivered mono Float32 at an integer 8–192 kHz; the downstream acoustic processor supports16–96kHz and at most30seconds, with probe high frequency at most0.45times the actual delivered rate. A retained export outside that processor range is not eligible for mapping. It does not convert unsupported formats, downmix, discard channels, normalize or resample. Measurement mode minimizes processing according to Apple; it does not promise no processing.

The collector preallocates at most 20 seconds of samples and 4,096 block records. A small lock serializes bounded memory copies with stop admission; file encoding and UI updates happen elsewhere. A callback arriving after stop cannot mutate the export. This implementation still allocates small timestamp/metadata values and uses a lock on the audio thread; deadline behavior requires device stress testing. Reaching the sample cap retains the planned partial final block and records `duration_limit`. Metadata exhaustion or adverse events preserve partial samples and make the shot ineligible for inference.

Route changes, interruptions, media-service changes, engine configuration changes and app backgrounding stop the shot. There is no automatic resume or concatenation. Original native sample/host timestamps remain decimal strings; sample gaps are never repaired. Initial/final route snapshots and notification observations are not continuous hardware instrumentation. Host ticks are one device's clock, not synchronized source or physical time.

The collector and backend independently compare host elapsed time with sample elapsed time for adjacent blocks and from the first block. Their conservative engineering bound is 1% of the sample interval plus two sample periods and two host ticks; a host tick coarser than one tenth of a sample period cannot qualify continuity. This catches inconsistent timestamps, including cumulative drift, but is not calibrated clock uncertainty or guaranteed detection of every sub-buffer discontinuity.

Source configuration, probe and playback-route IDs are supplied by the operator, or explicitly `unknown`. They do not authenticate playback or replace pose/source-clock calibration. Device metadata excludes the user's personal device name, serial and account information. Recorded input-port names come from the observed audio route.

Export writes an atomic `<capture_id>.echosight.zip` under the app's Documents/Captures directory, preserving earlier captures. The user can share the saved package through the ordinary iOS share sheet. The hash-bound WAV/manifest contract is [CONTRACT.md](CONTRACT.md). Backend admission rechecks original bytes, timestamps and route/event evidence. A clean manual stop does not establish that the whole probe was captured; acoustic quality checks still apply.

If encoding or saving fails, the app retains the immutable capture in memory and blocks new captures. A Retry save control retries the pending job; after encoding succeeds, retries reuse the exact ZIP bytes. This protects evidence from an ordinary write failure while the process remains alive. Process death before a successful durable save can still lose that capture; this utility does not yet provide recovery of an unfinished recording after a crash. UI-level failure/retry behavior still needs device verification; the shared save helper is tested with injected failures.

## Pending physical acceptance

No app launch, microphone capture, signing, installation, on-device route/interruption test or acoustic validation has been performed. Before using this route for an EchoSight demonstration, qualify device/OS-specific formats and timestamps, repeated sample continuity, interruption/background behavior, export recovery, source playback/calibration and known-geometry acoustic results under [the hardware acceptance procedure](../../docs/HARDWARE_ACCEPTANCE.md). Installation authority and a signing route must be resolved separately. UI compilation alone does not demonstrate usable phone operation.

Primary references: [Apple audio-session preferences](https://developer.apple.com/library/archive/qa/qa1631/_index.html), [Apple measurement mode](https://developer.apple.com/documentation/avfaudio/avaudiosession/mode-swift.struct/measurement), [Apple AVAudioTime](https://developer.apple.com/documentation/avfaudio/avaudiotime). The installed SDK declarations were also inspected. All harness code is original project code; no phyphox or other recorder implementation was copied.
