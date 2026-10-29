# Preregistered conditional ML-versus-cuts test

Date frozen: 14 August 2026.

## Scope

This protocol tests algorithmic event selection only on our weighted
parton-level signal and coherent-photon proxy after the published Table I
preselection. It does not test detector performance, event-generation speed,
or real EIC reach. DIS remains an externally normalized, fully unrejected term.

## Primary and secondary questions

Primary: using only `log10(Qe2)`, recoil-electron `pT`, `eta`, and energy, does
a BDT outperform a rectangular selector fitted with the same events and inputs?

Secondary oracle: repeat after adding exact generator-level `log10(QA2)`. This
tests the value of perfect nuclear-recoil information and is not an observable
detector claim.

## Data roles

For every class and mass, generation seeds define disjoint training,
validation, and sealed final-test ROOT files.

- Training fits BDT structure and generates rectangular candidates.
- Validation chooses BDT profile, BDT score threshold, and rectangular
  candidate.
- Sealed final test is evaluated once after methods and scripts are frozen.

Previously inspected test files are development validation only. They are not
used as final evidence.

## BDT search fixed before sealed testing

Four TMVA BDTG profiles are considered: 400 trees with maximum depths 2, 3,
and 4, plus 800 trees with maximum depth 3. All use shrinkage 0.05, minimum node
size 2.5%, bag fraction 0.6, and 30 cut points. Validation `R_Z` selects one
profile and one score threshold per signal, mass, and feature set.

## Rectangular search fixed before sealed testing

Separate threshold grids use 40, 80, and 160 weighted quantiles with signal
and photon classes given equal total grid weight. Candidate boxes come from
every cyclic and reversed feature order plus 20 deterministic multistarts.
Coordinate searches use at most six passes. Training generates candidates;
validation chooses both the grid resolution and the candidate. The method is a
strong multistart rectangular baseline, not a proof of the global mathematical
optimum.

## Endpoint and decision rule

For each sealed test sample,

`G = 1 - sqrt(R_box / R_BDT)`

is the BDT coupling-threshold advantage over the rectangular selector. Paired
event bootstrap intervals preserve correlation between both selections.

- A predeclared single benchmark would use the one-sided 95% bootstrap lower
  limit (the 5th percentile) for `G`.
- Because no single mass was predeclared here, the 22 electron-only mass/spin
  tests form one primary family. The mass-scan evidence threshold is the
  conservative Bonferroni lower quantile at `0.05/22`.
- Practical improvement requires the applicable lower limit above +1%
  coupling and consistent independent-seed behavior.
- The exact-`QA2` oracle scan is secondary/descriptive and cannot establish an
  experimental ML advantage.
- If the interval crosses zero, report no evidence that ML is better.
- Practical equivalence requires the 90% interval to lie inside -1% to +1%
  and must also be stable across independent seeds.

## Mandatory qualifications

Regardless of algorithmic outcome, conclusions remain conditional because the
photon joint distribution is unvalidated, event-level DIS is absent, selected
signal normalization differs from the source paper, scalar amplitude lacks an
independent check, and detector effects are absent. No rescaling or invented
detector resolution is introduced to hide these limitations.
