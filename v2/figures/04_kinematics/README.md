# Figure 4: weighted kinematics

`figure.pdf` and `figure.png` are the exact current figure assets.

`data/bins.csv` contains the exact 36 by 36 displayed-bin probabilities for six panels. `data/flows.csv` records full class weights and probabilities outside the displayed rectangles. Panels use the first corrected test run at 1 and 10 GeV. Photon weights include the photon-miss probability exactly once. The visible bins sum to 100% minus the recorded overflow probability. `draw.cpp` reproduces the original ROOT styling from these bins.

## Reproduce

Dependencies: Python 3, ROOT (root-config on PATH), and a C++17 compiler. No ROOT event files are needed.

Run from the `v2/` directory:

```sh
python3 figures/04_kinematics/plot.py --output-dir /tmp/dark-figure4
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
