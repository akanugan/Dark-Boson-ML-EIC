# Figure 8: signal and photon efficiencies

`figure.pdf` and `figure.png` are the exact current figure assets.

`data/roc_curves.csv.gz` contains every vertex of the eight weighted ROC curves, without downsampling. `roc_auc.csv` gives their areas; `roc_cuts.csv` gives the four validation-selected rectangular operating points. All use the first corrected independent test run at 10 GeV. DIS is absent from this photon-efficiency plot but remains in the selection objective. The script checks each AUC against its full curve.

## Reproduce

Dependencies: Python 3, NumPy (with trapezoid support), and Matplotlib.

Run from the `v2/` directory:

```sh
python3 figures/08_roc/plot.py --output-dir /tmp/dark-figure8
```

The script writes `figure.pdf` and `figure.png` to the chosen directory. Without
`--output-dir`, it uses a local `generated/` directory and leaves the checked-in
reference assets unchanged. All required plotting inputs are in this folder;
no training, simulation, or model files are needed. Numerical values are fixed
inputs from the completed study, not recomputed statistical inference.
Different graphics-library/font versions can change pixels while preserving the data.

## Verification

`verification.json` records exact native PNG RGB equality and exact PDF-rendered
RGB equality at 160 dpi against the current figure assets. Every comparison had
zero differing pixels. It also records source hashes and graphics-library versions.
