# Figure 7: importance

> **OLD STUDY ONLY.** This is the original submission's figure and numbering, superseded by the [current figure guide](../../../figures/README.md). Commands below refer to this archived copy.

The `figure` image/PDF is the manuscript figure; `data/` contains its numerical inputs. Existing simulation pipelines remain in their original locations.

Compile `plot.cpp` with ROOT and run it with the CSV path followed by an output directory. See its usage string. The CSV contains per-run importance values and their summary statistics.

```sh
c++ -std=c++17 $(root-config --cflags) archive/original_figures/07_importance/plot.cpp -o /tmp/plot_importance $(root-config --libs)
/tmp/plot_importance archive/original_figures/07_importance/data/tmva_t_importance_10gev.csv archive/original_figures/07_importance
```
