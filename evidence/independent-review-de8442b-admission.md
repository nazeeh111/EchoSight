# Independent admission repair review

Reviewed immutable commit **de8442b2dd088c036d2b92eaeaf29a1273785795**, extracted with `git archive` into `work/review-de8442b-snapshot`. No implementation, tests, schemas, or Git state were changed. All 92 Python and Swift source files in the snapshot were byte-compared with the commit; SHA-256 values are retained in `work/review-de8442b-source-hashes.json`. Byte verification establishes snapshot identity, not review coverage.

## Result

**No remaining P1/P2 found in this bounded follow-up.** The three findings from `work/review-78cb796.md` are closed by rerunning their original reproductions against this snapshot. The new exact decoded-waveform reuse guard also passed independent probes across ordinary mapping, raw multisource processing, calibration, controlled comparison, and export/import replay.

## Code inspected

Read the repair changes and their surrounding call paths in `echosight/storage.py` (format decoding, evidence snapshot, waveform digest, duplicate-group rejection), `pipeline.py` (evidence propagation and pre-inference admission), `calibration.py` (reference identity admission), `controlled.py` (native/outer control reconciliation and waveform identity), `multisource.py` (raw entry admission only), and `acquisition/ios/Sources/CaptureCore.swift` (explicit optional timestamp encoding). Read the relevant acquisition contract/schema expectations, targeted regression sources in `tests/test_acquisition.py`, `test_controlled_native.py`, `test_waveform_identity.py`, `test_calibration.py`, `test_schemas.py`, and only the two raw-admission regression methods from `test_path_alternatives.py`. New physical path-alternative mathematics is outside this review.

## Original defect reproductions

1. **Interrupted native recordings admitted by raw multisource processing: closed.** The retained physical two-plane, 32-native-package reproduction now reports `calibration_needed`, zero surfaces, and 32 rejected observations. Package hashes and acquisition evidence remain attached. The ordinary pipeline control rejects its eight interrupted packages and returns no result. Reproduction and output: `work/review-de8442b-native-multisource-probe.py` / `.json`. The original 78cb failure evidence is preserved separately.

2. **Contradictory inner native controls overridden by outer epoch declarations: closed.** The same actual 16-package controlled-comparison reproduction still identifies four changed receiver views for matching declarations. Changing the inner source configuration, receiver input route, or source playback route now returns `inconclusive`, no receiver change evidence, and `native_controls_contradict_protocol`; contradiction details remain visible. Reproduction and output: `work/review-de8442b-controlled-probe.py` / `.json`. The additional source tests cover recorder/device/session-format differences and missing native coverage.

3. **Swift nil timestamp omission violates manifest schema: closed.** Compiled the original reviewer Swift reproduction against the repaired core. Its actual ZIP now contains explicit `sample_time: null` and `host_time: null`, passes the published manifest schema, and remains ineligible for processing. The original old package, whose timestamp keys are absent, is now rejected with `timestamp field required; use null when invalid`. Evidence: `work/review-de8442b-invalid-timestamps.zip` / `.json`.

## Independent consequential checks

`work/review-de8442b-identity-probe.py` and its JSON output retain checks beyond simply running the new regression tests:

- Independently serialized 262,147 decoded values with Python `struct.pack`, crossing both digest chunk boundaries. Included big-endian input, signed zero, and a Float64 subnormal. The digest agrees with independent serialization, source bits remain unchanged, and a one-ULP change produces a different digest.
- A clean twelve-view simulated room retains six planes and twelve distinct waveform identities. Repackaging one recording into Float32 at another capture's distinct pose rejects **both** group members, preserves the ten other observations, and gives the same decisions with reversed capture order. Raw byte hashes differ; decoded identities agree. Forged caller-supplied waveform hashes do not replace the decoder-computed identity.
- A clean actual-audio calibration fixture produces a calibration proposal. Copying one held-out recording into another held-out pose using a different container rejects both copied members and rejects calibration, despite distinct raw hashes.
- Regression tests independently executed from the snapshot cover five equivalent containers (PCM16, repacked PCM16, Float32 WAV, native ZIP, phyphox CSV), replay of exported/imported recordings with all twelve copies rejected, controlled comparison using repackaged repeated audio, and cross-source copies with 32 distinct raw hashes but eight decoded waveform groups. The raw multisource tests also exercise nonfinite Float32, wrong raw hashes, eligible package pass-through, and preservation of all other per-capture decisions when one package is malformed.

The identity definition includes nominal sample rate and sample count and canonicalizes signed zero. It is an exact decoded-value test. Different hashes do not establish independently acquired evidence, and this review makes no near-similarity or resampling detection claim.

## Executed checks

- `python -m unittest tests.test_acquisition.AcquisitionTests tests.test_controlled_native tests.test_waveform_identity tests.test_calibration tests.test_schemas -v`: **22 tests passed** (9.313 seconds).
- The two methods `PathAlternativeTests.test_native_raw_entry_rejects_interruption_and_preserves_evidence` and `PathAlternativeTests.test_exact_decoded_copies_across_source_sessions_reject_every_container`: **2 tests passed** (1.362 seconds). No path-model tests or mathematics are included in this conclusion.
- `acquisition/ios/test-core.sh`: passed exact Float32/WAV/ZIP preservation, counts/timestamps, interruption transitions, limits, invalid samples, and 50 stop/append races. Output: `work/review-de8442b-native-tests.txt`.
- `acquisition/ios/bridge.py`: passed actual Swift-package/backend integration, exact valid capture, explicit-null invalid times, and rejection controls for gaps, overlap, host regression/inconsistency, and invalid timestamp. Output: `work/review-de8442b-native-bridge.txt`.
- All three original reviewer reproductions and the new identity probe completed successfully with the changed expected rejection outcomes above.

## Limits

This is an admission-boundary repair follow-up, not a fresh complete backend review. HTTP routing, storage crash/recovery, a full unsigned app build, broader frozen scientific acceptance, and the complete test suite were not repeated here. The coordinator's full-suite result is not used as independent evidence. The updated Swift core was compiled and exercised, but no microphone, AVAudioEngine runtime, signing, installation, or app launch was used. Acquisition metadata remains declared evidence rather than proof of physical setup. Previous held-out scientific failures and the original 78cb reproductions remain preserved; these admission fixes do not establish physical validity or general scientific performance.
