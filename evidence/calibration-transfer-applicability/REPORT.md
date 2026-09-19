# Acquisition-to-mapper handoff decision

Inspected backend e372158d9daa47891b0c5f7106b224b0aca75d05. No runtime edits, new recordings, waveform generation, hardware access or commits. The completed 38ce3ff provenance/schema audit was not repeated. All work here is advisory evidence derived from existing inputs.

## Consequential next requirement

Demonstrate that the fixed two-reference source/effective-speed calibration transfers to a room recording set with the same physical emitter/configuration, and improves or preserves useful 3D recovery. The two successful isolated-reference fits cannot establish this. A generic raw multi-reference utility is premature: it would expose a new public interface and duplicated policies before there is mapping benefit.

The experiment must be a separate bounded transfer test. Existing trial seed numbers, source coordinates or reuse of a probe are not evidence of source identity between unrelated recordings. Reprocessing isolated x/y WAVs as if they were a room cannot recover the room. A valid retained room set needs the same actual source configuration/effective-speed convention and a documented survey error relationship. Otherwise the exact blocker is missing matched room waveforms, requiring a separately frozen generation/capture experiment, not an adapter.

For a new development experiment, freeze before generation: one fixed room/source configuration; two recording realizations corresponding to both fitted source-reference controls; twelve noncoplanar mapping receiver stops plus four withheld stops; same source orientation/FIR, receiver FIR, effective speed and probe as the source references; independent recording clock/noise draws and independently drawn receiver surveys for the mapping set. Keep surveyed reference planes and generating truth out of mapping inputs. Retain the original x/y raw hashes and fixed source fits. No recalibration on room echoes or selection of a successful seed.

Compare identical room recordings under nominal calibration, existing single-reference calibration and fixed joint-reference calibration, with the existing mapper and direct-plane-grid baseline. Use existing public process_session for recording admission, then the current inference methods. Accept a full selected room result only with all six surveyed planes including floor/ceiling, 5 degree/0.10 m geometry tolerance and zero unmatched definitive planes (H4). Report the older frozen suites under their original own criteria, never substitute H4 for their 0.15 m match threshold. Report all misses, ambiguous/missing withheld paths, and ≤100 µs RMS/≤200 µs maximum for identifiable supported withheld paths without refitting. Preserve all original reference admission/bound/held gates. Record runtime against H4's ten-second processing target, separately from acquisition. If the proposed new layout is an exposed development case, call it that; it is not a new blind validation family.

Promotion additionally requires a predeclared actual gain over nominal or one-reference operation, with no false-surface regression. Passing room gates under every calibration would establish transfer, but would not itself establish that a generic two-reference feature earns its public maintenance cost. A failed joint transfer closes this bounded promotion attempt; retain outputs and do not retune to the room truth.

## Concrete public handoff gap

The experimental multi-source receiver covariance limitation is already documented: receiver_covariance.py requires independence from source/effective speed. This is not a newly discovered defect in that contract. The currently public single-reference path has an unqualified applicability gap:

- docs/CALIBRATION.md says the successful source/speed/covariance fields can be applied through calibration PATCH and then reprocessed from preserved raw bytes. It does not require independent mapping observations and surveys.
- storage.SessionStore.update_calibration accepts exactly these fields and preserves captures/raw bytes. validate_session accepts a source-reference session after applying a successful proposal.
- inference._covariance adds source/speed covariance, receiver variance and audio timing variance independently. It has no representation for correlation between a fitted calibration and the receiver surveys or timing observations used to fit it.

That public copying route is therefore an incomplete statistical handoff when the fitted source is used with calibration training recordings or their receiver surveys. It is not evidence of a wrong room reconstruction: the probe below is deliberately a covariance comparison at existing isolated-reference paths. Nor is independence guaranteed just by new capture IDs, different WAV hashes, moving phones, or resurveying with a common systematic frame error.

## Executed numeric probe

Run `.venv/bin/python work/acquisition-finish/cross_probe.py` from the backend. It reads existing single-2821-x WAVs, invokes current public calibrate_reference, applies the resulting three fields through session validation, and checks the current mapper covariance against its independently expanded formula. The proposal passed. Maximum covariance disagreement is 7.44e-18 seconds².

For declared-minus-actual receiver survey error dr, let H be the source/log-speed prediction derivative, D the receiver derivative, R receiver covariance and K the local weighted fit sensitivity. Then fitted parameter error is K(e - D dr - G dg), with e timing error. Thus Cov(fit,dr) = -K D R. Conversion from log-speed to speed applies the existing diagonal transform. Independent new audio at reused survey stops still requires the two source/receiver cross terms. Reusing the actual training audio also requires Cov(fit,e) = K T and its two cross terms. These are the same local model assumptions as the current output covariance; no uncertainty coverage claim is made.

Existing capture-00 delay SD:

| Model | Conditional SD |
|---|---:|
| Runtime independent addition | 79.506 µs |
| Fresh audio but reused calibration survey | 77.856 µs |
| Reused calibration training audio and survey | 40.102 µs |

Fresh-audio shared-survey effects reach only 2.1% in this particular case, so this does not substantiate a large source/receiver interval defect by itself. The same-audio dependence is material (SD ratio 0.504); held records remain unchanged because their timing and receiver errors were not used to fit. Both source/receiver and same-audio dependence must be separated when judging practical impact. `cross-probe.json` preserves all twelve rows and the cross block. No room waveform was generated or altered. One local linearized example is not confidence qualification.

## Smallest remedy and reuse

Before any promotion, clarify the public handoff applicability: proposal values/covariance can be used directly only when mapping audio and receiver survey errors are independent of the fit inputs, conditional on the declared reference/source model. Raw replay of the calibration session is still valid for reproducing calibration, but cannot be presented as independent mapping evidence. If a client needs reused calibration surveys/audio, retain the joint nuisance cross covariance in a separately specified integration; do not silently zero it or enlarge marginal uncertainty to pass.

Do not solve this by introducing another recorder, importer, waveform processor, covariance framework or source admission policy. Reuse storage validation/lossless import/hash policies; pipeline.process_session and acquisition.source_declaration_consistency; current calibrate_reference for its supported one-reference public path; current fixed trial runner for the bounded two-reference experiment only; current inference/grid methods for mapping. The trial runner is scientific evidence, not a production adapter. A future implementation must explicitly share existing admission/result-envelope policy, and must represent required calibration-to-mapping correlations before claiming support for reused surveys.

Remaining obstruction: matched calibration-to-room raw data and source identity, plus user/root assignment before changing owned runtime/docs. Hardware qualification remains separately unavailable and must follow the existing H1–H5 acceptance plan, not a demand for immediate microphone access.

## Archive applicability

This report and probe are preserved from `work/acquisition-finish/`. The probe requires the original ignored V2 raw recordings at its declared path; the repository-only artifact is not a raw reproduction. Running the archived script writes `cross-probe.json` beside the script. Preserve the archived result before rerunning. The public calibration documentation now explicitly states the independent-mapping-input requirement.
