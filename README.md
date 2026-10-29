# EIC invisible dark-boson selection study

Simulation code and numerical data for comparing rectangular cuts, an estimated likelihood, and boosted decision trees (BDTs), with and without nuclear momentum-transfer information, in invisible scalar and vector dark-boson searches at the Electron-Ion Collider. Manuscript sources and manuscript PDFs are excluded.

## Current analysis

Start with the [current analysis guide](docs/current-analysis.md), [revision package](revision/README.md), and [per-figure code and data](figures/README.md).

The current comparison contains ten independent runs at eleven masses for each boson type: 220 analyses, each with six selections. The numerical results include the repair of six photon-sampling failures. At 10 GeV, adding nuclear momentum transfer improves simulated significance by approximately 31–39%; BDT and likelihood give a smaller additional gain over cuts when all methods include t.

## Which files apply to which study?

| Status | Files | Use |
|---|---|---|
| **CURRENT RESULTS** | [`revision/stratified_repair/`](revision/stratified_repair/README.md) | Corrected three-method comparison, resolution benchmarks, and photon-loss scenarios. |
| **CURRENT FIGURES** | [`figures/`](figures/README.md) | Canonical Figure 1–9 code, inputs, and rendered assets. Figures 1–3 are unchanged from the original submission. |
| **CURRENT + EARLIER REVISION TOOLS** | [`revision/src/`](revision/src/README.md), [`revision/scripts/`](revision/scripts/README.md) | Current entry points and required helpers are listed separately from earlier revision pilots. |
| **CURRENT CONFIGURATION** | [`revision/config/`](revision/config/README.md) | Preselection and starting inputs. Final photon rates are in [`photon_calibration_rates.csv`](revision/stratified_repair/photon_calibration_rates.csv), not the starting rate CSV. |
| **SHARED CODE** | [`src/`](src/README.md), [`include/`](include/README.md), [`config/`](config/README.md) | Original signal generators, BDT trainer, rectangular optimizer, and physical definitions still used by the current workflow. Other tools in these folders belong to the original study. |
| **OLD STUDY ONLY** | [`fair_study/`](fair_study/README.md), original classifier [`results/`](results/README.md), [`scripts/`](scripts/README.md), [`archive/original_figures/`](archive/original_figures/README.md) | Original BDT-versus-cuts analyses, wrappers, and superseded figures. |
| **HISTORICAL OUTPUTS** | [`plots/`](plots/README.md), [`frozen_baseline/`](frozen_baseline/README.md), [earlier notes](docs/README.md) | Preserved original outputs and records. Some unchanged assets remain shared; the folder guides identify them. |

Names such as `final`, `current`, `rigorous`, or `sealed` inside historical paths describe that stage of the work. They do not identify the current result. Recorded protocols and numerical checks are indexed under [`revision/`](revision/README.md).

## Reproduction

The current comparison plots can be regenerated from committed numerical tables. Figure 3 additionally needs the original inclusive photon ROOT sample from `data-v1`; its reference histograms are bundled. See each [figure's README](figures/README.md) for dependencies and commands. Event generation and fitting require ROOT with TFoam and TMVA, a C++17 compiler, and the corresponding event/model files; Python tools use NumPy and Matplotlib. The checked calculations used ROOT 6.36.04.

The [revision-data-v2 release](https://github.com/iRojae/Dark-Boson-ML-EIC/releases/tag/revision-data-v2) supplies current paired analysis arrays, run records, and 880 selected model files. Saved-array reaggregation reproduces the 198 primary comparisons, 132 selection summaries, and 2,376 photon-loss comparisons exactly. The [data-v1 release](https://github.com/iRojae/Dark-Boson-ML-EIC/releases/tag/data-v1) preserves the original study. See [download instructions](DATA_DOWNLOAD.md) for archive checksums, extraction, and the distinction between statistical replay and fresh event-level calculations.

External papers and private documents are excluded. Reference distributions are identified in the corresponding figure instructions.
