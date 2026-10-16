# Published measured-NLOS method and data

Tailin Li, Ilya Starshynov, Khaled Kassem, Zongliang Xie, Ge Ren,
Yihan Luo and Daniele Faccio (2025).

- Paper: https://doi.org/10.1038/s42005-025-02335-3
- Official published PDF: https://eprints.gla.ac.uk/368628/1/368628.pdf
- Official data/code: https://researchdata.gla.ac.uk/2046/
- Dataset DOI: https://doi.org/10.5525/gla.researchdata.2046
- License: [Creative Commons Attribution4.0](https://creativecommons.org/licenses/by/4.0/).

`fk_us.m` and `generate_figures.m` are unchanged selected files from the official
[Code.zip](https://researchdata.gla.ac.uk/2046/2/Code.zip),
6558bytes,SHA256a66b0de38f08ae92243855dd522e9acf1b11f563e37b0c9416e0a99f5c4e5446.
The exact scripts and archive identities are listed in `source-manifest.json`.
These attribution/source files are included in wheels and source archives.
No MATLAB runtime or license is bundled.

`echosight/nlos.py` adapts their Fig2 full-phase/native55×55 route into Python.
Changes: omit MATLAB figure windows; use one SciPy FFT worker; calculate the
same Stolt linear interpolation along z in bounded slabs at unchanged x/y grid
nodes, skipping source-zeroed z≤0; save arrays and explicit source/axis/limit
metadata. Stdlib PNG/HTML displays add a quantitative legend. This adaptation
and the source-derived figures retain CC BY4.0 attribution. This notice does
not relicense any pre-existing EchoSight file.

The paper Methods describes a ±30kHz band-pass that is not explicit in these
released Fig2 scripts. Whether supplied data_origin was prefiltered is unknown.
No filter, time offset or room/world transform has been silently introduced.
This is a port of the released route, not a full independent reproduction of
every paper step, new algorithm, hardware demonstration or adaptive-sampling
result. The paper itself already proposes adaptive measurement selection.

Raw measured data and full reconstructed volumes are deliberately excluded from
Git. Obtain the exact official Fig2 input yourself; no automatic download is
performed. The input,source and supplied-document hashes are in the manifest.
