# Figure 3: photon shapes

The `figure` image/PDF is the manuscript figure; `data/` contains its numerical inputs. Existing simulation pipelines remain in their original locations.

The `plot.cpp` entry point generates only this figure. Compile from the repository root:

```sh
c++ -std=c++17 $(root-config --cflags) figures/03_photon_shapes/plot.cpp -o /tmp/plot_fig3 $(root-config --libs) -lTMVA
/tmp/plot_fig3 "$PWD" "$PWD/figures/03_photon_shapes"
```

Restore the ROOT events and models from the [data-v1 release](https://github.com/iRojae/Dark-Boson-ML-EIC/releases/tag/data-v1) into the repository layout first. The CSV files allow inspection without downloading these larger files.

`compare.cpp` reads `data/ml/validation/photon_inclusive.root` and the two reference `.dat` histograms to produce `data/distributions.csv`. Each histogram is normalized separately in the displayed range. The reference data were supplied as the original paper’s public ancillary histograms (local provenance: `references/published_ancillary_v2`; original Figure 4). They are reference-author data, not newly generated results. The photon generator is `src/generate_vector.cpp`.

```sh
c++ -std=c++17 $(root-config --cflags) figures/03_photon_shapes/compare.cpp -o /tmp/compare_photon $(root-config --libs)
/tmp/compare_photon data/ml/validation/photon_inclusive.root figures/03_photon_shapes/data/Fig4_pt_photon.dat figures/03_photon_shapes/data/Fig4_eta_photon.dat figures/03_photon_shapes/data/distributions.csv
```
