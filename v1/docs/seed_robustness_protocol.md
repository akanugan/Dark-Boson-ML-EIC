# Seed-robust benchmark protocol

## Purpose

`scripts/run_seed_robustness.sh` tests whether a BDT improves the same
parton-level significance proxy as a fitted rectangular selector. It runs four
benchmarks: vector masses 1 and 10 GeV, and scalar masses 1 and 6.31 GeV. The
primary feature set contains only `log10(Qe2)`, recoil-electron `pT`, `eta`, and
energy. Exact generator-level `QA2` is excluded.

## Sealed data roles

Every benchmark and complete replica receives fresh, independent signal and
photon seeds.

1. The training files fit BDT structure and generate rectangular candidates.
2. The validation files select one of the four frozen BDT profiles, its score
   threshold, and one rectangular candidate.
3. Test files are generated only after both selections are frozen. The selected
   BDT and box are evaluated together once on those same test events.

The frozen BDT profiles are 400 trees at depths 2, 3, and 4, plus 800 trees at
depth 3. Their common settings remain those recorded in `train_tmva.cpp`. The
rectangular fit uses 40, 80, and 160 weighted-threshold grids with
deterministic multistarts; validation selects the grid and candidate.
Both methods receive the same training, validation, test events, weights,
inputs, and significance objective.

Within one benchmark replica, every frozen BDT profile also receives the same
TMVA random seed. Complete replicas change that seed together with all event
generation seeds.

`optimize_rectangular_fair` requires test-file positional arguments. The runner
deliberately supplies the validation files in those two slots. Its interim
test-number columns are ignored; only validation-selected bounds are retained.
The sealed test files do not exist until after this command completes.

## Uncertainty and decision rule

Within each complete replica, event resampling is paired: every resampled event
carries both its BDT and box decisions. The final summary performs a
hierarchical bootstrap by resampling complete generator/training replicas and
then a paired event-bootstrap draw within each selected replica.

The direct endpoint is

`RZ ratio = RZ_BDT / RZ_box`,

with coupling-threshold advantage

`1 - sqrt(RZ_box / RZ_BDT)`.

A one-sided familywise lower limit uses the conservative Bonferroni quantile
`0.05/4` for the four predeclared benchmarks. A limit above zero is statistical
evidence for the BDT; a limit above +1% is the preregistered practical-
improvement threshold. An interval contained within -1% to +1% is reported as
practical equivalence. At least ten complete replicas are
required; more are needed when sub-percent effects remain unresolved.

## Running

Run from any directory with:

```text
bash /Users/rojaemighty/Dark/scripts/run_seed_robustness.sh
```

Important controls are `ROBUST_REPLICATES`, `ROBUST_TRAIN_EVENTS`,
`ROBUST_VALIDATION_EVENTS`, `ROBUST_TEST_EVENTS`, `ROBUST_PAIRED_BOOTSTRAPS`,
`ROBUST_AGGREGATE_BOOTSTRAPS`, `ROBUST_SEED_BASE`, and `ROBUST_RUN_ID`.
Replicas below ten are rejected. A run never overwrites an existing run
directory.

Each run writes its configuration, complete seed manifest, per-replica paired
metrics, event-level bootstrap distributions, hierarchical bootstrap,
benchmark summary, and a concise Markdown verdict under
`fair_study/seed_robustness/<run-id>/`.

## Interpretation boundary

This remains conditional evidence after Table I preselection. It does not fix
the photon-shape mismatch, absent event-level DIS, selected-signal discrepancy,
scalar-amplitude validation, or missing detector response. No result from this
runner alone is a detector-level EIC sensitivity projection.
