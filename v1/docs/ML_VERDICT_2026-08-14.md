# Final fair test of ML versus optimized cuts

**Date:** 14 August 2026  
**Status:** frozen numerical result; conditional parton-level interpretation

## Question

Does a boosted decision tree (BDT) improve the signal-versus-background
selection compared with a strong rectangular-cut method when both methods use
the same recoil-electron information, event samples, weights, and optimization
objective?

## Test design

The primary BDT and rectangular selector used only
`log10(Qe2)`, recoil-electron `pT`, `eta`, and energy. Exact generator-level
`QA2` was excluded from the primary claim.

- The full sealed scan covered 11 masses for vector signals and 11 masses for
  scalar signals.
- Training fitted each method, validation selected the BDT profile/threshold
  and rectangular bounds, and an independent sealed sample was used once for
  the final comparison.
- Four frozen BDT profiles were compared with weighted, multistart rectangular
  searches at 40, 80, and 160 threshold-grid resolutions.
- The full scan used paired event bootstraps and a 22-test Bonferroni lower
  bound.
- A separate robustness study repeated the complete generation, training,
  validation, and test procedure ten times at four predeclared benchmarks.
  It contained 40 independent benchmark replicas, 2,000 paired bootstrap
  samples per replica, and 20,000 hierarchical bootstrap draws per benchmark.
- Method and result checksum manifests were verified. All 40 replicas and all
  80,000 hierarchical draws were present, and no bootstrap draw was invalid.

The comparison endpoint was

`RZ ratio = RZ_BDT / RZ_rectangular`,

with the relative coupling-threshold proxy

`coupling advantage = 1 - sqrt(RZ_rectangular / RZ_BDT)`.

Positive values favor the BDT. A +1% coupling advantage was fixed in advance
as the minimum practically useful improvement.

## Full mass-scan result

Across all 22 electron-only vector/scalar points:

- the nominal coupling difference ranged from -0.228% to +0.161%;
- no point had a positive familywise-controlled lower bound;
- no point reached the +1% practical-improvement threshold;
- the largest nominal positive result, scalar 1.585 GeV, was +0.161%, with a
  pointwise 95% interval of [+0.033%, +0.289%] but a familywise lower bound of
  -0.026%; and
- at some points the optimized rectangular selector was slightly better.

Therefore the full scan provides no multiplicity-controlled evidence that the
electron-only BDT is better than the rectangular selector.

## Independent-seed result

The table reports the hierarchical bootstrap median and 95% interval. The win
count is the number of the ten complete replicas in which the BDT's nominal
`RZ` exceeded the rectangular result.

| Signal | Mass [GeV] | Coupling advantage | BDT wins | Conclusion |
|---|---:|---:|---:|---|
| Vector | 1.00 | -0.009% [-0.029%, +0.004%] | 4/10 | practical equivalence |
| Vector | 10.00 | -0.057% [-0.142%, +0.021%] | 2/10 | practical equivalence |
| Scalar | 1.00 | +0.031% [-0.083%, +0.132%] | 8/10 | practical equivalence |
| Scalar | 6.31 | -0.088% [-0.182%, -0.005%] | 0/10 | cuts slightly favored, but practically equivalent |

None of the four familywise lower bounds was above zero, and none was above
+1%. Even familywise-adjusted equivalence bounds remained inside -1% to +1%.
The selected BDT profiles and rectangular grid sizes changed across replicas,
but the near-unity performance ratio did not. This shows that the conclusion
is not produced by one lucky seed or one chosen model depth.

Both methods did improve the scalar proxy relative to leaving the Table-I
preselection unchanged at some masses. For example, their geometric-mean `RZ`
values were about 1.047 at scalar 1 GeV and 1.022--1.024 at scalar 6.31 GeV.
The optimized rectangular selector captured essentially all of that gain, so
it is not an ML-specific improvement.

## Exact-`QA2` oracle test

When exact generator-level nuclear momentum transfer was added, the BDT had a
small high-mass advantage over a rectangular selector using the same added
information:

- vector 10 GeV: +1.14% [ +0.96%, +1.32% ];
- scalar 10 GeV: +1.37% [ +1.15%, +1.59% ].

This establishes that perfect nuclear-recoil information contains useful
high-mass separation and that a nonlinear classifier can extract slightly more
of it. It is an oracle result, not an experimental claim: `QA2` is exact
generator truth here, with no recoil reconstruction, acceptance, or detector
resolution model. It was also not part of the primary multiplicity-controlled
family or the ten-seed study.

## Verdict

**With the available recoil-electron variables, the BDT is not better than a
properly optimized rectangular selector.** The supported result is practical
equivalence, with differences much smaller than 1%. The earlier 11.8% claim
compared a truth-assisted BDT with the unrefined Table-I baseline and is not a
fair measure of an electron-only ML advantage.

Publication-safe wording is:

> On independently generated weighted parton-level samples conditional on the
> published Table-I preselection, boosted decision trees using recoil-electron
> variables do not outperform a strong multistart rectangular refinement.
> Across the full scalar/vector mass scan there is no
> multiplicity-controlled evidence of ML superiority, and independent-seed
> studies at four benchmarks find practical equivalence at substantially
> better than the 1% coupling level. Exact generator-level nuclear-recoil
> information produces additional high-mass discrimination, but this is an
> oracle result rather than an experimental projection.

## Limits on the claim

This is a controlled negative/equivalence result for the implemented
parton-level proxy. It is not yet an EIC sensitivity or coupling-reach result
because:

1. the coherent-photon joint distribution has not been independently
   validated and its published one-dimensional marginal comparison is poor;
2. no event-level DIS sample is classified;
3. detector response and nuclear-recoil reconstruction are absent;
4. the selected signal rate still differs from the source paper by about a
   factor of three, although that normalization cancels in this relative
   BDT-versus-cuts comparison;
5. the scalar amplitude lacks an independent analytic or generator
   cross-check; and
6. `RZ` is a background-dominated significance proxy rather than a
   nuisance-aware profile likelihood.

The defensible paper direction is therefore a transparent negative methods
result: optimized cuts saturate the electron-only information in this setup,
while experimentally reconstructible recoil or detector-level information is
the most plausible place to test for genuine ML value next.

## Numerical records

- Full sealed scan: `fair_study/rigorous/final/rigorous_final_metrics.csv`
- Full-scan summary: `fair_study/rigorous/final/rigorous_final_summary.md`
- Ten-seed benchmark summary:
  `fair_study/seed_robustness/run_20260814T063518Z/benchmark_summary.csv`
- Ten-seed narrative summary:
  `fair_study/seed_robustness/run_20260814T063518Z/seed_robustness_summary.md`
- Frozen-method and result manifests are stored beside the corresponding
  outputs.
