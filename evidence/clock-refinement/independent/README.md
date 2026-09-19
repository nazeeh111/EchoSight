# Exact independent clock-review probes

These five files preserve the executed reviewer code, outputs and candidate diff. The [outcome report](../../independent-review-clock-refinement.md) identifies which63 raw recording pairs and two paired scene fits were rerun independently; aggregate counts for all1248records and24saved scenes were recalculated. Historical27/30+25 waveform checks were inspected but not independently rerun by this reviewer.

The scripts resolve paths from their original `work/` locations. They require the full frozen clock experiment layout, underlying v3/v4 raw inputs and full paired scene outputs described in the parent INTEGRATION.md. Those large artifacts are not embedded here; regenerate them first in a disposable checkout with the immutable core. Copy the scripts into `work/` before execution, preserving differing existing files. The spatial probe additionally reads `work/review-de8442b-snapshot/evaluation/metrics.py` from a Git archive of de8442b. These scripts are exact historical probes, not self-contained current-core benchmarks.

The self-contained production regression tests are the preferred quick reproduction of the repaired raw-clock defect. No own-device measurement or general confidence calibration is established by either route.
