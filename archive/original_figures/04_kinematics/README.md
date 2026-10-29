# Figure 4: kinematics

The `figure` image/PDF is the manuscript figure; `data/` contains its numerical inputs. Existing simulation pipelines remain in their original locations.

The `plot.cpp` entry point generates only this figure. Compile from the repository root:

```sh
c++ -std=c++17 $(root-config --cflags) figures/04_kinematics/plot.cpp -o /tmp/plot_fig4 $(root-config --libs) -lTMVA
/tmp/plot_fig4 "$PWD" "$PWD/figures/04_kinematics"
```

Restore the ROOT events and models from the [data-v1 release](https://github.com/iRojae/Dark-Boson-ML-EIC/releases/tag/data-v1) into the repository layout first. The CSV files allow inspection without downloading these larger files.

The macro reads sealed photon/vector/scalar event samples at 1 and 10 GeV in `data/ml/sealed/root/`. `data/t_pt_density.csv` contains the resulting normalized two-dimensional bins.
