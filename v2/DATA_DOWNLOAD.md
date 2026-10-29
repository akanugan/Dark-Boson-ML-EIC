# Study data and model download

The bundled [results](results/README.md) and [figure inputs](figures/README.md) support inspection and plotting. The [v2 data package](https://github.com/iRojae/Dark-Boson-ML-EIC/releases/tag/revision-data-v2) adds paired statistical arrays, all 220 nominal analyses, 40 smearing analyses, and 880 selected BDT/likelihood XML models.

Download all nine release assets into `v2/downloads/`, then run from `v2/`:

```sh
python3 scripts/restore_data.py --downloads downloads
```

The importer verifies the release archives and their member checksums, then places the analysis inputs under `results/`. The existing release filenames and archive paths are retained for compatibility; the importer translates their internal layout. It keeps the bundled results README and stores the release's older README with its import record instead.

Allow about 10 GB for downloads and extracted files. The package excludes raw ROOT events, raw event-level scores, and unselected candidate models. It supports [statistical replay](scripts/README.md); prediction on events, refitting, or repeating production requires the corresponding raw inputs.

## Inclusive photon sample for Figure 3

Restore the original [v1 data package](https://github.com/iRojae/Dark-Boson-ML-EIC/releases/tag/data-v1) under `v1/` using [its guide](../v1/DATA_DOWNLOAD.md). Figure 3 then reads `../v1/data/ml/validation/photon_inclusive.root`. Its reference histograms and plotted binned distributions are included under [`figures/03_photon_shapes/`](figures/03_photon_shapes/README.md); no trained models are needed.

All other figures use their bundled inputs and the dependencies listed in their READMEs.
