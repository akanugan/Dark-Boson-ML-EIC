# Independent photon-rate benchmark

Started 26 October 2026 before evaluating the new benchmark outputs.

Purpose: reconcile the historical direct photon-loss-weighted integration
with the separate central/outside integrations. All methods target the same
physical quantity. The updated reference is an external comparison, never a
target used to tune a parameter or stop sampling.

## Fixed physics

- Electron 18 GeV; gold 100 GeV/nucleon, A=197, Z=79, ion mass 183 GeV.
- Photon regulator 1e-6 GeV; electron coupling 0.3028221209.
- Original electron-line ISR+FSR amplitude and Helm form factor.
- Exact original electron preselections for mass hypotheses .032 and 10 GeV.
- Central |eta_gamma| <= 3.5, loss probability 1e-6; outside loss probability 1.

## Initial comparison

For each preselection, run three independent seeds for four routes:

1. Historical CM direct-effective integration, including the photon-loss
   factor inside the adapted density. Reuse historical seeds 833001, 833101,
   833201 and the preserved original executable/source.
2. CM central-only integration using the retained central generator.
3. Historical CM outside-only integration (historical region name `forward`).
4. New lab-coordinate outside-only integration.

Each route uses 250000 generation attempts, 2500 TFoam cells, 1200 adaptation
samples. This reproduces the historical direct-effective settings and gives
the separate routes the same budget. Central, CM-outside and lab-outside
seeds use separate fixed seed bases. The three replicas within a route are
independent. Historical seeds are reused between the two different cuts;
do not pool their errors as independent physics measurements.

The comparison has 24 generation jobs, at most four concurrently. Preserve
all outputs and failures. Record commands, binary/source hashes and ROOT
version; resume only identical successful commands. Stop starting jobs below
15 GiB free. Existing events, models, calibrated rates, results and manuscript
are unchanged.

## Checks and interpretation

Compare direct-effective with `1e-6 * central + outside`, for both independent
outside-coordinate routes. Report means, per-seed values, reported integration
errors and observed seed scatter. Inspect physical component weights,
azimuthal reflection balance, effective sample size and weighted electron
energy/eta distributions. Merely obtaining a large effective sample size or
small internal error does not establish complete integration support.

The initial goal is approximately 1% numerical precision on the total effective
rate and consistent results between routes. Numerical support failures or
significant inter-route discrepancies trigger a documented mapping/support
investigation rather than deletion of low samples or adjustment to the
reference value. Increased budgets or transformed coordinates are separate
diagnostic stages and must be recorded before their results are evaluated.

Do not change classifier selections, reinterpret prior errors as uncertainty
on different quantities, or claim a numerical agreement test against rounded
reference values without reference uncertainties. The reference comparison
does not replace consistency between independent integration methods.
