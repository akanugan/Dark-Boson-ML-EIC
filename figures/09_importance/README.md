# Figure 9: BDT input importance

`figure.pdf` and `figure.png` are the exact current figure assets.

`data/importance.csv` records the normalized variable importances printed in the original TMVA training logs for twenty validation-selected t-inclusive BDTs at 10 GeV: ten runs per boson type. Values retain the logs' printed precision. `importance_summary.csv` records means and sample standard deviations. These model-dependent scores reflect correlated inputs; they are not independent measures of physical information.

## Reproduce

Dependencies: Python 3, NumPy, and Matplotlib.

From any working directory, run the script by its path. For example, from the repository root:

```sh
python3 figures/09_importance/plot.py --output-dir /tmp/dark-figure9
```

The script writes `figure.pdf` and `figure.png` to the chosen directory. Without
`--output-dir`, it uses a local `generated/` directory and leaves the checked-in
reference assets unchanged. All required plotting inputs are in this folder;
no training, simulation, or model files are needed. Numerical values are fixed
inputs from the completed corrected study, not recomputed statistical inference.
Different graphics-library/font versions can change pixels while preserving the data.

## Verification

`verification.json` records exact native PNG RGB equality and exact PDF-rendered
RGB equality at 160 dpi against the current figure assets. Every comparison had
zero differing pixels. It also records source hashes and graphics-library versions.
