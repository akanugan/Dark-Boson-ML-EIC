# Simulation data

Download all assets from the `data-v1` release. Keep the files together in the project root.

Verify the downloaded archives:

```sh
shasum -a 256 -c SHA256SUMS
```

Restore the event and model directories:

```sh
tar -xzf events-and-models.tar.gz
```

Restore the complete fair-comparison studies:

```sh
cat fair-study.tar.gz.part-* | tar -xz
```

Archives restore `data/`, `models/`, and `fair_study/` without changing the project structure. Some compact result files also appear in Git and will be restored identically by extraction. Allow at least 8 GB of space for extracted files, in addition to the downloads. DATA_MANIFEST.csv records the original path, size, and SHA-256 checksum of every archived regular file.

These archives include both completed studies and historical development runs. Use the protocol and final-result manifests to identify the analysis relevant to the manuscript. They do not include third-party papers or public ancillary reference histograms; obtain those from the cited publication before running the historical external-comparison scripts.
