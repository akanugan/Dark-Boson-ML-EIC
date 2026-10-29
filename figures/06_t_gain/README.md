# Figure 6: benefit of t

`figure.pdf` and `figure.png` are the exact current figure assets.

`data/t_gain.csv` contains 66 within-method contrasts: 100*(RZ_with_t/RZ_electron_only - 1), for three methods, eleven masses, and two boson types. Plotted bars are pointwise 95% intervals. Family-adjusted bounds in the CSV use the full 198-comparison family; they are not the displayed bars.

## Reproduce

Dependencies: Python 3, NumPy, and Matplotlib.

From any working directory, run the script by its path. For example, from the repository root:

```sh
python3 figures/06_t_gain/plot.py --output-dir /tmp/dark-figure6
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
