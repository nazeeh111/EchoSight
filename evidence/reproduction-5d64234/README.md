# Clean GitHub reproduction: 5d6423486be5

**Passed.** A separate clean GitHub checkout at exact commit `5d6423486be5fd448a4d7b42fbbaee264eb07c9c` passed **212 tests in 64.076 seconds**, then the raw twelve-view CLI demo, inspect, export, replay, and generated-artifact schema/identity checks. The checkout was clean before and after. No runtime changes, commits, dependencies, or scientific threshold changes were made by this lane.

The commit was fetched from `https://github.com/nazeeh111/EchoSight.git`, verified reachable from `origin/backend/implementation`, and checked out detached in `work/final-reproduction/checkout`. This is distinct from the coordinator's prior reproduction clone.

## Executed evidence

Original execution directory: task-local `work/final-reproduction/evidence-5d6423486be5/`. Compact logs, hashes and reports are archived beside this file. Generated WAVs, ZIP and replay-store files remain in the original ignored directory.

| Check | Result |
| --- | --- |
| Full suite | 212 tests, 64.076 s, OK; exactly one suite run |
| CLI demo | Twelve generated raw recordings, six room surfaces, height-dependent structure present |
| CLI inspect | Exit 0, actual saved result summary |
| CLI export | Exit 0; all twelve archived recording hashes equal originals |
| CLI replay | Exit 0; same twelve recording hashes and exactly equal six-surface geometry |
| Result identity | Both direct demo and replay: `result-88c96eea6c371d4653e6` |
| Generated schemas | Original/exported sessions, original/exported/replayed results, and replay job pass offline validation |
| Provenance | `physical_validation=false` retained |
| Git tree | Empty porcelain status before and after execution |
| Setup failures | None in this final reproduction; native scoped GitHub/loopback permission approved |

`commands.json` records exact argv, cwd, exit code and observed duration for every subprocess. `full-suite.txt` is the complete suite output. `environment.txt` records Python 3.12.14, macOS 26.6.2 arm64 and every checked dependency. `source-sha256.json` hashes runtime, tests, schemas and relevant handoff documents. `artifact-checks.json` records all recording hashes and identity assertions. `summary.json` ties results to the commit, runner and environment. The CLI-generated original recordings, archive and replay store remain available in the original ignored execution directory, not this Git archive.

## Exact invocation and hashes

From the current task directory, executed:

```sh
work/reproduction-venv/bin/python work/final-reproduction/run.py 5d6423486be5fd448a4d7b42fbbaee264eb07c9c
```

The runner fetches before execution and creates an exclusive per-commit evidence directory. It intentionally refuses accidental repetition in an existing directory. The full-suite command inside the runner is `python -m unittest discover -s tests -v`; the actual absolute interpreter and full paths are preserved in `commands.json`.

| Artifact | SHA-256 |
| --- | --- |
| run.py | c50f2154f595563ee4c699a9adcadf4a502033a99581350e1a19180aded48114 |
| full-suite.txt | 632a056e540d5837c3f567fc2277d8a451bbd568ac8bd4742b2a0393dbfec9ac |
| artifact-checks.json | 8d1aba64781d1974db84f9dc859c99548ce465065e44b1c4f6616cfa3b84f3fd |
| commands.json | d815dafd70bd20d996699b6eaf422180ab454d114800e66167c6023ac718ff83 |
| room.zip | 6cac45300b020bcab94a50c4fd32bdd9f29a79d5e686c45f64282489cba50b74 |

## Meaning and limits

This is direct local reproduction from a freshly cloned remote source, using the pre-existing pinned task environment. The runner verified installed versions against both requirements files before tests. No new download/install was performed, so this is not evidence of fresh dependency resolution or every supported platform.

The CLI scene is synthetic. The suite and replay establish software behavior within their checks; they do not establish own-device accuracy, erase harder synthetic or measured-data failures, or complete the scientific charter. Existing source-model, external reconstruction, and hardware limits remain in the repository state. The read-only command audit in `PREPARED.md` found no material mismatch between current README/API/frontend examples and live entry points.

For the original runner, restore `run.py` to a fresh ignored work directory with its own `checkout/` clone and sibling `reproduction-venv/`. It intentionally uses this relative layout. The portable manual setup/test/demo commands are in the repository README; the archived script is not a package entry point.
