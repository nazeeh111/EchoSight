# Independent assembled acquisition review: 78cb796

Reviewed **78cb7963b8bbe5ef822c199ba857fde2d5529cf1**, using an immutable `git archive` snapshot at `work/review-78cb796-snapshot`. All snapshot `echosight/*.py` and `acquisition/ios/Sources/*.swift` bytes were verified against that commit after execution. No implementation changes or Git writes were made. No app launch, microphone access, signing, installation, simulator run or device operation occurred.

**Three P2 findings; no P1 established.** The Float32/storage/ordinary-pipeline path and injected native checks passed the checks below, but two other geometry consumers fail to enforce the new evidence consistently, and a native interrupted-export case violates the published schema.

## P2: experimental multisource bypasses native acquisition rejection

**Location:** `echosight/multisource.py:424–428`.

The compatibility `read_recording_snapshot` interface now decodes native packages but discards acquisition evidence. `process_scene_bundle` still calls that interface and sends the decoded samples straight to `process_recording`, without checking `processing_eligible`. The ordinary pipeline correctly uses the evidence snapshot and withholds interrupted input.

**Executed reproduction:** `work/review-78cb796-native-multisource-probe.py` independently renders 32 recordings at four source poses/eight receivers for two planes, then wraps every recording in an actual Float32 native ZIP with an `interruption` event. Every package is structurally valid and its sample bytes/hash/manifest agree. The ordinary pipeline rejects all eight observations in its first-source control and returns no geometry. The experimental multisource raw entry marks **all 32 observations `ok` and publishes two planes**. The resulting offsets agree with the simulated geometry, which does not excuse accepting the interrupted records.

Evidence: `work/review-78cb796-native-multisource-probe.json`.

**Action:** consume `read_recording_evidence_snapshot` at this raw entry, preserve acquisition/input evidence and exact package digest, and apply the same eligibility rejection before signal extraction. This is a recording-admission integration defect, not a review of the separately evolving path-alternative mathematics. The native contract explicitly says interrupted/unverified packages remain preserved but cannot silently enter geometry.

## P2: controlled claims ignore contradictory native route/source evidence

**Location:** `echosight/controlled.py:229–239` (quality/hash admission goes directly to response comparison), in composition with `_load`'s outer protocol checks.

The outer protocol requires unchanged source/configuration/route controls, but native manifests now contain additional independently preserved declarations and observed route/session snapshots. Those are retained in each epoch's observations yet never checked across epochs before a repeatable-change claim. A matching outer declaration silently wins over a known contradiction in the recording evidence.

**Executed reproduction:** `work/review-78cb796-controlled-probe.py` converts the four-view moved-reflector development recordings into actual native Float32 ZIPs. The matching control produces repeatable unlocalized acoustic change. Keeping every outer epoch control unchanged, separately mutate both B epochs' manifests to declare:

- a different source configuration ID;
- a different input route (`USBAudio` and a different input name, with matching initial/final routes within that recording);
- a different source playback-route ID.

Each package remains individually eligible. **All three contradictory protocols still return `repeatable_acoustic_change_unlocalized`, four changed views, and only `controlled_acoustic_difference` diagnostics.** The contradictory fields are present in nested acquisition evidence, so the result is not caused by an unreadable manifest or missing information. Full evidence is in `work/review-78cb796-controlled-probe.json`.

**Action:** before comparing responses, check available native evidence for cross-epoch contradictions per stationary device and explicit conflicts with the corresponding outer source declaration. Return inconclusive with the conflicting fields/evidence. Do not equate a recording-route identifier with an input port name, or a source playback route with a receiver route; compare the appropriate field namespaces. Legacy input without native metadata remains a separate lack-of-evidence case. Metadata is still a declaration, not authentication, but its known contradictions cannot be ignored under the controlled protocol's stated controls.

## P2: invalid native timestamps export missing fields instead of required nulls

**Location:** `acquisition/ios/Sources/CaptureCore.swift:4–11`; schema requirement at `schemas/capture-manifest.schema.json:261–268`.

Swift's synthesized `Codable` encoder omits nil optional `sample_time`/`host_time` fields. The capture contract explicitly requires null for an invalid timestamp, and both properties are required by the published schema. Consequently, the normal partial-export path for missing native timestamps creates a package that fails the project's own contract.

**Executed cross-language reproduction:** compiled the unchanged `CaptureCore.swift` with `work/review-78cb796-invalid-timestamps.swift`, injected three finite samples with missing sample/host timestamps, and exported a real ZIP. Its block contains both validity booleans `false` but neither timestamp property. The installed JSON Schema validator reports:

- `'sample_time' is a required property`;
- `'host_time' is a required property`.

The backend decoder preserves this package and marks it ineligible, so this is **not** a demonstrated false-geometry admission. It breaks interchange for schema-validating clients precisely when interrupted evidence should remain usable for audit. Artifact: `work/review-78cb796-invalid-timestamps.zip` and `.json`.

**Action:** explicitly encode JSON null for missing timestamps, retaining the validity flags and interruption reason. Add a cross-language schema check of an actual Swift export with invalid timestamps. The existing Swift test checks an in-memory nil, while existing schema tests create Python manifests with explicit null; those tests do not cover this composition.

## What was independently checked

Read the original charter and native capture contract, complete new `echosight/acquisition.py`, changed storage/pipeline sections, native collector/exporter/pending-save helper, AVAudioEngine wrapper, minimal UI state wiring, project/build settings, bridge, acquisition/schema tests and relevant API/acquisition documentation. Inspected controlled and multisource raw-entry composition only where necessary to follow the new recording evidence; ongoing path-alternative changes were excluded.

### Preserved samples and ordinary backend admission

The decoder widens little-endian finite Float32 values to Float64 without quantizing them; the original waveform/package bytes are separately preserved and hashed. Native packages bind their WAV hash, rate/count/format and manifest hash to one immutable package snapshot. Code and tests independently check block coverage, native sample adjacency, validity flags, host monotonicity/interval consistency, route changes and adverse events. Interrupted packages remain importable evidence but the ordinary pipeline rejects their observations before geometry.

Executed eight acquisition unit tests, three schema tests and the loopback acquisition HTTP test: **12 Python tests passed**. These cover exact Float32/signed-zero sample round trips and original bytes, malformed/hash/resource failures, interruption override resistance, twelve-recording geometry through native upload, malformed upload without a phantom capture, original package export/reload and actual pipeline/schema outputs. The temporary loopback test used native approval.

### Native collector, pending save and unsigned compilation

Ran `acquisition/ios/test-core.sh` against the snapshot. It passed exact Float32 bit/WAV/ZIP checks (including subnormals), bounds, partial final blocks, invalid clocks/format/samples, interruptions, 50 injected stop/append races, and encoding/write-failure retries. The shared pending-save helper retains the encoding closure after encode failure and retains the exact encoded data after write failure; repeated persistence uses identical bytes. Source inspection confirms Start is blocked while a save is pending and Retry save clears pending state only after success. This is an injected helper/state inspection, not execution of UIKit/AVAudioEngine failure/retry behavior.

Ran `acquisition/ios/build.sh`: **unsigned generic iOS build succeeded**. Independently inspected the product as an arm64 Mach-O executable; `codesign -dv` reports it is not signed. No device or simulator destination was launched. Logs: `work/review-78cb796-native-tests.txt` and `work/review-78cb796-native-build.txt`.

Ran the native bridge independently. Its Swift exporter processed **93,120 synthetic samples at 48 kHz**. Python import preserved exact sample values and complete extracted observation objects, including five echo candidates. The clean control remained eligible; gap, overlap, host regression and host/sample inconsistency controls were ineligible. Report/log: `work/review-78cb796-native-bridge.txt`; generated packages and bridge report are inside the snapshot's ignored `acquisition/ios/build/` directory.

### Limits

The unsigned build and Foundation/CryptoKit injected collector establish compilation and selected software behavior. They do not establish AVAudioEngine callback deadlines, actual permission/route notifications, OS processing, mic timestamp validity, hardware continuity, audio fidelity, UI recovery on a phone or acoustic accuracy. Pending-save evidence survives ordinary encode/write failures only while the process remains alive; pre-save process death remains documented data-loss exposure. No new hardware guarantee is inferred from measurement mode, a WAV container, a hash or internally consistent recorder declarations.

No broad backend suite, frozen acceptance rerun, new physical measurement, or scientific path-model review was performed. The three reproductions are saved independently of the live fixes; this report applies only to the identified immutable commit.
