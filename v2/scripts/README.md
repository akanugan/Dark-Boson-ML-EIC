# Analysis scripts

Run these commands from `v2/`.

| Script | Purpose |
|---|---|
| [analyze.py](analyze.py) | Paired uncertainty analysis, direct benefits from adding `t`, method contrasts, and photon-loss scenarios. |
| [compare_methods.py](compare_methods.py) | Six-selection summaries relative to the common preselection, checked against the paired contrasts. |
| [plot_results.py](plot_results.py) | Summary plots from numerical tables. |
| [restore_data.py](restore_data.py) | Verify and import the existing v2 release into `results/`. |

## Plot bundled tables

```sh
python3 scripts/plot_results.py --results results
```

For the manuscript layouts, use the [per-figure plotting commands](../figures/README.md).

## Repeat the statistical calculation

First [restore the v2 data package](../DATA_DOWNLOAD.md). Use a copied results directory if you want to preserve the bundled tables while checking their reproduction.

```sh
python3 scripts/analyze.py --results results --summarize-only
python3 scripts/compare_methods.py --results results --workers 4
```

These commands use the saved paired arrays and per-run metrics. They do not generate events, fit models, or choose selections. The nominal calculation uses 220 analyses, 2,000 event resamples per run, and one million combined run/event draws. The 198 contrasts include 66 within-method comparisons of adding `t` and 132 comparisons between methods. The photon-loss aggregate uses 20,000 draws.

The second command requires the complete nominal scan. For the smaller smearing sets, use `analyze.py --results results/smearing/10pct --summarize-only` or the corresponding `20pct` path.

Lightweight checks:

```sh
python3 scripts/analyze.py --self-test
python3 scripts/compare_methods.py --self-test
```

Generation, fitting, and validation code is indexed under [`../src/`](../src/README.md). Recorded end-to-end drivers and their original configurations are preserved under [`../provenance/`](../provenance/README.md). Fresh event-level calculations require the raw samples and candidate-model artifacts described there.
