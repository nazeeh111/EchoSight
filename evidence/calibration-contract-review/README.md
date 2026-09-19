# Preserved independent calibration review probes

Exact reviewer source and outputs for commit `38ce3ffcbca671fa00134284d53cdf9aef82dc90`; only log filenames change to `.txt` for portable packaging. [Review report](../independent-review-38ce3ff.md). No new scientific evaluation was run here.

To rerun in a fresh disposable directory:

```sh
mkdir -p work/review-calibration/source
git archive 38ce3ffcbca671fa00134284d53cdf9aef82dc90 | tar -x -C work/review-calibration/source
cp evidence/calibration-contract-review/probe.py work/review-calibration/probe.py
.venv/bin/python work/review-calibration/probe.py
```

The script creates its own simulated recordings and sends SIGINT only to its own child CLI process. `tests.txt` preserves the separate 25-test run; `source-check.json` binds reviewed source and unchanged numerical-block hashes.
