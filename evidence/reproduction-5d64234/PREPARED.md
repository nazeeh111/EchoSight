# Prepared clean GitHub reproduction

Awaiting coordinator-supplied exact final runtime commit. No full test suite or demo has been run by this reproduction lane.

Separate checkout: `work/final-reproduction/checkout`, newly cloned from `https://github.com/nazeeh111/EchoSight.git`, single branch `backend/implementation`, without using the coordinator's reproduction checkout. Initial fetched remote branch: `c3de891223ab7e987616609c895a2e32ee85967a`. Clone completed with native scoped network approval.

Existing environment: `work/reproduction-venv/bin/python`; successful initial imports of NumPy, SciPy and jsonschema. No dependencies installed. Runner verifies every direct and test dependency's exact pinned version before tests.

## Read-only command audit

Current README commands map to implemented argparse commands: `demo`, `inspect`, `process`, `serve`, `compare`, and `probe`. The README explicitly identifies `demo` as both simulation and processing; `python -m echosight` works from the repository root without editable installation. The API's bare `echosight` executable requires the README's optional package installation; the frontend handoff already supplies the module equivalent. No new executable is needed for reproduction.

The frontend's `refine-demo`, scenario-specific `demo`, and controlled commands match live entry points. Documentation distinguishes session/job/scene version 1.0, comparison version 1.1, and the separate calibration envelope version 1.1. Formal schema IDs are resolved locally. Browser integration's local proxy/authentication requirement is explicit, as are archive quarantine and the need for a fresh store on repeated import.

README/API/frontend files inspected:

| File | SHA-256 |
| --- | --- |
| README.md | e70e6b378c6110aff5d876a064b58dffdb28dfd839ad48dc7972448e7acec2e3 |
| docs/API.md | 744f7b8c7e7cb47fe2efa8ea558a75f631b8839d79663cc0dc77e75fed0ded1d |
| docs/FRONTEND_HANDOFF.md | 8b342192d720140ea608659d1704f7a8bb74c64fab3e4e30b3d7904e3a9395cf |

No material command mismatch identified. Final evidence will hash those files again at the supplied commit.

## Exact execution

From current task root:

```sh
work/reproduction-venv/bin/python work/final-reproduction/run.py FULL_FINAL_RUNTIME_COMMIT
```

The runner fetches the branch, verifies target remote reachability, detaches at the exact SHA, records the environment and clean status, and runs `python -m unittest discover -s tests -v` once. Then it runs the twelve-view raw CLI demo, inspect, export, and replay into a new store. It validates the newly produced session, result and job schemas without network resolution, checks all twelve original hashes through export/replay, requires six surfaces including height structure and identical original/replayed geometry and result identity, and checks that Git remains clean.

`evidence-SHA12/commands.json` records exact executable argv, cwd, exit code and duration for every command. Separate logs, environment, source hashes, raw hashes, summary and explicit failure state are retained. Creating that evidence directory exclusively prevents accidental repetition at the same target.

Runner syntax passed using the existing environment. Prepared runner SHA-256: `c50f2154f595563ee4c699a9adcadf4a502033a99581350e1a19180aded48114`.

Limit: this reproduces a clean remote checkout with an existing pinned environment. It does not establish fresh dependency downloads, universal portability, physical-device accuracy, or success on the separately preserved failed scientific acceptance suites.
