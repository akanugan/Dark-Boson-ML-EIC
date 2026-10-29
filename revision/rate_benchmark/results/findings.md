# Photon-rate benchmark: findings

**Follow-up completed 27 October 2026:** the six diagnosed production
components and their affected selector results have now been repaired in
[the corrected study view](../stratified_repair/results.md). This report
retains the diagnostic findings that motivated that repair; statements below
about production files not yet being replaced describe the audit stage.

Completed 27 October 2026. This investigation checks numerical integration of
the existing coherent electron-line photon model. It does not fit a result to
the reference, change the physical model, retrain the classifiers or revise
the manuscript.

## Main result

The historical calculation reproduces the old rates exactly, but its adaptive
sampling misses part of the photon contribution outside acceptance. The
outside component of the separate calculation is supported by an independent
CM-coordinate integration using direct random draws without adaptive sampling. The revised
rate is therefore much better justified numerically than the historical
average. The remaining difference from the updated reference is unresolved.

| Electron preselection | Historical mean (pb) | Increased-budget component sum (pb) | Updated reference (pb) | Difference from reference |
|---|---:|---:|---:|---:|
| 0.032 GeV hypothesis | 2.270654 | 2.635673 | 2.06 | +27.9% |
| 10 GeV hypothesis | 0.332670 | 0.350009 | 0.33 | +6.1% |

Reference: [Davoudiasl and Liu, v4, Table I](https://arxiv.org/html/2505.08871v4#S3).
The reference entries are rounded and have no quoted integration errors in the
table. These percentage differences are comparisons of central values, not
tests of statistical agreement. The first four mass hypotheses use identical
photon physics and electron cuts; the low-mass row checks that shared selection,
not four different photon masses.

## Why the historical estimate changed

All calculations target

`sigma_effective = 1e-6 * sigma_central + sigma_outside`,

with central `|eta_gamma| <= 3.5` and outside `|eta_gamma| > 3.5`.

The original executable and commands were recovered and replayed with their
original three seeds. Their outside contributions were:

| Preselection | Seed 1 (pb) | Seed 2 (pb) | Seed 3 (pb) | Independent lab result (pb) |
|---|---:|---:|---:|---:|
| 0.032 GeV | 0.329024 | 0.155176 | 0 | 0.509904 |
| 10 GeV | 0.049951 | 0.045302 | 0.028997 | 0.059106 |

The zero outside component, mirror imbalance in some unfolded samples, and
large variation between seeds demonstrate missed numerical support. This is
more specific evidence than inferring an integration problem from a rate
disagreement. The old calculation already included photon loss during
adaptation and used 250000 production attempts per seed; the issue was not
simply forgetting that loss factor or using fewer production attempts.

The selected outside region is a thin correlated patch in CM coordinates.
Changing only the t sampling did not reliably discover it. Even an exact
full-support joint-box proposal layered under TFoam still underestimated it:
those failed adaptive estimates are retained and explicitly flagged in the
[complete numerical summary](summary.md). They are not averaged into an
accepted rate.

## Independent checks

1. **Pointwise coordinate agreement.** Reconstructing 100 weight-proportional
   outside events per preselection in both lab and historical CM coordinates
   gives density/Jacobian agreement better than 0.003% at all checked points.
   This checks the coordinate normalization where the outside contribution
   is important. It does not independently validate the shared matrix element.
2. **Independent outside integral.** Three fresh seeds with 2000000 direct
   random draws each integrate the original CM formula using a known proposal
   with positive density throughout the full domain. Every zero-density
   attempt enters the ordinary mean and variance; no TFoam adaptation runs.
   Both estimates agree with the lab calculation within their sampling errors.

| Preselection | Lab adaptive mean (pb) | Direct CM mean (pb) | Pooled direct-draw SEM (pb) | SEM from three CM seed means (pb) |
|---|---:|---:|---:|---:|
| 0.032 GeV | 0.509904 | 0.513298 | 0.013373 | 0.018217 |
| 10 GeV | 0.059106 | 0.059903 | 0.001427 | 0.001290 |

   SEM denotes one standard error of the mean, not a 95% interval. The two
   routes are consistent at the achieved precision of this outside check. The
   total-rate estimate in the first table uses the more precise lab component;
   it does not average known failed CM adaptations with these results.
3. **Larger budgets.** Each component was repeated with three fresh seeds,
   1000000 attempts, 5000 cells and 2000 adaptation samples. The resulting
   component sums agree with the smaller-budget estimates at the subpercent
   level across the tested stable maps.
4. **Photon regulator.** Reducing the artificial photon mass from 1e-6 to
   1e-7 GeV gives the following totals:

| Preselection | 1e-6 GeV regulator (pb) | 1e-7 GeV regulator (pb) | Relative change |
|---|---:|---:|---:|
| 0.032 GeV | 2.635673 | 2.635950 | +0.0105% |
| 10 GeV | 0.350009 | 0.349192 | -0.2335% |

   The changes are 0.17 and 0.97 combined empirical seed standard errors.
   There is no resolved regulator effect at this precision. The three-seed
   empirical SEMs of the baseline totals are 0.001442 and 0.000683 pb;
   they are numerical diagnostics, not complete model uncertainties.
   At 10 GeV the regulator difference is much larger than the narrow
   conditional TFoam errors alone. Those internal errors understate the
   observed numerical variation and must not be the sole uncertainty quoted.
5. **Bookkeeping.** All 24 increased-budget/regulator ROOT files have zero
   photon-loss mismatches. Reconstructed weight sums reproduce their stored
   cross sections to relative 1.1e-13. Weighted outside electron energy and eta
   summaries are stable under the regulator change. Algebra, reflection and
   full-domain proposal identities are recorded in the `check_*.json` files.

The physical coupling, nuclear form factor, electron-line amplitude and
phase-space factors are reviewed separately in
[the physics audit](../background_audit/physics.md), the subsequent
[physical-scope review](../background_audit/physical_review.md), and the
[physical mapping review](physical_mapping_review.md). This calculation remains
the specified tree-level coherent model with the assumed photon-loss rule.
The checks above support its numerical evaluation, rather than establishing
the accuracy of all background physics or a detector response.

## Consequences and remaining work

- The prior closeness to the reference is not sufficient evidence that the
  historical mean was accurate: its missed outside contribution is now directly
  demonstrated. No physical parameter was adjusted to restore that closeness.
- The cause of the remaining +27.9% and +6.1% differences from the updated
  reference is not identified by the public table. We cannot attribute it to
  the reference authors' numerical correction or assert their revised result
  has the same sampling problem. Resolving that difference requires a matched
  calculation with further implementation details or event-level information.
- This two-preselection benchmark does not establish convergence at every
  distinct mass-dependent selection, nor does matching a rate validate an
  entire joint background shape.
- Six retained production outside samples also missed support: 1.585 GeV
  training runs 4 and 7 and test run 5; 2.512 GeV test run 5; 5 GeV validation
  run 1; 6.31 GeV validation run 4. Exact-coordinate replays recover the missing
  contribution and agree with fresh seeds; see [support recovery](support_summary.md).
  Affected training/validation selections need renewed fitting or threshold
  selection and evaluation; test-only failures need corrected independent
  evaluation. The complete scan must be updated accordingly before it is
  treated as final. The six flagged files do not include the 10 GeV samples.
- These diagnostic folded-azimuth files have not replaced production events,
  models, calibration rates, confidence intervals or manuscript content.

## Plots and reproducibility

- [Historical component replay versus increased-budget totals](comparison.png).
- [Independent outside-photon integration comparison](outside_check.png).
  Its error bars use the larger of the pooled per-run SEM and the observed
  seed-mean SEM for the direct CM result. They exclude physical-model errors.
- [All finite estimates and support flags](route_summary.csv),
  [every retained integration result](all_integrations.csv),
  [physical component sums](component_sums.csv).
- `protocol.md`, `transformed_protocol.md`, `focused_protocol.md`,
  `support_protocol.md`, `stability_protocol.md`, and `mixture_protocol.md`
  record the successive diagnostic designs. This was a sequential numerical
  investigation, not a preregistered physics analysis.
- `run*.py` reproduce/resume their respective stages with at most four workers;
  each run directory preserves its command, seed, log and result. The direct
  random-draw stage saves rate JSON rather than large event files.
- `sources/` preserves the recovered and diagnostic C++ sources, exact diffs,
  deterministic checks and provenance; `bin/` contains the tested local ROOT
  executables. Environment manifests and result records contain SHA-256 hashes.
- [Independent scientific review](final_review.md).
