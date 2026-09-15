# Reproducibility manifest

## Frozen classical reference

The equations-as-written signal baseline is preserved under
`frozen_baseline/`. Its input hashes are recorded in
`docs/baseline_manifest.md`. No factor is applied to force the selected signal
curve onto the published red curve.

## Final ML production

- ROOT/TMVA: local ROOT 6.36 series build
- Signal hypotheses: 11 vector masses and 10 scalar masses
- Training sample: 30,000 weighted events per class and mass
- Evaluation sample: 20,000 separately seeded weighted events per class and
  mass, divided equally into validation and final-test subsets
- Classifier: TMVA BDTG, 400 trees, depth 3, shrinkage 0.05, bag fraction 0.60
- Inputs: `log10(Qe2)`, `log10(QA2)`, `electron_pt`, `electron_eta`, and
  `electron_energy`
- Threshold: selected on validation data by maximizing the stated conservative
  significance ratio
- Final metrics: calculated once on the held-out test subset

The deterministic event seeds and generation commands are contained in
`scripts/run_ml_study.sh`. The merged result contains 21 models, 21 score
files, and 21 numerical metric rows. Run

```bash
python3 scripts/validate_ml_outputs.py
```

to check the final artifacts and formulas.

## Background boundary

The coherent-photon background is our documented massless-vector-limit model.
DIS is not simulated and is left unrejected in the significance calculation.
The old public inclusive photon marginals are stored under
`references/published_ancillary_v2` and checked by
`bin/validate_photon_shapes`. They are not used to tune or reweight the ML
sample.

## Main outputs

- `paper/ML Paper.docx`: final paper-style report
- `results/ml/ml_metrics.csv`: all held-out numerical results
- `results/ml/photon_shape_validation.csv`: public-marginal comparison
- `plots/`: publication figures in PNG and PDF
- `models/`: trained TMVA XML models and held-out score tables
- `data/ml/root/`: generated ROOT event samples
