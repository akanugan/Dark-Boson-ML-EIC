# Simulation and selection code

Build these programs with `./build.sh` from `v2/`. Executables are written to `bin/`.

| Source | Purpose |
|---|---|
| [generate_vector.cpp](generate_vector.cpp) | Vector signal generation. |
| [generate_scalar.cpp](generate_scalar.cpp) | Scalar signal generation. |
| [generate_photons.cpp](generate_photons.cpp) | Photon generation in specified acceptance regions. |
| [generate_photon_outside.cpp](generate_photon_outside.cpp) | Full-support laboratory-coordinate generation of photons outside acceptance. |
| [merge_photon_samples.cpp](merge_photon_samples.cpp) | Combine central and outside photon samples using their cross sections and miss probabilities. |
| [train_tmva.cpp](train_tmva.cpp) | Fit candidate BDT configurations. |
| [train_likelihood.cpp](train_likelihood.cpp) | Fit the TMVA PDERS estimated likelihood. |
| [optimize_rectangular_fair.cpp](optimize_rectangular_fair.cpp) | Optimize rectangular selections on common training and validation samples. |
| [export_scores.cpp](export_scores.cpp) | Evaluate fitted models and cuts, including photon-loss and smearing scenarios. |
| [select_thresholds.cpp](select_thresholds.cpp) | Select thresholds using validation events. |
| [check_photon_sampling.cpp](check_photon_sampling.cpp) | Compare photon-sampling support and event schemas. |

The shared kinematics header is under [`../include/`](../include/README.md). Each executable reports its arguments when invoked without inputs.

Plotting code lives beside each [figure](../figures/README.md). The exact production drivers and configurations used to obtain the published numerical tables are retained under [`../provenance/`](../provenance/README.md); these require raw production inputs beyond the compact statistical data package.
