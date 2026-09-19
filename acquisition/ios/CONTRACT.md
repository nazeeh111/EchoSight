# EchoSight native delivered-audio capture v1

Implementation contract agreed before the harness. This is a minimal acquisition utility, not a mapping frontend. Original delivered samples and device/session observations are evidence; neither measurement mode nor a lossless container proves raw ADC access, absence of OS processing, correct source geometry or hardware accuracy. No microphone use, signing, installation or deployment is part of software verification.

## Export container

One ZIP named `<capture_id>.echosight.zip`, with exactly `recording.wav` and `manifest.json` at its root. ZIP32 stored entries are sufficient; standard CRC32. No directories, encryption or links. At most64MiB compressed and expanded total; manifest at most1MiB. WAV is little-endian RIFF/WAVE format3, one channel, IEEE Float32, exact delivered sample rate (integer8–192kHz), one fmt chunk and one data chunk. Preserve delivered finite Float32 values, signed zero and subnormals bit-for-bit in the WAV. No quantization, normalization, gain, resampling, downmix or channel discard. Reject unsupported tap formats rather than silently convert. A20second recorder cap keeps software buffers bounded; no background recording promise.

Manifest keys:

- `schema_version`: `"1.0"`; `format`: `"echosight_capture"`; `capture_id`: opaque1–80character ID; `recording_sha256`: lowercase SHA256 of exact recording.wav bytes.
- `sample_encoding`: `"ieee_float32_le"`; `sample_rate_hz`: actual WAV rate; `channel_count`:1; `frame_count`: exact sample count.
- `recorder`: `{name,version}`; `acquisition_layer`: `"ios_audioengine_delivered_buffers"`.
- `device`: `{model,os_version}`. No device name, advertising ID, serial, account or personal identifier.
- `source_declaration`: `{configuration_id,probe_id,route_id}`; operator-supplied bounded strings. Unknown is explicit; these do not authenticate playback, route or physical source rate.
- `session`: `{category,mode,preferred_sample_rate_hz,activated_sample_rate_hz}`; exact observed values after activation. Requested rate is not substituted for actual rate. `mode` is `"measurement"`.
- `route_initial`, `route_final`: objects with `input_port_type`, `input_port_name`, `input_channel_count`, `input_sample_rate_hz`. Declared route snapshots are not continuous route instrumentation.
- `host_timebase`: `{numer,denom}` positive Mach timebase integers. Tick differences times numer/denom are nanoseconds on this device's host clock, not a synchronized physical/source clock.
- `continuity`: `{status,reasons,blocks}`. Status is `complete`, `interrupted` or `unverified`; reasons bounded string list. Each block is `{sequence,first_frame,frame_count,sample_time_valid,sample_time,host_time_valid,host_time}`. Sequence starts0; first_frame is accumulated output offset; frame_count is positive. Native signed sampleTime and unsigned hostTime are decimal strings (or null when invalid) to avoid JSON/JavaScript integer rounding. At most16384blocks. Preserve original timing, never repair gaps by concatenating and relabeling timestamps.
- `events`: up to256 objects `{type,at_frame,detail}`. at_frame is the number of retained delivered frames when the event was observed. Detail is a bounded string, not a claim of exact ADC event timing. Normal stop is `user_stop` or `duration_limit`; adverse events include `interruption`, `route_change`, `engine_configuration_change`, `media_services_lost`, `media_services_reset`, `buffer_overrun`, `format_changed`, `timestamp_invalid`, `nonfinite_samples`, `capture_error`.

## Collection, interruption and admission

Permission is requested only after the user presses Start. Use AVAudioSession record/measurement with preferred48kHz and mono input, then inspect actual activation/tap format. No voice-processing unit is selected by this harness. Keep one stationary route per shot. Any adverse event stops capture and preserves a partial export; never silently resume/concatenate. Buffer handoff and total retained samples are bounded. Stop/export must wait for admitted buffers to finish or mark an overrun/truncation; a UI update must not block the audio callback. A clean manual stop does not prove the full probe was captured; backend pilot checks still apply.

Backend reads the WAV and manifest from one immutable ZIP byte snapshot, verifies SHA/rate/count/format, and independently checks block coverage, native sampleTime adjacency, timestamp validity, monotonic hostTime, host/sample interval consistency, route equality and adverse events. Structurally malformed or hash-inconsistent packages reject import. Well-formed interrupted/unverified packages remain preserved, with diagnostics and `processing_eligible=false`; they cannot silently enter geometry fitting. Import summary stores manifest SHA, actual format and summarized continuity; full block/event evidence remains in the immutable ZIP. Raw WAV without a manifest remains accepted with continuity unverified.

No own-device physical validation flag becomes true. CLI/API/export/reload all reuse the same decoder and original package. Physical source clock, acoustic-center survey, direct-path identity and transducer phase remain independent calibration requirements.

## Verification before physical acceptance

Use injected Float32 buffers and timestamps to check exact WAV samples/hash, partial final blocks, gaps/overlaps/invalid clocks, format/route changes, queue bounds, nonfinite data, interruption/stop/export races and non-microphone determinism. Compile an unsigned generic iOS app using installed SDK and project-local derived data; inspect executable/package metadata without launching or signing. Feed deterministic harness packages through backend import and recording processing. Later installation/signing and actual phone continuity/route behavior remain explicit pending steps under docs/HARDWARE_ACCEPTANCE.md.

Host/sample consistency is an engineering admission gate: adjacent and first-to-current blocks must agree within1% of elapsed sample time plus two sample periods and two host ticks. Host tick resolution coarser than0.1sample period is unqualified. This deliberately broad bound is not probability calibration or guaranteed detection of every discontinuity, and does not equate phone host time with the source clock. Raw timestamps are preserved; none are repaired.
