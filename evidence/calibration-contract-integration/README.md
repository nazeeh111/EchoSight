# Calibration contract integration

The resumed calibration repair passes 210 assembled tests in 70.099s, including raw input, API loopback, malformed input, cancellation, calibration and schema checks. Exact source hashes and commands are in `checks.json`; the complete output is `tests.txt`. The pinned existing environment passes `pip check`.

The raw twelve-view CLI demo returns six surfaces, including two horizontal surfaces, with `partial` status and `refinement_budget_reached` retained. Export/replay recomputes identical surfaces, hypotheses, dimensions and raw recording hashes. These are simulated recordings, not physical accuracy.

Reproduction commands from the repository root:

```sh
python -m echosight demo work/checkpoint-demo --seed 1 --captures 12
python -m echosight export work/checkpoint-demo/session.json --output work/checkpoint-session.zip
python -m echosight replay work/checkpoint-session.zip --store work/checkpoint-replay --output work/checkpoint-replayed.json
```

All 16 tracked acceptance/freeze files retain their pre-repair hashes. Synthetic/external spatial failures remain unchanged. Own-device validation is absent. Historical source-calibration review logs omitted by global ignore rules are included verbatim with their original hashes; no scientific experiment or review was repeated to replace them.
