# Eight-record saved-map follow-up

This separate synthetic development study passes its transfer gate and fails its promotion criteria. Both saved joint maps validate 24/24 paths. Their complete RMS errors are 20.4534 and 20.0449 microseconds. On instance 2821, the joint map improves one-x RMS by 14.7783 microseconds, below the required 20.8333 microseconds. The required 3 mm anchor improvement passes, but both improvements are required. No feature or physical qualification is promoted.

The original 56-record study remains failed: both original joint fits validate only 19/24 held paths. Its transfer and promotion decisions remain false. New held positions are a separate follow-up, not a replacement for the original failed results.

From a clean repository checkout with its declared NumPy/SciPy dependencies:

```sh
python evidence/calibration-held-followup/replay.py --output /tmp/new-followup-replay.json
```

Use a destination that does not exist. From any other directory or with this packet outside the checkout, specify `--repo /path/to/EchoSight`. No audio is processed or generated. The replay verifies the original replay manifest and all its declared inputs, recomputes all twenty original rows, then evaluates all ten saved maps against the new compact observations. It recomputes comparator benefits, retained null controls, transfer and promotion. The denominator remains 24 paths per method, including both zero-surface first-echo maps. Complete error fields stay null when incomplete; unique-subset errors are labelled separately.

`frozen_followup.py` contains the exact `held_metrics` and `summarize` functions from `records/original-run.py`. The latter is retained as historical source, **not a portable execution runner**. The replay supplies the new settings to the original manifest-verified frozen association function, and supplies recomputed original rows instead of trusting the historical summary. Expected follow-up values are read only after arithmetic completes. Gates, identifiers, structure and non-float types match exactly. Finite floating values use relative tolerance 1e-10 and absolute tolerance 1e-12. This replays the frozen evaluator; it is not an independent scoring implementation.

`source-identities.json` records full extraction and raw WAV SHA-256 identities plus the exact field projection. The packet retains four accepted observations per instance, their surveyed receiver coordinates, candidate IDs/delays/merged flags, both raw session/truth/manifests, the prospective protocol, frozen settings/input identities, and root approval record. Full extraction arrays and all eight WAV files are omitted. Packaging verified those full bytes locally; another checkout cannot independently verify omitted bytes from hashes alone or repeat extraction. The same recorded full-extraction identity is attributed to all five methods per instance. The actual projection has its own packet hash. Timing is inherited from the original saved maps, not measured again.

`reviews/execution/REVIEW.md` records an independent review of full local results and separate geometry verification. Its adjacent code and receipts retain the original review identity and context; their historical task-local paths are not portable commands. The package replay above is the portable entry point. The preparation review in `reviews/REVIEW.md` records pre-execution qualification, not completion. The root approval file identifies the human-authorized bounded local experiment; it is neither authority for new runs nor permission for publication.

The two instances use a first-order rectangular-room point-source simulation. Systematic extraction error and correlated geometry uncertainty remain UNKNOWN. These exposed development maps, synthetic recordings and saved-output arithmetic do not establish independent generalization, measured-room accuracy or real-device qualification. The frozen protocol and failed outcomes are preserved without retuning positions, seeds, maps, thresholds or source physics.
