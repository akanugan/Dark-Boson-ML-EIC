# Current figure code and data

| Figure | Content | Folder |
|---|---|---|
| 1 | Production diagrams | [01_diagrams](01_diagrams/) |
| 2 | Signal cross sections | [02_cross_sections](02_cross_sections/) |
| 3 | Inclusive photon shapes and reference comparison | [03_photon_shapes](03_photon_shapes/) |
| 4 | Corrected joint kinematic distributions | [04_kinematics](04_kinematics/) |
| 5 | All six selections relative to preselection | [05_selections](05_selections/) |
| 6 | Benefit of adding t within each method | [06_t_gain](06_t_gain/) |
| 7 | Pairwise method comparisons | [07_methods](07_methods/) |
| 8 | Signal–photon efficiency curves | [08_roc](08_roc/) |
| 9 | BDT variable importance | [09_importance](09_importance/) |

Each folder contains the current rendered figure, its plotting code, numerical inputs and a README. Figure 1 is an image asset because its editable drawing source was not available. Figures 2–3 are unchanged from the original submission; Figures 4–9 use the corrected comparison. Earlier Figure 4–8 files are retained under [v1/figures](../../v1/figures/).

Figures 2 and 5–9 can be plotted directly from included CSV inputs with NumPy and Matplotlib. Figure 4 draws the included binned data using ROOT and a C++17 compiler, without event downloads. Figure 3’s original ROOT macro reads the inclusive sample in the historical `data-v1` release; its reference histograms and binned comparison are also included for inspection. Refer to each folder for exact commands.

## Verification

From the `v2/` directory:

```sh
python3 figures/verify.py --project-root ../v1 --report /tmp/figure-check.json
```

Restore the original `data-v1` release under `v1/` first. The command reads `../v1/data/ml/validation/photon_inclusive.root`, the unchanged Figure 3 inclusive sample; see the [data download guide](../DATA_DOWNLOAD.md). Its reference histograms and binned comparison are already bundled in the figure folder. To verify all other figures without that sample, add `--skip-legacy`. ROOT is still required for Figure 4. The verifier uses temporary output directories and leaves the checked-in figures unchanged. It compares PNGs at native resolution and PDFs rendered at 160 dpi using Poppler. PDF timestamps may differ even when the rendered pixels match exactly. Renderer, font and library versions can affect pixel identity.

See `verification.json` and the individual figure verification records for the measured results. No manuscript source or complete manuscript PDF is distributed here.
