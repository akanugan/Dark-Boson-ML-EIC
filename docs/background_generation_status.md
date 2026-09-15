# Background-generation status

## What the paper specifies

The corrected paper identifies:

1. Coherent bremsstrahlung `e A -> e A gamma`, where the photon is missed.
   After the electron cuts, it assumes a photon miss probability of `1e-6`
   for central energetic photons and a 100% miss probability for
   `|eta_gamma| > 3.5`. It reports only the resulting effective cross sections
   in Table I.
2. DIS `e p -> e X j`, simulated at parton level with MadGraph5_aMC@NLO.
   It states that selected jets are central (`|eta_j| < 3.5`) with minimum
   energy 8 GeV, applies a 95% ZDC veto assumption, multiplies by A for the
   nucleon luminosity, and reports effective cross sections in Table I.

## What is not specified

The public paper does not give the MadGraph process card, beam/PDF card,
factorization and renormalization scales, generation-level cuts, random seed,
event files, matching settings, or a detector response. It likewise does not
provide an event generator or event sample for coherent bremsstrahlung.

## Decision

Background event generation is not started by inventing these missing choices.
The project can use the Table I effective cross sections for a cut-based rate
check, but an ML classifier needs event shapes. The next defensible step is to:

1. obtain the authors' generation cards or define and document our own
   independent background model;
2. validate its post-cut rates against Table I;
3. add detector-veto observables and their uncertainties; and
4. export the same schema used by `config/event_schema.csv`.

MadGraph5_aMC@NLO is not currently installed in the inspected workspace.
Pythia 8 is installed, but substituting Pythia for the paper's stated
MadGraph parton-level setup would be a different analysis choice.
