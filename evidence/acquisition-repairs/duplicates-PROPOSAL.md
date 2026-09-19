# Exact waveform independence audit

## Reproduced software defect

One synthetic 48 kHz recording from development seed 1701 was reused at twelve distinct declared receiver positions. Positions were deliberately chosen on a constant bistatic excess-delay locus. The purpose is to expose evidence accounting, not to claim those positions were measured or that the resulting surfaces exist.

`probe.py` imports through SessionStore and uses the real recording-to-geometry pipeline. PCM WAV, PCM WAV with an extra legal JUNK chunk and losslessly equivalent Float32 WAV have three distinct container hashes but identical decoded samples. All twelve observations were accepted; the mapper returned three surfaces with status `partial`. Archive export, reload and fresh processing returned the same three surfaces and twelve accepted observations. Full outputs are `result.json`, `replay-result.json`, summarized in `report.json`.

`api_probe.py` adds the same Float32 WAV inside a native-format ZIP with a correctly hash-bound injected synthetic manifest. Four different container hashes again produced twelve accepted observations and three surfaces through real local HTTP upload/job/result endpoints. Native continuity admission was eligible. Evidence: `http-report.json`, `http-result.json`, `http-log.txt`. This package is synthetic repackaging, not phone acquisition. Its manifest template comes from the native deterministic fixture, and no microphone ran. The local listener required a scoped sandbox escalation, which was approved.

The ordinary pipeline keeps container hashes for provenance but does not reject these reused samples as independent. Calibration and controlled acquisition compare container hashes; exact waveform repackaging therefore also defeats that narrower identity test. Multisource raw-entry duplication likewise needs a cross-session check. A separate native-eligibility bypass in multisource was reported to the coordinator and is owned by another implementer.

## Agreed minimal policy

Retain every original container unchanged. Compute a separate versioned canonical waveform fingerprint over the decoded mono sample rate, frame count and little-endian Float64 samples. Normalize signed zero only in the hash representation, since positive and negative zero carry the same numeric audio evidence; original sample bits remain preserved. Hash bounded chunks to avoid an unnecessary full-size allocation. Invalid/nonfinite or unsupported data remain subject to existing decoder checks.

Reject every member of an exact-equivalent waveform group from inference, rather than arbitrarily selecting one of several conflicting pose declarations. Keep a diagnostic listing the group and its original container identities; do not erase recordings. Apply grouping before inference across an ordinary session, across all source sessions in a scene bundle, and across the relevant calibration/control independence sets. Recompute identity from the same immutable input snapshot as decoding; do not trust user-provided hashes.

This is exact content equivalence, not a claim about user intent or proof that independently captured silence cannot be identical. Such silence already cannot establish geometry; preserve it as a no-result/control record. Conversely, different fingerprints do not establish physical independence. No amplitude normalization, approximate matching, offset matching, resampling or near-duplicate heuristic is proposed.

## Verification needed with implementation

- Same bytes assigned to distinct poses: preserve raw, reject all duplicates, no invented surfaces.
- PCM metadata padding, exact Float32 representation, native ZIP and exact-value phyphox repackaging: same content fingerprint despite different byte hashes.
- Positive/negative zero hash equivalence with original bits untouched; different sample values/rates/lengths remain different.
- Direct pipeline, real HTTP processing, export/reload and cross-source processing use the same grouping semantics.
- Calibration/control jobs cannot count repackaged copies as independent training, held-out or epoch evidence.
- Unique recordings still produce their prior results; duplicated silence remains an explicit no-result rather than a malformed-input crash.

No main implementation was edited for this audit. The coordinator owns storage/pipeline/calibration/controlled fixes; the evaluation owner owns multisource integration. The standalone proof uses generated development recordings, not frozen evaluation answers.
