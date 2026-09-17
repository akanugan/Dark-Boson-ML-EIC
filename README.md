# EIC dark-boson simulation and analysis data

Reproducibility package for comparing boosted decision trees with optimized rectangular cuts in coherent scalar and vector dark-boson production. The manuscript is not distributed in this repository.

## Contents

- `src/`, `include/`, `scripts/`, `config/`: simulation, analysis, and plotting code and configurations.
- `results/`, `fair_study/`, `plots/`: numerical outputs, analysis records, and scientific figures.
- `docs/`: methods, background assumptions, protocols, and provenance. Historical notes may describe superseded exploratory analyses; consult the final-result manifests.
- [Independent-run numerical tables](results/figure8_independent_runs/): exact values and uncertainty intervals.

## Simulation data and trained models

The [data-v1 release](https://github.com/iRojae/Dark-Boson-ML-EIC/releases/tag/data-v1) contains `data/`, `models/`, and `fair_study/` as compressed archives, including ROOT events, event-level CSVs, trained models, bootstrap outputs, and historical run records. See [download instructions](DATA_DOWNLOAD.md) for extraction and integrity checks.

## Reproducing the analysis

The simulation requires ROOT with TFoam and TMVA and a C++17 compiler. Python dependencies are listed in `requirements.txt`; individual scripts may need additional tools. See [project workflows](docs/PROJECT_WORKFLOWS.md) and the protocol documents under `docs/`.

This package was assembled from existing outputs; the complete simulation was not rerun during upload. External papers and private documents are excluded. Public ancillary reference distributions used by historical comparison scripts must be obtained from the cited original work.

For the Figure 3 macro, data paths, and generator files, see the [code guide](src/README.md).
