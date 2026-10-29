# Three-method revision study

Configuration fixed before evaluating the new likelihood on test samples.

* Scalar and vector bosons: 0.010, 0.032, 0.100, 0.316, 1.000, 1.585,
  2.512, 3.981, 5.000, 6.310, 10.000 GeV. Ten independently generated
  train/validation/test sets at every point. Existing sets with the same event
  budgets are reused where available; provenance and SHA256 hashes are recorded.
* Each run uses 30,000 training, 20,000 validation, and 20,000 test generation
  attempts per class, 1,000 TFoam cells and 300 samples. The number of stored
  events can be smaller. All methods see exactly the same events and weights.
* Two input sets: log10(Qe2), electron pt, eta, energy; and those inputs plus
  log10(QA2), where QA2 is the positive nuclear momentum-transfer variable t.
* Primary photon rates are our calculated effective rates from
  results/background_comparison/bg_compare.csv. The fixed published DIS rates
  remain unrejected for all three methods. This is not an event-level DIS study.
* BDT candidates: existing depth2, depth3, depth4, depth3_800 configurations.
* Likelihood: ROOT 6.36 TMVA PDERS, a joint multidimensional density estimator.
  Fixed RMS-scaled search volume, Gaussian kernel (sigma 0.3), normalized class trees.
  Four candidate widths: 0.2, 0.4, 0.8, 1.6 times each variable’s mean within-class RMS.
  An adaptive-volume technical pilot failed to converge reliably and was discarded
  before any likelihood test result was evaluated; fixed volumes avoid that solver.
  The reader explicitly refreshes parsed PDERS options after XML loading because
  ROOT 6.36 otherwise retains default internal mode/kernel enums. Both validation
  and test readers apply this correction. Earlier technical-pilot outputs are
  excluded from the study.
  The output estimates a signal-versus-photon density ratio. It incorporates
  correlations, but remains an estimated likelihood, not an exact matrix-element
  likelihood. Density estimation uses labeled simulation; do not claim that this
  method needs no fitting or that all possible likelihood methods were tested.
* Rectangles: existing optimizer, quantile grids 40, 80, 160, 20 restarts each.
* Candidate and threshold selection use validation only, maximizing
  RZ = epsS sqrt((Bphoton + BDIS)/(epsPhoton Bphoton + BDIS)).
  Existing samples have previously been inspected for BDT/cuts, so they are
  independent test samples for fitting, not a newly blinded external dataset.
* Tests are generated/read only after all selections are chosen. The existing
  paired-event evaluator is used for both BDT/cuts and likelihood/cuts with
  identical bootstrap seeds, event order, and 2,000 resamples. Dividing those
  paired ratios yields BDT/likelihood. Any missing draw stops the run.
* Aggregate the log RZ ratios over the ten runs. Report geometric mean ratios,
  95% intervals, and individual-run results. Use 200,000 two-stage resamples
  (resample runs, then a paired test resample within each selected run).
  Treat all 132 comparisons (3 pairs × 22 points × 2 input sets) as one
  multiplicity family. Two-sided Bonferroni intervals use tails 0.025/132.
  Do not report aggregate confirmatory results until all ten runs are complete.
* Reused data are linked rather than copied. Diagnostic training.root files are
  removed after successful fitting; model XML files are losslessly compressed
  after evaluation. Candidate metrics and seeds are retained. Stop new work if
  available disk falls below 4 GiB. Code/binary/configuration hashes prevent
  mixing changed methods into a resumed result directory.

Reference: https://root.cern.ch/download/doc/tmva/TMVAUsersGuide.pdf, section 8.3.

## Manuscript boundaries

Compare our photon rates with the latest reference rates in the background
section without recounting the revision history. The acknowledgment can credit
the discussion and resulting correction. The updated rates do not by themselves
resolve the shape discrepancy. Shape variations, t resolution, and event-level
DIS remain separate reviewer issues; this scan does not resolve them.

The manuscript and submission archive must not be uploaded to GitHub.
