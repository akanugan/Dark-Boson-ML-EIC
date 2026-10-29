# v2 data download and statistical replay

The committed [`revision/stratified_repair/`](revision/stratified_repair/README.md) tables and [`figures/`](figures/README.md) inputs support inspection and current comparison plots. The [revision-data-v2 release](https://github.com/iRojae/Dark-Boson-ML-EIC/releases/tag/revision-data-v2) additionally provides paired statistical records, all 220 nominal analyses, 40 smearing analyses, and 880 selected BDT/likelihood XML models.

Download all release assets into `v2/revision-download/`. From the repository root:

```sh
cd v2
(cd revision-download && shasum -a 256 -c SHA256SUMS)
for file in revision-download/revision-*.tar.gz; do
    tar -xzf "$file"
done
shasum -a 256 -c revision-download/FILES_SHA256SUMS
```

Allow about 10 GB for downloads and extracted files. `INVENTORY.json` records archive membership, sizes, provenance, and SHA-256 checksums. The archives are unchanged: their `revision/...` paths are relative to `v2/`. They restore `v2/revision/stratified_repair/`, including regular copies of the original corrected overlay's files.

Use the [reaggregation commands](revision/scripts/README.md) on a copied extraction; they overwrite aggregate tables. Statistical replay requires neither ROOT nor event generation. It reproduces the saved-array uncertainty calculation, not the original event generation or model fitting.

Raw training/validation/test ROOT files, raw event-level scores, and unselected candidate models are excluded. Event-level prediction, refitting, or repeating the repair requires those corresponding inputs or the generation workflow. Original `data-v1` events are not a replacement for the later v2 samples.

## Original inclusive sample for current Figure 3

Figure 3 is unchanged from v1 and still reads `data/ml/validation/photon_inclusive.root`. Restore the original [data-v1 release](https://github.com/iRojae/Dark-Boson-ML-EIC/releases/tag/data-v1) under `v1/` following [its download guide](../v1/DATA_DOWNLOAD.md). Current Figure 3 can then use `../v1` as its project root, without duplicating the event file. Reference histograms and the plotted binned distributions are bundled under [`figures/03_photon_shapes/`](figures/03_photon_shapes/README.md); trained models are not required.

Current figures other than Figure 3 do not require the original release. The current analysis is described in [`docs/current-analysis.md`](docs/current-analysis.md).
