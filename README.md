# EIC invisible dark-boson selection study

Simulation code and numerical data for comparing rectangular cuts, an estimated likelihood, and boosted decision trees (BDTs), with and without nuclear momentum-transfer information, in invisible scalar and vector dark-boson searches at the Electron-Ion Collider. Manuscript sources and manuscript PDFs are excluded.

## Current analysis

Start with the [current analysis guide](docs/current-analysis.md), [revision package](revision/README.md), and [per-figure code and data](figures/README.md).

The current comparison contains ten independent runs at eleven masses for each boson type: 220 analyses, each with six selections. The numerical results include the repair of six photon-sampling failures. At 10 GeV, adding nuclear momentum transfer improves simulated significance by approximately 31–39%; BDT and likelihood give a smaller additional gain over cuts when all methods include t.

- [`revision/src/`](revision/src/), [`revision/scripts/`](revision/scripts/), and [`revision/config/`](revision/config/): current analysis implementations and configurations.
- [`revision/stratified_repair/`](revision/stratified_repair/): corrected aggregate results, resolution benchmarks, and photon-loss scenarios.
- [`revision/checks/`](revision/checks/) and [`revision/protocols/`](revision/protocols/): numerical checks and analysis provenance.
- [`figures/`](figures/): plotting entry points, compact input data, and rendered figures.

## Reproduction

The comparison plots can be regenerated from the committed numerical tables. See each figure's README for its inputs and plotting command. Event generation and fitting require ROOT with TFoam and TMVA, a C++17 compiler, and the corresponding event/model files; Python tools use NumPy and Matplotlib. The checked calculations used ROOT 6.36.04.

The [revision-data-v2 release](https://github.com/iRojae/Dark-Boson-ML-EIC/releases/tag/revision-data-v2) supplies current paired analysis arrays, run records, and 880 selected model files. Saved-array reaggregation reproduces the 198 primary comparisons, 132 selection summaries, and 2,376 photon-loss comparisons exactly. The [data-v1 release](https://github.com/iRojae/Dark-Boson-ML-EIC/releases/tag/data-v1) preserves the original study. See [download instructions](DATA_DOWNLOAD.md) for archive checksums, extraction, and the distinction between statistical replay and fresh event-level calculations.

## Earlier analyses

Top-level `src/`, `scripts/`, `config/`, `results/`, `fair_study/`, `plots/`, and earlier notes in `docs/` preserve the original study. They remain available for provenance; use `revision/` for the current comparison. Earlier figure folders are preserved under [`archive/original_figures/`](archive/original_figures/). The [original code guide](src/README.md) includes the Figure 3 reference-data comparison.

External papers and private documents are excluded. Reference distributions are identified in the corresponding figure instructions.
