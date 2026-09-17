# Figure code and data

- [Figure 1: diagrams](01_diagrams/)
- [Figure 2: cross sections](02_cross_sections/)
- [Figure 3: photon shapes](03_photon_shapes/)
- [Figure 4: kinematics](04_kinematics/)
- [Figure 5: mass scan](05_mass_scan/)
- [Figure 6: roc](06_roc/)
- [Figure 7: importance](07_importance/)
- [Figure 8: independent runs](08_independent_runs/)

Each folder holds its plotting macro, small numerical inputs, and rendered figure. Figure 1 has only a rendered diagram. Large ROOT files and trained models remain in the data-v1 release. Figures 3, 4, and 6 retain their event-level reproduction paths; their CSV files are also included for direct inspection. No manuscript source or manuscript PDF is included.

## Exact reproduction check

Figures 2-8 were regenerated and compared with the exact assets included by the manuscript's `main.tex`. All seven passed exact RGB-pixel comparison. PNGs were compared at native resolution; PDFs (Figures 5 and 8) were rasterized at 160 dpi with the same Poppler renderer. PDF binary hashes can differ because of creation timestamps, even when rendered figures are identical.

Run from the repository root after restoring release events/models:

```sh
python3 figures/verify.py --report /tmp/figure-verification.json
```

The verifier builds in a temporary directory and leaves the checked-in figures untouched. Use `--project-root /path/to/project` if the large data and models are in another checkout. It requires ROOT/TMVA, a C++ compiler, Matplotlib, Pillow, and `pdftoppm` on PATH. The recorded run used ROOT 6.36.04, Matplotlib 3.11.2, Pillow 12.3.0, and Poppler 26.07.0. Different renderer/font versions may change pixels. See `verification.json` for the measured hashes.

Figure 1 is the exact manuscript image, but cannot be regenerated from drawing commands because its editable source was not found. It is excluded from the macro verification.
