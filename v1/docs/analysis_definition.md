# Analysis definition and scope

## Scientific claim

This project is our parton-level proof of concept for adding a
boosted decision tree to the invisible-dark-boson search proposed by
Davoudiasl and Liu. It is not an exact reproduction of the authors' private
event samples and is not a detector-level sensitivity forecast.

## Signal

Scalar and vector `e Au -> e Au phi` samples use the equations-as-written
implementation frozen under `frozen_baseline/`. The beam energies are 18 GeV
for the electron and 100 GeV per nucleon for gold. The coupling is `1e-4`.
Final ML samples are generated directly in the corresponding corrected Table I
selection region with TFoam importance weights. This improves usable Monte
Carlo statistics without changing the integrated selected cross sections.

## Background

The dominant coherent `e Au -> e Au gamma` background is modeled with the
massless-vector limit of the same exact three-body matrix-element and phase-
space implementation. The photon mass regulator is `1e-6 GeV`, far below the
analyzed scales, and the coupling is the electromagnetic coupling
`e = 0.3028221209`. Events are generated separately inside each Table I region.

The paper's photon-miss prescription is applied event by event: `1e-6` for
central photons and unity for `|eta_gamma| > 3.5`. For absolute yields, each
mass sample is normalized to the corrected Table I effective photon cross
section. The published v2 one-dimensional photon histograms are retained under
`references/published_ancillary_v2`; they are not sufficient to reconstruct
the required joint distribution and are not used for training. As an explicit
validation, the uncut massless-vector sample was compared with those published
marginals. The total-variation distances are 0.715 for
`log10(electron pT)` and 0.409 for electron `eta`. This mismatch is reported as
a leading background-model uncertainty. The marginals are not used to
reweight events because they are inclusive, coarse, and do not resolve the
rare joint tail that survives the Table I cuts.

The DIS effective rate from Table I is included in the significance as a
fully unrejected background after ML. No DIS shape is supplied to the model.
This is conservative and avoids assigning unsupported ML rejection to an
unsimulated process. The irreducible neutrino background is omitted because
the reference paper reports it as negligible.

## Machine learning

A separate gradient-boosted decision tree is trained for every signal type and
mass. The historical full scan uses `log10(Qe2)`, `log10(QA2)`, electron `pT`,
electron `eta`, and electron energy. It is retained as an idealized study of
the value of exact nuclear momentum-transfer information. Generator truth such
as boson mass, pair mass, boson momentum, and class-specific hidden information
is excluded, but `QA2` itself remains exact generator truth.

The primary fair pilot under `fair_study/` trains two explicit modes. The
`electron` mode uses only the four variables present in the Table I selection.
The `electron_qa2` mode adds exact `QA2`. Each BDT is compared with an optimized
rectangular selection receiving the identical feature set. See
`docs/fair_analysis_design.md`.

Each sample requests 30,000 generation attempts for training and a separately
seeded 20,000-attempt evaluation sample. Generator acceptance leaves fewer
stored events; exact tree entries are reported in the metrics. Half of the
evaluation entries select the score threshold; the other half form the
untouched final test sample. All training and metrics use event weights.

The selected threshold maximizes

`R_Z = epsilon_signal * sqrt((sigma_gamma + sigma_DIS) /
      (epsilon_gamma * sigma_gamma + sigma_DIS))`.

The reported coupling improvement follows from `sigma_signal proportional to
g^2`: `1 - 1/sqrt(R_Z)`. Statistical errors reflect weighted test-sample
efficiencies only. They do not include generator, detector, or background-
model systematics.

## Reproducibility boundary

The complete source, event ROOT files, trained XML models, held-out scores,
metrics, and plotting inputs are included. The authors' MadGraph cards,
background events, and detector response were not publicly available as of 13
August 2026. A detector-aware study must replace the present background model
before experimental sensitivity claims are made.
