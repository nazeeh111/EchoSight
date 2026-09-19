# Preserved source-model experiment

This archive contains the exact50files of review snapshot `b5de1137125e098c6e546463abb18495585fdbcc48b2c3ed5b7fe3b2c896e417`. [MANIFEST.json](MANIFEST.json) hashes the original source, frozen designs, results and failed versions. [REPORT.md](REPORT.md) distinguishes nominal warning benefit from lost geometry and the invalid timing-axis stress. **Not promoted. [Independent review](../independent-review-source-model-prototype.md) found an invalid timing-axis stress and an inexact bounded-gain fit; corrections are separate active work.** The added restore helper and this index are outside that original manifest.

No recorded or simulated audio is committed. In a clean full Git checkout with the project-local dependencies installed, restore the exact expected experiment layout:

```sh
.venv/bin/python evidence/source-model-diagnostic-trial/restore.py
.venv/bin/python work/source-model-diagnostic/check_math.py
.venv/bin/python work/source-model-diagnostic/check_profiles.py
.venv/bin/python work/source-model-diagnostic/check_v3.py
```

The helper validates every archived byte and refuses to overwrite any differing work. Existing scientific sources must still match the frozen source hashes. The source runner uses historical de8442b for recording processing and geometry; a full checkout containing that commit is required. To regenerate the preserved development comparisons, run the original stages in order:

```sh
.venv/bin/python work/source-model-diagnostic/run.py run
.venv/bin/python work/source-model-diagnostic/run_v2.py run
.venv/bin/python work/source-model-diagnostic/run_v3.py run
```

These regenerate raw fixtures and overwrite only their restored working reports. Preserve the committed archive as the original evidence. The original `freeze.json` files are supplied: do not create another claimed unseen freeze. These exposed development seeds are not new blind acceptance evidence. Timing-axis sensitivity is retained as a failed representation stress, not a physical clock simulation. No software-only result establishes an ordinary-device source configuration.

The restore helper and all three listed mathematical checks were executed successfully from the clean checkout at3beffb5. Those narrow checks do not resolve the later independent-review findings or reproduce every classifier case.
