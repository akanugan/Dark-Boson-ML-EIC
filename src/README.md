# Code guide

This directory contains shared programs used by the [current analysis](../revision/README.md)
alongside utilities retained from the original study. The current photon samplers,
likelihood fitting, and score evaluation implementations are in
[`revision/src/`](../revision/src/).

## Shared generation and fitting programs

| Source | Role in the current comparison |
|---|---|
| `generate_vector.cpp` | Generates vector signal events. Its massless-vector limit also supplies the original inclusive photon calculation used for Figure 3. |
| `generate_scalar.cpp` | Generates scalar signal events. |
| `train_tmva.cpp` | Fits and evaluates candidate TMVA BDT configurations on training and validation samples. |
| `optimize_rectangular_fair.cpp` | Searches rectangular selections using separate training and validation samples. |
| [`../include/DarkBosonKinematics.h`](../include/DarkBosonKinematics.h) | Shared kinematic definitions used by the vector generator and revision photon samplers. |

From the repository root, build the four shared programs with:

```sh
make bin/generate_vector bin/generate_scalar bin/train_tmva bin/optimize_rectangular_fair
```

Building requires ROOT with TFoam and TMVA, a C++17 compiler, and Boost headers
available on the compiler include path. See the current analysis guide for the
additional revision programs and workflow.

## Original-study utilities

`optimize_rectangular.cpp`, `evaluate_fair_model.cpp`, `extract_cutflow.cpp`,
`validate_sealed_sample.cpp`, and `plot_results.cpp` retain their original-study
roles. The multi-figure code in `plot_kinematics_roc.cpp`, the importance plot in
`plot_tmva_importance.cpp`, and `../scripts/plot_bdt_comparison.py` describe the
earlier plots; use [`figures/`](../figures/README.md) for the current numbering
and plotting entry points.

## Current Figure 3: inclusive photon shapes

Figure 3 retains the original inclusive photon comparison. Its canonical code,
reference histograms, binned data, and commands are documented in
[`figures/03_photon_shapes/`](../figures/03_photon_shapes/README.md).

The comparison step bins the inclusive photon sample and the reference
histograms, normalizing each distribution separately within its displayed range.
The corresponding original implementation is `validate_photon_shapes.cpp`;
the figure folder provides its `compare.cpp` entry point. The original
`make_photon_overlay` function in `plot_kinematics_roc.cpp` reads
`results/ml/photon_shape_validation.csv`; the canonical per-figure macro reads
the bundled `data/distributions.csv` instead.

Both plotting paths also read `data/ml/validation/photon_inclusive.root` to
calculate the fractions outside the displayed ranges. This inclusive event file
is supplied by the historical `data-v1` release. Trained models are not needed
for this figure. Earlier rendered copies remain under `plots/revision/`;
the current reference asset is in `figures/03_photon_shapes/`.
