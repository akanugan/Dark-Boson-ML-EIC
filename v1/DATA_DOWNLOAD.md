# Version 1 data and models

These archives reproduce the **original BDT-versus-cuts study**. For current
results, use the [Version 2 data guide](../v2/DATA_DOWNLOAD.md).

Download the assets from the
[data-v1 release](https://github.com/iRojae/Dark-Boson-ML-EIC/releases/tag/data-v1)
and keep them together inside `v1/`. From the repository root, enter that
directory before verification and extraction:

```sh
cd v1
shasum -a 256 -c SHA256SUMS
tar -xzf events-and-models.tar.gz
cat fair-study.tar.gz.part-* | tar -xz
```

The archives restore `data/`, `models/`, and `fair_study/` inside `v1/`, preserving
the paths expected by the original programs. Some compact result files also
appear in Git and are restored identically by extraction. Allow at least 8 GB
for extracted files, in addition to the downloads.
[`DATA_MANIFEST.csv`](DATA_MANIFEST.csv) records the original path, size, and
SHA-256 checksum of every archived regular file.

The release includes completed original studies and earlier development runs;
consult the original protocols and final-result manifests for their scope.
It does not contain the later likelihood comparison, corrected photon samples,
or current statistical arrays. It also excludes third-party papers.

The per-figure folders include the ancillary histograms used by original
Figure 3. Other historical external-comparison scripts may reference additional
source-machine files that must be obtained from the cited publication.
