# Scientific sources and dataset provenance

Access checked 2026-09-18. Theory, published measurements, our simulation, hybrid measured-response replay, and our future phone recordings are distinct evidence classes. No paper's reported accuracy is transferred to this backend.

| Source | Access and use | Transfer limit |
|---|---|---|
| Crocco et al., [Uncalibrated 3D Room Reconstruction from Sound](https://arxiv.org/html/1606.06258), arXiv:1606.06258 | Primary methods/experimental sections, opened in research and reopened in implementation. Supports direct plane search as a serious alternative to image-source localization. | Its synchronous multichannel apparatus differs from independent phone clocks. Unknown spatial calibration is not unqualified asynchronous timing. |
| Sprunck et al., [Fully Reversing the Shoebox Image Source Method](https://arxiv.org/html/2405.03385v2), v2 2025-03-10 | Primary forward model and restrictions, research access; reopened in implementation. Motivates gridless competing recovery and tests of model mismatch. | Exact low-pass shoebox inversion is not proof for consumer hardware, finite furniture, diffraction or arbitrary source filters. |
| Di Carlo et al., [dEchorate](https://link.springer.com/article/10.1186/s13636-021-00229-0), 2021 | Primary dataset methods and limitations; reopened implementation. Actual small SOFA waveforms read using h5py. | Laboratory RIRs are genuine measurements, but convolving our probe with them is a hybrid replay, not a fresh recording. |
| [SOFA dEchorate directory](https://www.sofaconventions.org/data/database/dechorate/) | Directory reopened; five pre-existing local files verified by SHA-256 and length. URLs/hashes in `evaluation/external_manifest.json`. | Five microphones in each selected array are collinear. They test signal behavior and abstention, not unique unconstrained 3D recovery. |
| [Pinned annotation generator](https://github.com/Chutlhu/dEchorate/blob/d3e664f1e7a7d46241d7f7b3b3761448686b9537/dechorate/main_geometry_from_echo_calibration.py) | Prior selected static source audit at exact commit, not executed. Its image-source times agree with local annotation file to nanoseconds. | Those echo annotations are generated from a model, not independent echo truth. This implementation never loads them to fit or score detector recall. |

The hosted SOFA license is MIT, Copyright (c) 2019 Diego Di Carlo. The complete license is retained in each downloaded SOFA file and copied verbatim into external evaluation metadata. Raw external data are excluded from Git; retrieval is explicit, bounded to five files (8.8 MB), checks exact hashes and will not overwrite a changed local file. No upstream code is copied into the runtime.

Known SOFA metadata defects: all selected `RoomDescription` fields name `020002` despite different filenames, and `RoomTemperature` is 0 K. Do not derive configuration or sound speed from these fields. Coordinates are used as supplied calibration, with explicit uncertainty. 345.844 m/s is a declared reference-model constant in the replay, not independently established environmental truth. Source 5 was difficult in prior blind waveform tests; the evaluation retains every file instead of selecting the favorable source.

Existing research considered measured-array learned geometry, smartphone acoustic SLAM and audiovisual twins. They require different hardware, training or optical information. This release claims an inspectable acoustic measurement-to-surface loop, not invention of acoustic room mapping or dense object recognition. There is no optical reconstruction substitute.

No current event was supplied in the implementation charter. Historical event dates are intentionally not treated as a present deadline. Submission, eligibility interpretation and public publication remain separate from backend delivery.


FLAIR measured impulse responses plus laser geometry: see [bounded retrieval/license manifest](../evaluation/flair_manifest.json) and [access-depth/evaluation record](audit/EVALUATION.md). Zenodo record17037517, version1, CC-BY4.0; bounded range retrieval and subset checksums are distinguished from an unverified whole-file checksum. Measured responses are convolved with a probe for hybrid replay, not recordings from our phones. Spatial acceptance currently fails; the laser subset is incomplete reference coverage.
