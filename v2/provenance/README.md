# Recorded workflows and numerical checks

The main study is organized under [`../figures/`](../figures/README.md), [`../src/`](../src/README.md), [`../scripts/`](../scripts/README.md), and [`../results/`](../results/README.md).

`workflow/` preserves the previous execution tree, including production drivers, earlier pilots, integration diagnostics, sampling checks, protocols, and original source-export records. Its filenames, embedded source-machine paths, and checksums describe those recorded calculations. They are retained literally rather than rewritten as new runs.

The public code locations are recorded in [PATH_MAP.json](PATH_MAP.json). Renamed public statistical scripts change module names, default paths, and documentation; their numerical calculations are unchanged. The public C++ sources retain the recorded implementations, with the local include path updated for `select_thresholds.cpp`.

Useful records:

- [Production and fitting drivers](workflow/scripts/README.md).
- [Recorded protocols](workflow/protocols/README.md).
- [Numerical checks](workflow/checks/README.md).
- [Photon-integration diagnostics](workflow/rate_benchmark/README.md).
- [Original source export manifest](workflow/EXPORT_MANIFEST.csv).

The export manifest's `revision/...` paths map to `provenance/workflow/...` here. Source-path columns and embedded timestamps remain historical provenance. The recorded drivers need the full raw production inputs and their original relative layout; the compact release supports saved-array analysis and selected models only.

Some links inside checksum-protected reports refer to local audit notes or plots that were not included in the public export. They are historical references, not additional public inputs. Manuscript files are excluded.
