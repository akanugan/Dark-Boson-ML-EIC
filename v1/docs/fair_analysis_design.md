# Fair parton-level ML analysis design

## Question

Using the same weighted parton-level events and the same recoil-electron
information, does a boosted decision tree improve sensitivity beyond an
optimized rectangular selection?

This question tests event-selection performance. It does not test detector
simulation speed or claim detector-level EIC sensitivity.

## Common starting sample

Signal and coherent-photon events are importance-generated inside the corrected
Table I mass-dependent selection. Table I is therefore a common preselection.
All efficiencies and improvement factors reported by this fair study are
conditional on that preselection.

Because events outside Table I are absent, the rectangular optimizer can refine
the published selection but cannot loosen or replace it. Replacing Table I
would require new samples generated over a broader phase-space region.

## Feature sets

The primary `electron` comparison uses exactly four quantities:

1. `log10(Qe2)`
2. recoil-electron `pT`
3. recoil-electron `eta`
4. recoil-electron energy

The secondary `electron_qa2` comparison adds exact generator-level
`log10(QA2)`. It measures the idealized value of nuclear momentum-transfer
information. It must not be described as experimentally measurable without a
separate reconstruction and resolution study.

For each feature set, the BDT and rectangular optimizer receive identical
inputs.

## Independent samples

Generation requests 30,000 training attempts and 20,000 separately seeded
evaluation attempts per class. Generator acceptance leaves fewer stored tree
entries; exact counts are written to the result table. The evaluation sample is
split deterministically into two disjoint subsets:

- even entries: threshold or rectangular-bound optimization;
- odd entries: final held-out evaluation.

No final-test event selects a threshold or rectangular boundary.

## Metric

Both methods maximize the same parton-level proxy

`R_Z = epsilon_signal * sqrt((sigma_gamma + sigma_DIS) /
      (epsilon_gamma * sigma_gamma + sigma_DIS))`.

The coherent-photon efficiency is evaluated event by event. The corrected
Table I DIS rate is kept fully unrejected because no event-level DIS sample is
available. Coupling improvement relative to another selection follows from
`sigma_signal proportional to g^2`.

## Interpretation boundary

This design fixes feature fairness, sample separation, and weighted evaluation.
It does not fix the known photon-shape mismatch, missing event-level DIS,
selected-signal discrepancy, scalar-amplitude validation, or detector effects.
Results remain model-dependent parton-level evidence.

Before a million-event production run, require stable conclusions at several
sample sizes and random seeds. More events reduce Monte Carlo noise; they do
not repair modeling bias.
