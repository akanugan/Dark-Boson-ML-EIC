# Repair of six photon sampling failures

Authorized 27 October 2026. This is a documented numerical correction after
the original held-out results have been inspected, not a new blinded or
preregistered confirmation. No external upload or manuscript change is made.

## Fixed scope

Regenerate only these outside-acceptance photon components, using the same
physical model, electron cuts, integration budgets and original source seeds:

| Mass (GeV) | Independent run | Split |
|---:|---:|---|
| 1.585 | 4 | train |
| 1.585 | 7 | train |
| 1.585 | 5 | test |
| 2.512 | 5 | test |
| 5 | 1 | validation |
| 6.31 | 4 | validation |

The corrected lab sampler uses the exact log-electron-energy mapping and
analytic azimuthal mirror integration checked in `../rate_benchmark`.
Restore a random signed-azimuth mirror after generating each weighted event,
using an independent RNG stream so the density callback and integration RNG
remain deterministic and unchanged. Reflect all final-state y components
together; present classifier inputs remain invariant. Preserve the old ROOT
schema so central and outside components can be merged normally.

Use the original 40000 attempts, 1000 cells and 1000 adaptation samples for
each replacement. Compare rates and weighted distributions with the independent
diagnostic recovery integrations before accepting the replacements. Check
event conservation, photon region/loss, source weight sums, mirror-feature
invariance and restored mirror coverage. A small TFoam error alone is not a
support check. Retain unsuccessful outcomes instead of dropping them based
on selector performance. At most four generation or fitting processes run
concurrently; stop new heavy work below 15 GiB free.

## Preserve original results and isolate the correction

`../stratified_refit` remains unchanged. This directory contains a versioned
view of the full study, reusing unaffected files through read-only access and
new local outputs for affected cases. Photon calibration totals, DIS rates,
signal events, fitting seeds, candidate profiles, rectangular-search budgets,
significance objective and inference settings remain the same. In particular,
this correction does not introduce per-component recalibration or tune a
physical parameter toward the reference rate.

The six files affect 12 of 220 mass/boson/run points:

- Two training components: refit BDT and likelihood candidate profiles and
  redo rectangular optimization for both boson types and both input sets.
- Two validation components: evaluate the previously trained candidate models
  on corrected validation events, reselect their thresholds and profiles,
  and rerun the original deterministic rectangular search using unchanged
  training events and corrected validation events. Do not use test data for
  these choices.
- Two test components: keep fitted models, thresholds and cuts unchanged;
  evaluate them on the corrected photon test events.

All 12 points are reevaluated with their original signal test events and the
appropriate corrected or unchanged photon test file. Do not rerun unaffected
points or refit test-only cases.

## Inference and checks

Record a new selection/model hash gate after fitting and validation choices
are completed. Its metadata explicitly states that this is a repair of known
sampling errors after earlier tests were seen. It does not retroactively
claim blinding. Retain the original gate as an immutable parent.

Recompute the 12 affected point analyses with 2000 paired event resamples,
seed 48230000 and batch 32. Reuse the other 208 point analyses only after
verifying their recorded input, selection/model and old-gate hashes against
the retained originals. They are read-only; do not run a force-reanalysis
through their symlinks merely because the new global gate hash differs.
Explicitly record both provenance branches in the reuse audit.

Reaggregate all ten runs per mass/boson group using the original one million
paired aggregate draws, seed schedule, 198-comparison family and descriptive
photon-loss scenarios. Regenerate the six-selection comparison and scientific
plots. Verify unchanged groups reproduce their prior numbers, and report
before/after changes for affected groups. The 10 GeV nominal and smearing
results are reused unchanged and checked, since none of the six components
is at 10 GeV.

Success means the six demonstrated sampling failures are repaired and their
downstream results are updated consistently. It does not settle the remaining
reference-rate discrepancy, establish every model assumption, or assert that
unobserved sampling errors are impossible elsewhere.
