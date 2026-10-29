# v2: invisible dark-boson selection study

We compare rectangular cuts, an estimated likelihood, and boosted decision trees (BDTs), using electron observables with and without nuclear momentum transfer `t`. Ten independent runs at eleven masses for each boson type give 220 analyses, with six selections in each.

## Figures and code

| Folder | Contents |
|---|---|
| [`figures/`](figures/README.md) | Figures 1–9, with plotting code, numerical inputs, and rendered images in each figure's folder. |
| [`src/`](src/README.md) | C++ signal and photon generators, BDT and likelihood fitting, rectangular optimization, and score evaluation. |
| [`scripts/`](scripts/README.md) | Statistical analysis, method comparisons, summary plotting, and data import. |
| [`results/`](results/README.md) | Selection results, photon rates, photon-loss scenarios, and `t`-smearing results. |
| [`config/`](config/README.md), [`include/`](include/README.md) | Physical inputs, rate configuration, and shared kinematics. |
| [`docs/`](docs/README.md) | Analysis definitions and interpretation. |
| [`provenance/`](provenance/README.md) | Recorded production workflows, protocols, source checksums, and numerical checks. |

The likelihood implementation is [`src/train_likelihood.cpp`](src/train_likelihood.cpp). The main numerical tables are [`results/selection_results.csv`](results/selection_results.csv) and [`results/summary.csv`](results/summary.csv).

## Reproduction

From the repository root:

```sh
cd v2
python3 -m pip install -r requirements.txt
python3 figures/05_selections/plot.py
```

Each [figure README](figures/README.md) gives its exact plotting command and dependencies. The comparison plots use bundled numerical tables. Figure 4 also needs ROOT and a C++17 compiler. Figure 3 uses the inclusive photon event file distributed with v1; its reference histograms and plotted bins are included here. Figure 1 is a supplied image.

Build the C++ programs from `v2/`:

```sh
./build.sh
```

This requires ROOT with TFoam and TMVA, a C++17 compiler, and Boost headers. The recorded calculations used ROOT 6.36.04.

The [v2 data package](https://github.com/iRojae/Dark-Boson-ML-EIC/releases/tag/revision-data-v2) supplies paired statistical arrays, run records, and 880 selected models. See the [download guide](DATA_DOWNLOAD.md) and [analysis commands](scripts/README.md). Raw event files and unselected model candidates are not included in that package.

The [analysis guide](docs/current-analysis.md) defines the observables and significance measure. [V1](../v1/README.md) preserves the original two-method study. Manuscript sources and complete manuscript PDFs are excluded.
