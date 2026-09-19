# Independent source-calibration review

The files here are exact reviewer-executed source, outputs and report. No runtime edits are included. Main evidence archive reviewed: `../source-calibration-mismatch-evidence.tar.gz`, SHA256 `2da45a689274cd1375e074c2da81edbd8e09d814ac6a803af98e10a03eb4aa1d`.

Run from the backend repository with the original retained `work/source-calibration-mismatch/` study and its pinned `core/` checkout:

```sh
cp evidence/source-calibration-mismatch/independent/review-source-calibration.py work/
cp evidence/source-calibration-mismatch/independent/review-source-calibration-replay.py work/
.venv/bin/python work/review-source-calibration.py
.venv/bin/python work/review-source-calibration-replay.py
```

The first verifies every archive payload, declared response-array hash transform, both freeze manifests against Git commit `3745665352f59bc88e432b1f703054ab29398ce1`, all 288 retained WAV hashes, original V1 snapshot, then independently checks local information. It requires original full observation outputs and raw files for the integrity portion. The second reprocesses three existing V2 recording sets and checks their frozen results.

The compact main archive deliberately omits WAVs, full response arrays and the runtime checkout. It is not by itself sufficient for these complete integrity/raw replay checks. To recreate a missing study, use its preserved protocols/runners and pinned Git commit in a separate fresh experiment directory; runners reject overwriting frozen/generated cases. Preserve the original evidence and restore the expected `work/source-calibration-mismatch/` paths only in an isolated repository copy. Runtime library versions in the reviewed evidence were Python 3.12.14, NumPy 2.3.5 and SciPy 1.18.1. The nominal mathematical information is distinct from nonlinear fit accuracy, and the new Gaussian draws test linear algebra only.
