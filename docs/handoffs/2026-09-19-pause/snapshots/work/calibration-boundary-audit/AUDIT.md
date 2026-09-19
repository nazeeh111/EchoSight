# Public reference-calibration boundary audit

Audited commit: `5f778a887817761b9db0626256698c5f678b497f`. Runtime source hashes are in `report.json`; no runtime or test files changed. This audit used the existing 20-recording development fixture, not held-out scientific answers or physical devices.

## Result

No unsafe calibration publication under ordinary CLI SIGINT was reproduced. A concrete, bounded handoff gap remains: calibration output has no formal result contract/example and does not retain its exact supplied reference or nominal acquisition snapshot. This is an auditability/integration gap, not evidence that the fitted calibration is wrong.

## Interruption evidence

`probe.py` invokes the real CLI on raw recordings and raises actual SIGINT at three deterministic boundaries: after the first recording's signal processing, after the reference least-squares fit, and immediately before output saving. Each is exercised with an absent output destination and with an existing destination. All six runs exit 130; no new output is written and existing bytes are unchanged. All 20 original recording hashes remain unchanged. A normal positive run produces `calibration_proposal`, 20 selected candidate records, 16/4 declared training/validation IDs and 20 raw recording hashes, with `physical_validation=false`.

`cli.py:149–158` calls calibration and only then saves its returned proposal/rejection. `KeyboardInterrupt` reaches the outer handler at 207–209. There is no cooperative cancel/progress argument or partial recovery envelope in `calibrate_reference`. The latter limits integration/recovery convenience, but unlike the earlier controlled comparison defect, it does not silently return unfinished evidence as a completed proposal. The caller can preserve its original session/reference and rerun. These probes test pre-publication interruption, not impossible immediate preemption after a completed atomic save.

No cooperative-cancellation feature is recommended from this evidence alone. Document current interrupt behavior and recovery procedure rather than adding another cancellation mechanism without a concrete consumer requirement.

## Admission behavior

The public core uses validated session input and the actual recording pipeline (`calibration.py:28–29,67`). Native discontinuity rejection and exact waveform-reuse admission therefore still apply to its observations. Known contradictory source declarations are explicitly checked at 88–95 before the reference optimizer. The focused existing regression `ReferenceCalibrationAdmissionTests` passed in 0.382s: real native packages with a conflicting declaration are rejected while all raw hashes/partitions remain present, and an ordinary mapping `no_result` alone does not wrongly disqualify reference fitting. Unknown source declarations remain uncertainty, not certification. No new policy bypass was found in this scope.

## Concrete handoff gap and minimal repair

At `calibration.py:82–87`, the output stores an opaque input result ID, recording provenance, partition IDs and a generic statement that reference geometry was independently supplied. It does **not** store the reference normal, offset, their uncertainty, selected search bounds/radius, or the nominal source/receiver calibration inputs. The opaque calibration ID incorporates the caller's reference dictionary at 158–159, but a hash cannot recover it. Consequently `proposal.json` by itself cannot establish which surveyed plane/uncertainty produced its covariance. This matters when a client inspects and applies the three calibration fields using the documented PATCH workflow. The early nonspatial rejection at 65–66 is even thinner, omitting the declared partition and input binding.

Only `schemas/calibration-patch.schema.json` exists. It describes applying fields, not the `calibration_proposal`/`rejected` result and its evidence. `docs/CALIBRATION.md` includes a human-readable request example but there is no formal reference request/result schema or calibration example in `examples/`. The existing `schema_version:1.0` output alone is insufficient as the charter's stable frontend handoff for this public CLI/core capability.

Recommended single cohesive repair, without changing the solver or acceptance thresholds:

1. Retain a bounded canonical copy of the validated reference fit inputs (including effective defaults) and the fit-relevant acquisition snapshot, with session/frame identity, probe metadata, ordered source/receiver poses and uncertainty, partition IDs and raw hash bindings. Exclude raw filesystem paths and arbitrary metadata. Emit a stable input/result identity for both successful and meaningful rejected results, including nonspatial rejection before decoding; distinguish not-read raw inputs from verified recording hashes. Keep supplied reference geometry clearly classified as calibration input, never inferred room geometry. Derive identity from those canonical inputs plus implementation provenance, not incidental caller dictionary fields. Preserve the existing applicable calibration ID separately where needed.
2. Publish a small versioned calibration-result schema and representative actual proposal/rejection examples. Encode that `rejected` cannot carry applicable calibration fields/ID. Define all units and joint covariance ordering; retain existing conditional/hardware caveats. A reference-input schema can share this input definition rather than inventing an API.
3. Check actual CLI/core outputs against the schema, preserve malformed-input behavior and source-conflict rejection, and verify that stored exact inputs reproduce the proposal from preserved recordings. Add a sparse-geometry rejection example so the schema does not describe only favorable fits.

No new endpoint, calibration optimizer, source model, reference acquisition routine, measured-confidence claim or global schema redesign is needed.

## Reproduction

From repository root:

```
.venv/bin/python work/calibration-boundary-audit/probe.py
.venv/bin/python -m unittest tests.test_mapping_admission_cancellation.ReferenceCalibrationAdmissionTests -v
```

Artifacts: `report.json`, `probe.log`, `admission.log`, `proposal.json`, exact `session.json`/`reference.json`, raw development recordings. The raw fixture stays task-local. The report distinguishes these simulation checks from physical validation.
