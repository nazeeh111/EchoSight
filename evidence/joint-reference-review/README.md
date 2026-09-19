# Independent frozen-trial checks

Exact reviewer source/output for freeze `1b59eb563ba72e29eebf1244a3eb59272e9d8c97f42eaa147d5bac5970e2b941`. The log is retained as `.txt` to avoid global ignore rules. [Review](../independent-review-joint-reference.md).

The checker requires the retained original `work/joint-reference-trial/` and `work/source-calibration-mismatch/` inputs; it independently rebuilds mathematics without importing the trial solver or running an optimizer. Copy `check.py` to `work/review-joint-reference/check.py` and run with the pinned Python environment. For the separate clean-checkout derived-observation replay, see [portable replay](../joint-reference-trial/portable-README.md). Neither route qualifies physical accuracy.
