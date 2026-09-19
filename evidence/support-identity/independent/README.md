# Independent support-identity review artifacts

Exact executed probe, result, parent source and logs for commit `3745665352f59bc88e432b1f703054ab29398ce1`. Source hashes inside the probe result were independently checked against Git object bytes. No runtime implementation changes are included.

From the backend Git repository, restore the original work paths and immutable snapshot (use a fresh directory if a snapshot already exists):

```sh
mkdir -p work/review-3745665-snapshot
git archive 3745665352f59bc88e432b1f703054ab29398ce1 | tar -x -C work/review-3745665-snapshot
cp evidence/support-identity/independent/review-3745665-probes.py work/
.venv/bin/python work/review-3745665-probes.py
```

The probe uses the repository environment, imports only snapshot runtime code, retrieves the exact parent implementation from Git and writes its results into `work/`. It needs the parent Git object. It runs CLI subprocesses but does not bind a socket. To repeat the 20 focused tests:

```sh
cd work/review-3745665-snapshot
../../.venv/bin/python -m unittest tests.test_evolution tests.test_tracking_integration -v
```

The HTTP integration test needs permission to bind an ephemeral localhost port. The retained first log honestly contains that sandbox denial; the separate HTTP log records its subsequent successful authorized execution. Archive hashes preserve the exact original evidence. See `../../independent-review-3745665-support-identity.md` for scope and limits.

Coordinator-requested supplemental cancellation-boundary reproduction (run the primary probe first to materialize the parent source):

```sh
cp evidence/support-identity/independent/review-3745665-cancelled-probe.py work/
.venv/bin/python work/review-3745665-cancelled-probe.py
```

This reproduces an inherited P2 using actual late-cancelled inference output. It does not edit runtime code.
