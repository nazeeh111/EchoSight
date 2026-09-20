# Independent review evidence

These files preserve the exact executed reviewer probes, original outputs, test log, inspected-source hashes and report for commit `37d355f786e1fa337a0f50f1fda4d6eb3c5eb0f9`. `artifact-sha256.json` identifies the archived bytes. This directory is the canonical location of the report.

The probes resolve their immutable snapshot relative to their original location under `work/`. To reproduce, run the following from the repository root, using the existing project environment. Preserve an existing snapshot or probe output before replacing it; if a snapshot directory already exists, verify it belongs to the exact commit before using it.

```sh
mkdir -p work/review-37d355f-snapshot
git archive 37d355f786e1fa337a0f50f1fda4d6eb3c5eb0f9 | tar -x -C work/review-37d355f-snapshot
cp evidence/receiver-covariance/independent/review-37d355f-probes.py work/review-37d355f-probes.py
cp evidence/receiver-covariance/independent/review-37d355f-boundary-probes.py work/review-37d355f-boundary-probes.py
.venv/bin/python work/review-37d355f-probes.py
.venv/bin/python work/review-37d355f-boundary-probes.py
(cd work/review-37d355f-snapshot && ../../.venv/bin/python -m unittest tests.test_receiver_covariance -v) > work/review-37d355f-tests-rerun.txt 2>&1
```

The probes write fresh JSON outputs under `work/`; archived outputs here remain unchanged. Verify snapshot source files against `review-37d355f-source-hashes.json` before interpreting results. The environment used NumPy 2.3.5 and SciPy 1.18.1. These checks use simulated/prepared evidence and local nonlinear fits, not hardware measurements or a full acceptance-suite rerun. See the report for exact scope and limitations.
