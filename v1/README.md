# Version 1: original BDT-versus-cuts study

This directory preserves the original reproducibility package from commit
[`f75b3cd`](https://github.com/iRojae/Dark-Boson-ML-EIC/tree/f75b3cd8bba4fa007cc6dc3f934153e26040da6d)
(17 September 2026), with documentation updated for the versioned layout.
It compares BDT selections with optimized rectangular cuts. Its code, numerical
outputs, and figure numbering belong to the original study.

**Use [Version 2](../v2/README.md) for the current three-method comparison**,
including the estimated likelihood method, corrected photon sampling, and
both input sets at all masses. Version 1 does not contain those later results.

## Contents

- `src/`, `include/`, `scripts/`, `config/`: original simulation, analysis, and plotting code and configurations.
- `results/`, `fair_study/`, `plots/`: original numerical outputs, analysis records, and figures.
- [`docs/`](docs/README.md): original methods, protocols, and provenance. Earlier pilot notes are retained as historical records.
- [Original Figure 8 tables](results/figure8_independent_runs/README.md): original independent-run values and uncertainty intervals.
- [`figures/`](figures/README.md): original Figures 1–8, with per-figure code and small numerical inputs.

## Reproduction

Run commands from this directory, after `cd v1` from the repository root.
The simulation requires ROOT with TFoam and TMVA, a C++17 compiler, and Boost
headers. Python dependencies are in `requirements.txt`. See the
[original workflow guide](docs/PROJECT_WORKFLOWS.md).

The [data-v1 release](https://github.com/iRojae/Dark-Boson-ML-EIC/releases/tag/data-v1)
contains the original ROOT events, trained models, event-level CSV files,
bootstrap outputs, and run records. Extract it inside `v1/`, following the
[download instructions](DATA_DOWNLOAD.md). The current `revision-data-v2`
release belongs under `v2/` instead.

The unchanged current Figure 3 also uses the original inclusive photon ROOT
sample from `data-v1`; see the [Figure 3 guide](figures/03_photon_shapes/README.md).
The reference histograms needed by that per-figure macro are already included.
Other historical scripts may refer to source-machine files that were not
published; their paths are provenance, not additional download links.

The manuscript and private documents are excluded. This package was assembled
from existing outputs; the complete simulation was not rerun during upload.
