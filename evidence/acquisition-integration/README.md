# Native acquisition integration evidence

This checkpoint implements exact delivered Float32/native-manifest import and a minimal unsigned iOS capture utility. It is software and simulation evidence, with no device recording or physical validation.

An isolated archive of eb1c267 plus only the listed acquisition/integration overlays passed **136 tests in32.513s**. [Source manifest](tested-source.json) pins every overlay byte; [full log](tests.txt) includes actual loopback upload→raw processing→six independent simulated room surfaces, export/reload, malformed/resource failures, clock inconsistencies, crash/cancellation and formal offline schemas. Ongoing experimental path-alternative edits were excluded. Metadata-only state/evidence updates after execution do not change tested runtime.

[Native verification](../../acquisition/ios/VERIFICATION.md) pins the unsigned arm64 build and injected Swift tests, including save-failure retries. [Bridge](native-bridge.json) preserves93,120 exact delivered sample values and the complete extracted observation through Swift ZIP export and backend import. No AVAudioEngine runtime was exercised. [Route comparison](route-comparison.md) records why one native route was selected over adding a browser recorder.

The [independent acquisition review](../independent-acquisition-physics-review.md) reproduced and closed a host/sample timestamp-consistency defect. Its hashes predate the separate native pending-save repair; that repair has injected encode/write retry tests and is awaiting identified-commit review. The broad clock gate does not detect every sub-buffer discontinuity or synchronize devices.

The first new HTTP test failed because the test client supplied a server-derived sample_rate_hz as writable capture metadata; restricting it to the documented writable fields fixed the test. Formal schema checks first exposed unresolved cross-schema IDs; published references now resolve through canonical registered IDs without network retrieval. An initial snapshot test invocation used the wrong relative Python path and never ran; the successful invocation above ran from the isolated snapshot. No scientific acceptance threshold changed.

Runtime installation uses requirements.txt. Full checks additionally install requirements-test.txt. Clean remote reproduction and immutable integrated review follow this checkpoint. Actual recording/OS processing/routing/signing/install and all physical accuracy await the frozen hardware plan.
