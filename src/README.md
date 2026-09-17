# Code guide

- `generate_vector.cpp`: vector signal generator, also used in the massless-vector limit for the photon proxy.
- `generate_scalar.cpp`: scalar signal generator.
- `validate_photon_shapes.cpp`: bins and separately normalizes simulated and reference photon distributions.
- `plot_kinematics_roc.cpp`: photon-shape overlay, joint kinematic distributions, and ROC curves.
- `plot_tmva_importance.cpp`: BDT variable importance.
- `../scripts/plot_bdt_comparison.py`: BDT-versus-cuts mass scans and independent-run plots.

## Figure 3

The plotting function is `make_photon_overlay` in `plot_kinematics_roc.cpp`.
It reads `results/ml/photon_shape_validation.csv`, which contains the bin edges and both normalized distributions.
The comparison is calculated by `validate_photon_shapes.cpp` using the inclusive photon sample and the reference histograms.
Each distribution is normalized independently within the displayed range.

The event file is `data/ml/validation/photon_inclusive.root`, distributed through the data-v1 release archives.
The plotting function also reads this event file to calculate the fractions outside the displayed ranges.
The rendered comparison is `plots/revision/photon_shape_overlay.pdf`.

The plotting program was previously named `make_revision_figures.cpp`;
`plot_bdt_comparison.py` was previously `plot_rigorous_ml_verdict.py`.
Only filenames and descriptions have changed; the calculations are unchanged.
