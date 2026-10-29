# EIC invisible dark-boson selection study

Code, numerical results, and figure inputs for invisible scalar and vector dark-boson searches at the Electron-Ion Collider. The manuscript is not distributed here.

| Version | Study | Start here |
|---|---|---|
| **[v1 — original study](v1/README.md)** | BDT versus optimized rectangular cuts, with the original samples, results, and Figure 1–8 layout. | [Code](v1/src/README.md), [figures](v1/figures/README.md), [data download](v1/DATA_DOWNLOAD.md) |
| **[v2 — current study](v2/README.md)** | Rectangular cuts, estimated likelihood, and BDT, each with and without `t`; ten runs at all eleven masses for both boson types, including photon-sampling repairs and response checks. | [Analysis guide](v2/docs/current-analysis.md), [figures](v2/figures/README.md), [data download](v2/DATA_DOWNLOAD.md) |

Use **v2** for the current results. Each version keeps its own code, configuration, numerical tables, and instructions. Run commands from that version's directory; do not combine their results or figure numbers. The shared generators are included in both versions so the current build does not depend on v1 code.

The likelihood implementation is [`v2/revision/src/train_likelihood.cpp`](v2/revision/src/train_likelihood.cpp).

The existing releases are unchanged: [data-v1](https://github.com/iRojae/Dark-Boson-ML-EIC/releases/tag/data-v1) belongs to v1, and [revision-data-v2](https://github.com/iRojae/Dark-Boson-ML-EIC/releases/tag/revision-data-v2) belongs to v2. Current Figure 3 reuses the original inclusive photon event file downloaded under v1.

[VERSION_HISTORY.json](VERSION_HISTORY.json) records the source commits used for this split. Scientific source files, numerical data, and recorded checksums were preserved when creating the version folders.
