# EIC dark-boson selection study

Code, numerical results, and manuscript for the comparison of boosted decision trees with optimized rectangular cuts in coherent scalar and vector dark-boson production.

## Contents

- `src/`, `include/`, `scripts/`, `config/`: simulation and analysis code and configuration.
- `results/`, `fair_study/`, `plots/`: numerical summaries, analysis records, and figures.
- `paper/latex/main.tex` and `main.pdf`: current manuscript draft (contains author-completion fields).
- `docs/`: methods, provenance, and historical analysis notes. Earlier notes may describe superseded exploratory analyses; consult the manuscript and final-result manifests for the current presentation.

## Build the manuscript

Install a TeX distribution with pdfLaTeX and latexmk, then run `make paper`. Output: `paper/latex/main.pdf`.

## Simulation data

The `data-v1` GitHub release contains the `data/`, `models/`, and `fair_study/` directories as compressed archives. These include ROOT events, event-level CSV files, trained models, and complete run records, including historical development runs. They preserve the existing project directory structure. See `DATA_DOWNLOAD.md` for extraction and integrity checks.

## Reproducing the analysis

The simulation requires ROOT with TFoam and TMVA and a C++17 compiler. Python package requirements are in `requirements.txt`; inspect the analysis scripts for additional task-specific tools. See [project workflows](docs/PROJECT_WORKFLOWS.md) and the protocol documents under `docs/`. This publication snapshot was packaged from the existing project; the complete simulation was not rerun during upload.

The background model and detector assumptions are described in the manuscript. External papers, private progress documents, and superseded manuscript drafts are not redistributed. Public ancillary reference distributions used by historical comparison scripts must be obtained from the cited original work.
