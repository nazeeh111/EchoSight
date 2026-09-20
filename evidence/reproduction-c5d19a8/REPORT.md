# Exact GitHub checkout reproduction

**Passed at `c5d19a8ced43f0692539e34d124376d6f4f20ee7`.** This commit was fetched from GitHub into the separate existing material-reproduction checkout, which was clean before and after execution. HEAD and origin/backend/implementation matched exactly when verified. This reuses the pinned Python environment; no new installation was performed.

| Check | Observed result |
| --- | --- |
| Full unittest suite, executed once | Exit 0; 249 tests passed in 68.737 s (69.370 s process wall time) |
| Archived saved-output replay | Exit 0; all 20 summary rows matched; transfer=false, promotion=false |
| Ideal held-path preflight | Expected exit 1; 20/24 unique, ideal_gate_pass=false |
| Production equality to ab5ea75de446b653fec058103030759fc7fbcdfa | Empty diff for echosight/, schemas/, acquisition/, capture ZIP, all three requirements files and pyproject.toml |
| Independent private GitHub release download | Exact expected 4,445,857 bytes and SHA-256 matched |

The evaluation helper and its five new tests are changes, and are covered by the 249-test suite. No claim is made that evaluation/ or tests/ are unchanged. Prior raw demos were not repeated. The saved-output checks do not reprocess audio, refit calibration/geometry or measure scientific runtime again. The observed failed scientific gates are retained; this is software and archived-evaluation reproduction, not new blind scientific evidence.

Environment: Python 3.12.14, NumPy 2.3.5, SciPy 1.18.1, macOS arm64. environment.txt and installed-versions.txt preserve exact reported details. commands.json records every suite/replay/preflight command, cwd, expected/actual exit code and wall duration. full-suite.txt is the complete test log. summary.json binds initial evidence hashes; additional-production-equality.json adds the evaluation dependency and package configuration comparisons.

Release `calibration-transfer-2026-09-19` asset `transfer-5d64234-raw-inputs.tar.gz` was independently downloaded with gh into a new directory. SHA-256 is `45cc11286e8c3180da562c50b28336ac14b66ec7384f6e09d81cf5a20f138567`. downloaded-raw-inputs/receipt.json preserves release/asset metadata, size, hash and exact commands/exits. This validates distributed bytes against the previously extracted and verified 74-file supplement; extraction/rendering/inference was not repeated after download.

No failed attempts, dependency installs, production mutations, commits or publication actions occurred in this verification. All launched subprocesses completed.
