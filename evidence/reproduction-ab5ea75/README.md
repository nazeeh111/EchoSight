# Clean GitHub reproduction: EchoSight 0.2.0

Exact fetched remote and detached checkout: **ab5ea75de446b653fec058103030759fc7fbcdfa**. The tree was clean before and after execution. **244 tests passed in 70.255 seconds**, with one full-suite run. The existing pinned Python environment was reused from the previously recorded fresh installation; this run did not reinstall dependencies or add packages.

[Summary](summary.json), [full test log](full-suite.txt), [environment](environment.txt), [exact commands](commands.json), [source hashes](source-sha256.json), [artifact checks](artifact-checks.json).

Verified:

- Documented twelve-view room CLI demo and inspect: six supported surfaces including floor and ceiling.
- New controlled raw material demonstration: six surfaces, three correct synthetic reference-filter estimates and three material unknowns, supplied contextual palettes, and all eight declared controls passing. [Complete material summary](material-summary.json).
- CLI context processing exactly matches demo result identity, geometry and interpretation. CLI reference building reproduces the complete profile object, including means, covariance, training hashes and palette.
- Ordinary and context-bearing raw archives replay in new stores with all twelve byte hashes, result identity, geometry and interpretation unchanged. Imported computations are quarantined before recomputation; archive binding diagnostics are empty for valid archives.
- Offline context, interpretation, session, result and job schemas validate. Full-suite HTTP checks use temporary local servers.

The [fresh assembled review](../material-appearance/FINAL-ab5ea75-REVIEW.md) covers this exact runtime and closes both reported contract findings. The final documentation/evidence delivery commit must preserve runtime, tests, schemas and evaluation code at this commit; no repeated full suite is justified for evidence-only changes.

## Reproduce the complete check

Run from a checkout with the pinned requirements available and GitHub access. This creates a new clone and never overwrites an existing reproduction directory:

```sh
mkdir -p work/clean-reproduction
cp evidence/reproduction-ab5ea75/run.py work/clean-reproduction/run.py
python3.12 -m venv work/reproduction-venv
work/reproduction-venv/bin/python -m pip install -r requirements-test.txt
work/reproduction-venv/bin/python work/clean-reproduction/run.py ab5ea75de446b653fec058103030759fc7fbcdfa
```

The [runner](run.py) retains the executed checks. Its remote check now permits the requested commit to be an ancestor of the recorded default-branch head, so this exact pin remains runnable after later evidence commits. The original run verified equality; its original runner hash and complete commands remain in the receipts. Git network access and local loopback binding must be available. Use an unused `work/clean-reproduction` directory, or rename it consistently before another run.

These are software and controlled simulation results. Existing frozen synthetic/external spatial failures remain visible. No physical device, building-material accuracy, qualified confidence or optical sensing is established.
