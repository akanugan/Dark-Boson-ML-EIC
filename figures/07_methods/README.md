# Figure 7: method comparisons

`figure.pdf` and `figure.png` are the exact current figure assets.

`data/comparisons.csv` contains 132 paired contrasts: 100*(RZ_first/RZ_second - 1), for three method pairs, two input sets, eleven masses, and two boson types. Positive values favor the numerator method. Plotted bars are pointwise 95% intervals; the additional family-adjusted bounds use the full 198-comparison family.

## Reproduce

Dependencies: Python 3, NumPy, and Matplotlib.

From any working directory, run the script by its path. For example, from the repository root:

```sh
python3 figures/07_methods/plot.py --output-dir /tmp/dark-figure7
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
