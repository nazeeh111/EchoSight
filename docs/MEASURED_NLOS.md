# Measured non-line-of-sight ultrasound

`echosight nlos-fig2` reconstructs a published measured scene containing an H,
a dinosaur and a resolution star from reflected ultrasound. PHANTOM is this
measured-imaging direction inside EchoSight. It shares the package and CLI;
the supplied room demo model is a separate simulation.

## Exact input and execution

[Install the backend](../README.md#install-the-backend): Python 3.12,
NumPy 2.3.5 and SciPy 1.18.1 on local macOS/Linux. No additional packages are
needed. The command admits one exact case. Before running, budget **6 GiB** of
working memory and at least **1 GiB** free at both temporary/output locations.
This is an estimate, not a hard memory limit or a measurement of free RAM.

Obtain [official Fig2.zip](https://researchdata.gla.ac.uk/2046/3/Fig2.zip)
from the [Glasgow record](https://researchdata.gla.ac.uk/2046/). There is no
automatic download. The archive is 234,048,284 bytes, SHA-256:

```text
ad6f7a44562e4fc74b4a61cd15223ce9f49338f879a16142bf4bb25782c656fd
```

Extract its sole member, `2024_2_29_22_26_32641_star_dig_H.mat`, into your data
folder. The MAT file is 239,719,404 bytes, SHA-256:

```text
bddb46d4c26457b8364bb63c646c6d558c4db0d3004f36de0bd87d34f2a702f4
```

The selected input is `data_origin`: **55 × 55 × 25,000 float64 values**, sampled
at the source's declared **1 MHz**. The second `data_origin2` array is not
selected. Dataset and code use CC BY 4.0.

```sh
mkdir -p work
# Verify the exact input and see resources; this creates no output directory.
echosight nlos-fig2 --input /your/data/2024_2_29_22_26_32641_star_dig_H.mat \
  --output work/fig2 --preset li2025-fig2-phase-native \
  --sample-rate-hz 1000000 --estimate-only

# Execute into a new directory.
echosight nlos-fig2 --input /your/data/2024_2_29_22_26_32641_star_dig_H.mat \
  --output work/fig2 --preset li2025-fig2-phase-native \
  --sample-rate-hz 1000000
```

`python -m echosight` is equivalent. The input is copied into a private temporary
snapshot and its exact size/hash verified before MATLAB decoding. The fixed
worker receives that snapshot, not a path from a project or JSON file. Symlinks,
wrong bytes, unsupported presets/rates, insufficient declared budgets and
existing outputs refuse. The output parent must already exist.

No output is overwritten. A failed or interrupted run retains partial files and
`FAILED.json`; choose a fresh directory for another attempt. The worker uses
one FFT thread, 240-second soft/250-second hard POSIX CPU limits, and a 300-second
parent wall deadline.

## Inspect and reuse the result

Open generated `inspection.html` in a browser. Its native **55 × 55**
depth-colored image, linear amplitude image and interactive axial slice view
use actual saved output. Scrub consecutive source depth bins from about
**1.0 to 1.7 m**. Click a pixel or use arrow keys for its source-array index,
source coordinates and first threshold depth. Eight-bit slice displays add no
voxels; `volume.npy` preserves full precision. Source y increases downward in
this display. These coordinates are not registered into the room/world frame.

`report.json` records input/source hashes, method, preset, axes, threshold,
resources, limits and every saved artifact hash. Its schema,
`echosight.nlos-fig2-report/1`, is separate from room-result schemas.

| Array | Values |
| --- | --- |
| `volume.npy` | 3,125 × 55 × 55 float64 reconstructed amplitudes |
| `depth_m.npy` | 55 × 55 float64 first strict global-threshold crossings, counted from 1; NaN means unknown, not zero distance |
| `maximum_amplitude.npy` | 55 × 55 float64 axial maxima |

Load with `numpy.load(path, allow_pickle=False)`. Use `mmap_mode='r'` to avoid
loading the entire 75.6 MB volume at once. `preflight.json`, `run.json` and
`worker.log` retain execution evidence. `axial-display.bin` is a bounded,
quantized display subset; its native indices, scaling and hash are in the report.

## Method, evidence and limits

This adapts Li et al.'s [released code](../echosight/notices/li2025/NOTICE.md)
for [DOI 10.1038/s42005-025-02335-3](https://doi.org/10.1038/s42005-025-02335-3).
It retains phase and uses three adjacent pairwise sums (K = 3), no envelope,
no spatial upsampling, a padded FFT, linear Stolt migration, an inverse FFT,
and a `max(volume) / 4.5` threshold. Slabbed interpolation changes allocations,
not the method. The packaged notice includes source identities and changes;
it does not relicense pre-existing EchoSight files.

An independent review checked a small direct-DFT/scalar-interpolation reference
and source identities. Its largest small-volume error was 1.01e-16, with equal
depths. One actual local dataset run took 14.65 seconds with 3.10 GiB peak worker
memory. That is one baseline-port observation on one Mac, not a cross-platform
benchmark. The example qualitatively resembles published Figure 2c; native
MATLAB output and a quantitative physical-accuracy reference were unavailable.
Each integrated command records its own resource use.

Paper Methods describes a ±30 kHz band-pass absent from the released Figure 2
scripts; input prefilter status is unknown. Absolute depth calibration, carrier
frequency, time-zero offset, sound-speed calibration and room transform remain
unresolved. Published depth labels differ from this released route; no guessed
offset is applied. The 1.372 mm bin spacing is neither resolution nor uncertainty.
A first threshold crossing can reflect ringing.

This work does not establish new hardware measurements, arbitrary-wall imaging,
hidden solid geometry or an adaptive-method advantage. The paper already proposes
adaptive selection. Existing room/simulation failures remain in the
[frozen room state](https://github.com/nazeeh111/EchoSight/blob/backend/implementation/STATE.md)
and [evaluation guide](EVALUATION.md); the new route does not erase those results.
