# Fresh GitHub and environment reproduction

A new clone of private GitHub `backend/implementation` at `38ce3ffcbca671fa00134284d53cdf9aef82dc90` and a new Python 3.12.14 virtual environment with newly installed `requirements-test.txt` pass all 210 tests in 59.184s. `pip check` passes. The checkout stays clean. Loopback HTTP tests ran with native permission.

The twelve-view raw CLI demo yields six surfaces, including two horizontal surfaces, with `partial` status and the refinement-budget diagnostic retained. Export/replay reproduces surfaces, hypotheses, dimensions and raw hashes exactly in that environment. The demo took 0.482s under shared local load; this is an observation, not a controlled performance benchmark.

All five calibration examples reproduce their status, canonical input identity and raw hashes. Three rejection artifacts are byte-identical. The proposal and held-out rejection differ by floating-point roundoff: maximum source delta 1.764e-10m, speed delta 3.507e-8m/s and predicted-delay delta 1.621e-13s. Their output/calibration hashes consequently differ. Canonical replay within each environment remains exact. This is numerical reproduction across installations, not byte-identical fitting; no scientific gate changed.

The eight historical source-calibration review files, including the two formerly omitted logs, all match their committed manifest hashes.

Commands from the new clone, using the new environment's Python:

```sh
python -m pip install -r requirements-test.txt
python -m pip check
python -m unittest discover -s tests -v
python -m echosight demo work/demo --seed 1 --captures 12
python -m echosight export work/demo/session.json --output work/session.zip
python -m echosight replay work/session.zip --store work/replay-store --output work/replayed.json
python evidence/calibration-contract/reproduce.py --output work/calibration-contract
```

These are software and simulation checks. Frozen synthetic/external spatial failures and absent own-device evidence remain unchanged.
