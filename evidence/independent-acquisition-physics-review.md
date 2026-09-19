# Independent acquisition correctness review

Scope: uncommitted acquisition importer, storage/pipeline integration, native collector/exporter and iOS recording lifecycle. The reviewer did not implement these files. Main source was read-only in this review; scratch probes live under `acquisition-review/`. No microphone, app launch or signing was used. Native tests compile and execute only the injected-buffer collector, not AVAudioEngine. The local HTTP test was not run by this reviewer.

## Consequential finding and resolution

**P1, resolved in the coordinator's backend fix:** the original importer checked adjacent native sample counters and increasing host ticks independently, but did not check their mutual consistency. A valid6-sample48kHz package with a1-second host jump between3-frame blocks was `processing_eligible=true`, reporting3 frames per host second. A1ns jump reported3 billion. This contradiction could enter waveform processing even while the recorder declared complete continuity. The original executable evidence is `acquisition-review/probes.json`.

Apple describes sample and host fields of `AVAudioTime` as representations of the same moment, with host time based on the system Mach clock: <https://developer.apple.com/documentation/avfaudio/avaudiotime>. This supports a consistency check; it does not make different devices' clocks synchronized or equal to physical source time.

The coordinator added adjacent and first-to-current backend checks, retaining integer tick differences before conversion. The native owner independently applied the same bound and coarse-timer rejection in the collector; I read that final implementation and recompiled its injected tests. The rejection allowance is1% of elapsed nominal sample time plus two sample periods and two host ticks. Timer resolution coarser than0.1 sample period becomes unqualified. Raw bytes remain preserved, with no timing correction. This is a broad engineering admission bound, not a calibrated clock uncertainty or guaranteed discontinuity detector.

Independent post-fix probes in `recheck.json` confirm:

- Nominal48kHz,±5000ppm host scale and125/3ns Mach ticks remain eligible.
- A1-second gap, near-zero host progress and unresolvable timer tick are ineligible.
- A cumulative1.3% drift is rejected even though each10ms interval's130µs error fits the adjacent allowance; the from-first check catches it.
- An80µs step remains eligible within the broad bound. This limit is deliberately preserved in evidence; no sub-buffer warp guarantee follows.

No additional blocking software finding was established in the inspected scope. The native nominal test fixture initially used4 frames with1ms host advance, equivalent to4kHz. After the backend fix it is correctly ineligible. The native owner corrected the nominal fixture to83,333ns for four48kHz frames. I recompiled and reran the injected native tests, then decoded all five exported fixtures: the corrected nominal package is eligible; gap, overlap, host regression and the new inconsistent-host fixture remain ineligible. Byte preservation is unchanged.

## Executed evidence

- Six original Python acquisition tests passed before the fix. Seven focused acquisition tests passed after it, including raw package-to-six-surface simulation, interrupted package exclusion, manifest override resistance, import/export/reload and malformed-input rejection. This is software/simulation evidence only.
- Native injected-buffer tests passed: exact Float32/WAV/ZIP, frame accounting, gaps, overlap, host regression, invalid time, nonfinite samples, format changes, frame/block caps and50 append/stop races. No audio hardware was used.
- Independent Float32 probe checked19,928 finite patterns, including positive/negative zero, subnormal and maximum finite values. The exact Float32 bits survive ZIP/WAV import, widening to Float64 and conversion back to Float32.
- High unsigned64-bit host ticks retain exact differences above JavaScript's exact-integer range because the manifest uses decimal strings and Python subtracts integers before conversion.
- Swift-exported exact/gap/overlap/regression fixtures were decoded by the Python importer. Original WAV hashes and sample values remain available when timing evidence rejects processing.

Logs, source hashes and scratch programs are in `acquisition-review/`. `reviewed-source-hashes.json` captures the original reviewed files; `reviewed-source-hashes-final.json` records the final checked versions. Files changed during the review are explicitly distinguished, rather than claiming an immutable review of the whole working tree.

## Semantics and remaining physical limits

Float32 preservation is limited to samples delivered by AudioEngine. It does not prove raw ADC access, absence of OS/device gain or filtering, input directivity, or transducer phase stability. The code and contract make this distinction. The tap rejects non-Float32, multichannel and changing sample rates rather than silently converting. Preferred48kHz is separate from the actual activation and tap rates, and backend consistency checks reject contradictory declared formats.

Adverse native events stop admission and retain a partial export. Collector locking protects frame admission and stop/export ordering; late buffers do not mutate the closed snapshot. Native collection is bounded to20seconds and4096 blocks. Backend package decoding caps compressed/expanded input and manifest size, block/event counts and sample duration. The original ZIP is retained, so summaries cannot replace or repair timing evidence. A user-stop event does not prove the whole acoustic probe was captured; independent signal checks remain necessary.

Source configuration, probe and playback-route IDs are operator declarations. They are retained, not authenticated or acoustically established. Current single-session fitting does not bind these free-text IDs to a separate expected declaration. Unknown or contradictory free-text source IDs alone do not change `processing_eligible`; that field describes acquisition admission, not source calibration. A fixed Bluetooth/USB input route is likewise not physically qualified merely by matching initial/final snapshots. These are documented limits, not evidence that route fidelity was demonstrated.

Actual notification delivery, tap timestamps, negotiated sample rate, source routing, hardware interruptions/background behavior, delivered-sample processing and source/direct-path calibration remain own-device acceptance work. This review does not certify any phone geometry accuracy or physical timing precision.
