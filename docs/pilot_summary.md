# Signal pilot summary

Date: 12 August 2026

## What was completed

- Generated weighted event-level samples for vector masses from 0.010 to
  10 GeV and scalar masses from 0.010 to 6.310 GeV.
- Applied the corrected Table I cuts sequentially in this fixed order:
  `Qe2`, electron `pT`, electron `eta`, and electron energy.
- Exported 417,290 events to one common table with 70/15/15 deterministic
  train/validation/test assignments.
- Preserved ROOT files and generator logs so every CSV row can be traced back
  to its source sample.
- Verified the table structure, finite values, non-negative event weights,
  unique event identifiers, cut flags, and split labels.

## Central validation point

At a boson mass of 1 GeV, the pilot gives:

| Signal | Inclusive [pb] | After Table I cuts [pb] | Effective selected events |
|---|---:|---:|---:|
| Vector | 13.5077 | 0.158882 | 217.6 |
| Scalar | 5.95269 | 0.0384997 | 212.7 |

The inclusive values agree with the established equations-as-written
baseline. The lower selected values reproduce the unresolved discrepancy
with the publication; no compensating scale factor has been applied.

## Statistical limitation of this pilot

The low-mass selected tails are not large enough for publication-level ML
training. For masses at or below 0.316 GeV, the effective selected sample size
is only about 1--29 events, depending on signal type and mass. These samples
verify the pipeline and expose where targeted generation is required; they
must not be used to claim a precise low-mass post-cut cross section.

The next production run should generate the phase-space region near the
selection boundary directly, then retain the correct importance weights. A
minimum effective selected sample size should be chosen before training; a
practical starting requirement is 1,000 effective events per signal and mass.

## Background boundary

No synthetic background was invented. The paper provides effective rates and
basic missed-object assumptions, but not the complete generator cards and
detector response needed to reproduce event-level bremsstrahlung and DIS
samples uniquely. The project is ready to ingest those samples once the
authors clarify their setup, or to define a clearly labeled independent
background baseline for the ML extension.
