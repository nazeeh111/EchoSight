# Independent v4 review evidence

`original-check.py`, `checks.json`, and `original-review.md` preserve the exact independent review bytes. `reproduce.py` changes only path/argument handling and verifies its output against the frozen checks; mathematical probes and reported-row aggregation are unchanged. It defaults to the sibling frozen v4 archive, verifies all 30 original hashes, runs 84 bounded-gain checks against SciPy BVLS and the three-record absent-plane check, and re-aggregates 24 saved result rows. No raw generation, source classification or mapper fit is performed.

```sh
.venv/bin/python evidence/source-model-v4-review/reproduce.py
# Optional alternate identical snapshot:
.venv/bin/python evidence/source-model-v4-review/reproduce.py --snapshot evidence/source-model-diagnostic-v4 --output work/v4-review-checks.json
```

Dependencies are the repository's pinned NumPy/SciPy environment. No historic core execution or external data is required for these narrow checks. Source and exact reviewer-result hashes are in MANIFEST.json. The [review report](../independent-review-source-model-v4.md) distinguishes algebra verification, preserved simulation totals and remaining hardware uncertainty.
