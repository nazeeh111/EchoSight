# Output files and original-data preservation

CLI output paths must differ from their inputs. The check includes normalized paths, symbolic links, hard links, session-referenced recordings, material/reference/context files, prior comparisons, and controlled-protocol session manifests. `replay` protects its archive and store data. Output checks run before expensive work and again before publishing the result. A refused command exits2 without replacing the protected input.

An unrelated existing result file can still be explicitly replaced with `--output`. The ordinary result writer publishes complete JSON atomically. This does not authorize replacing the input session, recording, archive or reference data, even if the filename has another extension.

`probe`, `simulate`, `demo` and `refine-demo` require unused generated filenames. Existing directories with unrelated notes are allowed; reuse a fresh subdirectory for another run. Existing recordings, manifests, truth files and generated result names cause an error before generation begins. Dangling links count as occupied names. Individual generated files use exclusive creation, so a name claimed by another writer after preflight is retained. A failed/interrupted run may leave newly created partial output; use another fresh directory rather than overwriting it. The software does not delete the prior attempt automatically.

For example:

```sh
python -m echosight probe work/probe-001
python -m echosight demo work/room-001 --captures 12
python -m echosight compare work/before.json work/after.json --output work/comparison.json
```

Store exports refuse destinations inside `sessions/`, `jobs/`, or the store ownership lock, including paths through directory links. Normal archives in `exports/` or another chosen output directory remain supported. Original recording hashes and provenance are retained.

These checks prevent ordinary output/input collisions and tested late-writer cases. They are not an adversarial filesystem sandbox: software already running as the same user can change paths between checks. Keep independent backups of real recordings. The opt-in [browser workspace](WORKSPACE.md) selects originals by file input and never supplies arbitrary export destinations to the store.

Verification covers actual comparison input replacement before the repair; refusal across CLI input classes and linked aliases; unchanged originals after partial failures; preservation of late-created generation targets; store export protection; and normal unrelated-output replacement. Numerical inference and frozen scientific acceptance criteria are unchanged.
