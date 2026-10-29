# v2: current three-method study

This version compares rectangular cuts, an estimated likelihood, and boosted decision trees (BDTs), each with electron inputs alone and again with nuclear momentum transfer `t`. Ten independent runs at eleven masses for each boson type give 220 analyses, each containing six selections. The results include the six photon-sampling repairs.

At 10 GeV, adding `t` improves simulated significance by approximately 31–39% across the three methods. BDT and likelihood provide a smaller additional gain over cuts when all methods include `t`.

| Folder | Contents |
|---|---|
| [`revision/`](revision/README.md) | Current implementation, corrected results, calibration, response checks, and provenance. Earlier revision pilots are identified separately in its code guides. |
| [`src/`](src/README.md), [`include/`](include/README.md) | Signal generators, BDT trainer, rectangular optimizer, and shared kinematics required by this version. |
| [`config/`](config/README.md) | Shared physical preselection; current rate-input and calibration roles are explained under `revision/`. |
| [`figures/`](figures/README.md) | Current Figure 1–9 code, compact inputs, and rendered assets. |
| [`docs/`](docs/README.md) | Current analysis guide. |

The likelihood implementation is [`revision/src/train_likelihood.cpp`](revision/src/train_likelihood.cpp). Final selection summaries are in [`revision/stratified_repair/selection_results.csv`](revision/stratified_repair/selection_results.csv); final photon calibration is in [`photon_calibration_rates.csv`](revision/stratified_repair/photon_calibration_rates.csv).

## Reproduction

From the repository root, enter this version before running its commands:

```sh
cd v2
python3 -m pip install -r requirements-revision.txt
python3 figures/05_selections/plot.py
```

Current comparison plots use committed tables. Figure 4 also requires ROOT and a C++17 compiler. The unchanged Figure 3 reads the original inclusive photon ROOT sample under `../v1/`; its [instructions](figures/03_photon_shapes/README.md) explain that dependency. Figure 1 is a supplied image; its editable source was unavailable.

To build the scientific tools, from `v2/`:

```sh
revision/build.sh
```

Building requires ROOT with TFoam and TMVA, a C++17 compiler, and Boost headers. The recorded calculations used ROOT 6.36.04. The v2 build includes its own copies of the shared original generators; no v1 build is required.

The [revision-data-v2 release](https://github.com/iRojae/Dark-Boson-ML-EIC/releases/tag/revision-data-v2) supplies paired analysis arrays, run records, and 880 selected models. It supports statistical replay of 198 primary contrasts, 132 selection summaries, and 2,376 photon-loss comparisons. It excludes raw event files and unselected model candidates. See [download instructions](DATA_DOWNLOAD.md) and [reaggregation commands](revision/scripts/README.md).

Original-study results and Figure 1–8 numbering are preserved separately in [`../v1/`](../v1/README.md). Do not substitute them for v2 results. Paths in `revision/EXPORT_MANIFEST.csv` and the release inventories remain relative to this `v2/` directory; their historical source-path fields and checksums are unchanged. Manuscript sources and complete manuscript PDFs are excluded.
