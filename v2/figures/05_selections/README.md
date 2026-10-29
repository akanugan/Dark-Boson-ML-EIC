# Figure 5: six selections

`figure.pdf` and `figure.png` are the exact current figure assets.

`data/selections.csv` contains all 132 boson/mass/input/method results. The vertical quantity is RZ = Z_selected/Z_preselection, where Z is approximated by S/sqrt(B). Each mass has one common preselection. Means are geometric means across ten independent runs; intervals are pointwise 95%. The same paired run/event draws underlie the contrast plots.

## Reproduce

Dependencies: Python 3, NumPy, and Matplotlib.

Run from the `v2/` directory:

```sh
python3 figures/05_selections/plot.py --output-dir /tmp/dark-figure5
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
