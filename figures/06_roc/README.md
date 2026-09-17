# Figure 6: roc

The `figure` image/PDF is the manuscript figure; `data/` contains its numerical inputs. Existing simulation pipelines remain in their original locations.

The `plot.cpp` entry point generates only this figure. Compile from the repository root:

```sh
c++ -std=c++17 $(root-config --cflags) figures/06_roc/plot.cpp -o /tmp/plot_fig6 $(root-config --libs) -lTMVA
/tmp/plot_fig6 "$PWD" "$PWD/figures/06_roc"
```

Restore the ROOT events and models from the [data-v1 release](https://github.com/iRojae/Dark-Boson-ML-EIC/releases/tag/data-v1) into the repository layout first. The CSV files allow inspection without downloading these larger files.

The macro reads selected-model metadata, trained XML models, and sealed 10 GeV events. `data/roc_t_comparison.csv` records the plotted efficiencies and operating points.
