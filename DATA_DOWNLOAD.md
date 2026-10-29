# Data availability and downloads

## Current corrected comparison

The compact results in [`revision/stratified_repair/`](revision/stratified_repair/) and the inputs under [`figures/`](figures/) are sufficient to inspect the reported comparisons and regenerate the associated summary plots. They include the six photon-sampling repairs, both input sets, and the three selection methods. See the [current analysis guide](docs/current-analysis.md).

The [revision-data-v2 release](https://github.com/iRojae/Dark-Boson-ML-EIC/releases/tag/revision-data-v2) contains the current paired statistical records and selected models. It includes all 220 nominal analyses, 40 smearing analyses, and 880 selected BDT/likelihood XML models. The release materializes the corrected overlay as regular files; it contains no broken source-machine symlinks.

Download all release assets into a separate `revision-download/` folder inside the repository. This keeps the release's README separate from the repository README. From the repository root:

```sh
(cd revision-download && shasum -a 256 -c SHA256SUMS)
for file in revision-download/revision-*.tar.gz; do
    tar -xzf "$file"
done
shasum -a 256 -c revision-download/FILES_SHA256SUMS
```

Allow about 10 GB of free space for downloads and extracted files. `INVENTORY.json` records archive membership, source provenance, sizes, and SHA-256 checksums.

The package restores `revision/stratified_repair/`. It is sufficient to replay aggregate estimates and intervals from the saved paired arrays. See [reaggregation commands](revision/scripts/README.md). Use a copied extraction for tests because the commands write aggregate CSV files.

Raw training/validation/test ROOT events, raw event-level scores, and unselected model weights are excluded. Repeating event-level prediction or fitting requires those current inputs or regeneration through the scientific code. The earlier `data-v1` release does not contain those later raw samples. The code, configuration, protocols, and numerical checks are under [`revision/`](revision/README.md).

## Original study: data-v1

Download the archives and `SHA256SUMS` from the [data-v1 release](https://github.com/iRojae/Dark-Boson-ML-EIC/releases/tag/data-v1). Keep them together in the repository root and verify:

```sh
shasum -a 256 -c SHA256SUMS
```

Restore the original events and models:

```sh
tar -xzf events-and-models.tar.gz
```

Restore the original fair-comparison studies:

```sh
cat fair-study.tar.gz.part-* | tar -xz
```

These archives restore `data/`, `models/`, and `fair_study/`. Allow at least 8 GB for extraction, in addition to the downloaded archives. [`DATA_MANIFEST.csv`](DATA_MANIFEST.csv) records their original regular-file paths, sizes, and SHA-256 checksums. Some files also appear in Git and are restored identically by extraction.

The archives include historical development runs. They do not contain the current stratified photon samples, corrected models, or updated paired bootstrap outputs. Third-party papers are excluded; consult each figure's README for reference-distribution sources.
