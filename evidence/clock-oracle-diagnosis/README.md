# Separate postfreeze clock diagnosis

All three original files and [MANIFEST.json](MANIFEST.json) are copied exactly from `work/clock-refinement/oracle-archive-5347fc5f87c4`, content ID `5347fc5f87c4d79c51d41943d70e1f49746fff1e0b577b3d43628a75a747516d`. This README is outside that manifest. This is later evidence than [frozen v4](../source-model-diagnostic-v4/README.md); no live clock experiment is included.

The [addendum](V4-CLOCK-ADDENDUM.md) diagnoses an accepted approximately 143 ppm clock-rate error in three exposed development recordings. Supplying the generating rate only to the acquisition template reduces the direct-null error to approximately 0.275 ppm and removes one false echo candidate. That supplied rate is evaluation truth unavailable to a real receiver. This is not an implementable correction, calibrated confidence, new mapping result or hardware validation. Overlapping floor/ceiling paths remain unresolved, including a worsened nearest-candidate ceiling comparison. Original v4 classifications and thresholds remain unchanged.

## Dependencies and reproduction

The exact [probe](oracle_clock_v4.py) expects the conventional restored `work/source-model-diagnostic` layout, the immutable core checkout at `run-v4/checkouts/de8442b2dd088c036d2b92eaeaf29a1273785795`, and these original v4 generated fixtures:

- `run-v4/fresh/direct_null-2459`
- `run-v4/fresh/single_room-2459`
- `run-v4/fresh/near_reflector-2459`

Each fixture needs `baseline.json`, `truth.json`, and `source-02/capture-01.wav`. These large raw/baseline artifacts remain outside Git. Restore/regenerate them using the [v4 reproduction instructions](../source-model-diagnostic-v4/README.md), with pinned project dependencies and the original core. The archived results contain raw hashes and both immutable/oracle signals-source hashes. To repeat the original diagnostic in a disposable restored checkout:

```sh
cp evidence/clock-oracle-diagnosis/oracle_clock_v4.py work/source-model-diagnostic/oracle_clock_v4.py
.venv/bin/python work/source-model-diagnostic/oracle_clock_v4.py
```

The script re-extracts only those three recordings, verifies original clock/candidate outputs, and writes `work/source-model-diagnostic/v4-oracle-clock-results.json`. It performs no classifier or mapping fit. Preserve existing work before copying a script or replacing a working report. Archival verification checked bytes only; this task did not rerun the oracle or any live experiment.
