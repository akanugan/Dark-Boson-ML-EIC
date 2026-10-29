# Revised scientific code

These scripts retain the numerical methods used for the corrected comparison.
They are separate from the manuscript. The current results are in
`revision/stratified_repair`; the older `revision/results`, photon-loss pilot,
wide-interval follow-up and `stratified_refit` paths in historical scripts refer
to earlier studies, not an alternative current result.

The active aggregate/statistics entry points are `analyze_stratified_refit.py`,
`compare_selections.py`, and `plot_stratified_refit.py`. In particular,
`evaluate_photon_loss.py`, `run_t_smearing*.py`, `run_comparison.py`, and
`regenerate_current_diagnostics.py` retain the earlier pilot workflows; their
names do not make their outputs current. The revised response scenarios are
calculated by `analyze_stratified_refit.py`. Current photon calibration rates
are recorded in the released point configurations and result tables, rather
than the earlier baseline rates in `revision/config/rates.csv`.

Install Python requirements from the repository root:

```sh
python3 -m pip install -r requirements-revision.txt
```

## Plot the released summaries

This needs the current CSV summaries only, without ROOT, models or event files:

```sh
python3 revision/scripts/plot_stratified_refit.py --results revision/stratified_repair
```

The command reads `summary.csv`, `selection_results.csv`, `precision_followup.csv`
when present, and `smearing/10pct` and `smearing/20pct` summaries when present.
It writes plots under that result directory. The per-figure folders supply the
current publication layouts and their small numerical inputs.

## Reaggregate released analysis arrays

After restoring the compact revision-data-v2 analysis archive, the following
commands recompute aggregate intervals and the six-method comparison from saved
paired run/event arrays. They do not generate events, train models, choose
selections or require ROOT:

```sh
python3 revision/scripts/analyze_stratified_refit.py \
  --results revision/stratified_repair --summarize-only
python3 revision/scripts/compare_selections.py \
  --results revision/stratified_repair --workers 4
```

The first command needs 220 `fits/rep_*/{boson}_m*/analysis` directories containing
`analysis_complete.json`, `nominal_RZ.npy`, `bootstrap_RZ.npy`,
`scenario_nominal_RZ.npy`, and `scenario_bootstrap_RZ.npy`, plus each point's
`sample_config.json` and the recorded `fit_protocol_gate.json`. The second also
needs `analysis/test_metrics.csv`. The primary aggregate uses one million
resamples and the original fixed seed; the scenario aggregate uses 20,000.
Outputs overwrite aggregate CSV summaries in the supplied result directory, so
use a copied extraction when comparing with the checked-in results.

The arrays preserve paired results of the six selections. Reaggregation checks
the statistical calculation, not the event generator or fitted models.

## Event generation, fitting and numerical checks

```sh
revision/build.sh
revision/build.sh --benchmarks  # also build the alternative integration maps
```

Set `ROOT_CONFIG` if `root-config` is not on PATH, `CXX` to select the C++17
compiler, and `BOOST_INCLUDEDIR` if Boost headers are outside default include
paths. `DARK_PROJECT_ROOT` can point archived study runners to a separate copy
of the original signal generators and source project; it defaults to the
repository root. Python tools use the interpreter that invokes them.

`prepare_stratified_data.py`, `run_stratified_refit.py`,
`continue_stratified_study.py`, and `stratified_repair/scripts/repair.py` preserve
the full execution workflow. These require raw ROOT training/validation/test
samples, trained candidate models and original run records beyond the compact
analysis archive. The old data-v1 release alone is not the corrected study.
Do not run these fitting drivers over the compact inference-only extraction.

The repair directory originally used an overlay of the preceding full study.
Its setup script rebuilds local links, while provenance JSON files preserve
historical paths and checksums. Moving an archived command record or rebuilding
a binary can change its path-dependent resume signature. Retained records must
not be silently relabeled as a new run. Fresh runs require complete inputs and
new output directories; matching aggregate outputs alone does not establish
full end-to-end reproduction.

The numerical alternatives in `revision/rate_benchmark/sources` include known
incomplete-support calculations, retained to document the diagnosis. Use the
benchmark findings and validity flags when interpreting their outputs.

Lightweight checks, using synthetic data only:

```sh
python3 revision/scripts/analyze_stratified_refit.py --self-test
python3 revision/scripts/compare_selections.py --self-test
```
