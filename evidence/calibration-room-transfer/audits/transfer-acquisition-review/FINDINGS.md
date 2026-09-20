# Rendered transfer acquisition audit

**Passed. No acquisition artifact obstruction found.** This is an independent read-only audit of the actual 56 rendered recordings, not another static protocol review or an inference run.

The frozen experiment is `work/frozen-transfer-runtime/work/calibration-room-transfer`, runtime `5d6423486be5fd448a4d7b42fbbaee264eb07c9c`, freeze SHA-256 `a995d28014c4c055003d34db193f5657a08d185a281d09ff1d7e667e5405da40`.

## Direct observations

- All **94 frozen input files** still match. All **48 original reference WAVs** in the main checkout and their isolated copies match the frozen digests. No original-reference regeneration or mutation is present.
- Render completion binds four manifests. Their complete member sets and every file hash match. There are **24 room mapping, 8 withheld room and 24 direct-only recordings**, exactly as planned. All 56 WAV file hashes and all 56 decoded PCM payload hashes are distinct. None of the new WAV hashes reuses a reference WAV.
- Every new WAV is mono, uncompressed signed PCM16, 48,000 Hz and 131,042 frames. Decoded peak magnitudes range from **0.1513413 to 0.4948271** of 32767. Peaks agree with the pre-quantization truth within half a quantization step; none clips.
- All six actual input sessions declare the same canonical probe, the exact synthetic frame, nominal source `[1.5, 1.5, 1.3]`, nominal speed **343 m/s**, and the prescribed uncertainties. The physical source `[1.54, 1.48, 1.31]`, effective speed **346 m/s**, path geometry, clock distortions and true receiver coordinates remain in separate truth artifacts. Session and capture fields pass strict allowlists; no truth file is referenced by a recording path.
- The four retained reference truth files and new query truth agree on source and effective speed. Frozen legacy and new generators use the same source FIR `[0.82, 0.13, -0.045, 0.025]` and receiver FIR `[0.94, 0.045, -0.018, 0.006]`. This is a matching synthetic source chain, not a physical source-route qualification.
- All new surveyed positions reproduce the declared independent query survey draw to `1e-14` m absolute tolerance. Retained reference surveys separately reproduce their original RNG draws. The **32 query survey groups** are disjoint from reference groups; mapping and withheld physical positions are disjoint from each other and all references. Each seed's direct-only control intentionally shares its twelve room mapping surveyed positions, with different audio.
- An independent image-source distance calculation reproduces every stored direct/reflected path delay with **zero observed numerical difference**. Room truth has seven paths per capture; null truth has only the direct path. Path amplitude law, single-tap reflection kernels, clock bounds and quantized peaks match the protocol.

## Interpretation limits

Survey independence is a construction assumption established by different deterministic random streams and distinct draws. An exact shared coordinate frame is stipulated; this experiment has no common physical survey registration error. The x/y calibration reference dependence has not been re-audited or altered.

The probe waveform fingerprint is a shared bound declaration and was not independently regenerated here. Source/receiver filtering is established by frozen generator provenance and retained metadata, not recovered independently from measured waveforms. This audit performs no waveform synthesis, deconvolution, optimization, geometry mapping or timing measurement. It establishes artifact integrity and permitted input separation, not successful transfer, generalization, physical device suitability or material identification.

## Reproduce

From the main backend repository:

```sh
.venv/bin/python work/transfer-acquisition-review/audit.py \
  --main . \
  --runtime work/frozen-transfer-runtime \
  --output work/transfer-acquisition-review/receipt.json
```

The executable audit imports only standard-library utilities and NumPy. It reads raw artifacts and writes its receipt only. The receipt contains all 56 WAV and PCM-payload SHA-256 values. PCM-payload SHA-256 here hashes the decoded PCM byte payload only; it is deliberately not labeled the application's canonical waveform fingerprint.

Artifacts: [audit.py](audit.py), [receipt.json](receipt.json).
