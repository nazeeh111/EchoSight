# Portable observation-level replay

From a clean repository checkout with its declared NumPy/SciPy dependencies:

```sh
.venv/bin/python evidence/joint-reference-trial/portable-replay.py
```

This optional replay reproduces the two frozen nonlinear calculations without
the ignored original study directory or WAV files. It imports the unchanged
`run.py` estimator. Its 48 records contain only the exact supplied source,
receiver and reference geometry, selected recorded delays and their uncertainty
inputs, plus capture/candidate IDs and original raw/waveform hashes. It reuses
the original admission records and compares fits, gates, residuals, covariance
matrices and paired-correlation sensitivity with the preserved results.

`portable-inputs.json` records SHA-256 identities of the 12 original full
session/reference/observation files used to create this field projection. Those
identities and all 48 raw hashes are checked against the original freeze. The
compact fields were projected only after checking those original files and the
existing raw admission boundary. The separate `portable-manifest.json` binds
the projection, adapter and required unchanged evidence bytes. The original
eight artifacts and `MANIFEST.json` are unchanged.

The adapter loads expected fit values only after fitting and never passes
generating truth to the estimator. It uses the existing fixed two seeds and
partitions, without a new solver, threshold, candidate-selection rule or raw
generation. Both fits reproduce with zero source/speed difference locally;
all numerical comparisons and exact gate comparisons pass. Output is retained
in `portable-result.json`. Tolerances are 1e-7 relative and 1e-10 absolute for
reported values, and 1e-12 absolute for covariance/Jacobian matrices. Different
installations may produce small numerical differences.

This is mathematical reproduction from derived observations, not fresh raw
processing, new scientific evidence, blind evaluation or verified physical
accuracy. Hash references identify omitted originals; they do not independently
verify omitted bytes on a clean machine. The original strict `run.py` remains
available for byte verification with the retained local raw/full-observation
tree, as described in the main README.
