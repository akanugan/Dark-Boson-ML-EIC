# Revised scientific code

These scripts retain the numerical methods used for the corrected comparison.
They are separate from the manuscript. Current results are in
`revision/stratified_repair`. The preceding `stratified_refit` scan is retained
for correction provenance; its shared pipeline helpers are still required.

## Current entry points and dependencies

| Current aggregate entry point | Purpose |
|---|---|
| `analyze_stratified_refit.py` | Paired uncertainty analysis and photon-loss scenarios; can reaggregate saved arrays without reading events. |
| `compare_selections.py` | Reconstructs the six-selection comparison and checks it against the 198 nominal contrasts. |
| `plot_stratified_refit.py` | Plots the current aggregate summaries. |

The following are current full-workflow modules, not earlier-study-only code:

- `prepare_stratified_data.py`: generation of the separate photon regions for the preceding full scan.
- `run_stratified_refit.py`: fitting, validation selection, and shared utilities.
- `continue_stratified_study.py`: final evaluation and the current 10%/20% smearing workflow, using `export_refit_scores`. The similarly named `run_t_smearing*.py` files below are earlier pilots.

The current repair workflow under `revision/stratified_repair/` also retains
`generate_photon_repairs.py` and its `scripts/setup_view.py`, `repair.py`,
`validation_reselect.py`, `check_reuse.py`, `audit_fitting_settings.py`,
`reproduce_validation.py`, and `report_changes.py`. These generate replacements,
repeat the affected selections, or audit the correction. They require the
preceding full study and additional raw events, candidate models, or execution
records; the compact array release is not sufficient to rerun that workflow.

Keep the shared modules together: the repair imports `run_stratified_refit`
and `continue_stratified_study`; those depend on `prepare_stratified_data` and
`analyze_stratified_refit`. `compare_selections` also uses
`plot_stratified_refit`.

Current photon calibration rates are recorded in the released point
configurations and result tables, rather than the earlier baseline photon
rates in `revision/config/rates.csv`.

## Earlier revision only

These 20 scripts belong to earlier stages of the revision, including pilots
and follow-up checks. They are distinct from the original 2026 submission
study and are not entry points for the current corrected results. Their
earlier outputs must not be substituted for `revision/stratified_repair`.

| Earlier revision workflow | Scripts |
|---|---|
| Initial three-method scan and statistics | `run_comparison.py`, `summarize.py`, `test_statistics.py`, `plot_results.py`, `plot_manuscript_scan.py` |
| Targeted wide-interval follow-up | `rerun_wide_intervals.py`, `plot_followup.py` |
| Photon-generation and photon-loss pilots | `pilot_photon_lab.py`, `pilot_photon_regions.py`, `run_photon_loss_generation.py`, `export_photon_loss_scores.py`, `evaluate_photon_loss.py`, `plot_photon_loss.py`, `report_photon_loss.py` |
| Ancillary-distribution reweighting tests | `run_photon_shapes.py`, `plot_photon_shapes.py` |
| Earlier smearing pilots | `run_t_smearing.py`, `run_t_smearing_20pct.py` |
| Earlier diagnostics and original-versus-refit comparison | `regenerate_current_diagnostics.py`, `compare_original_t.py` |

None of these scripts is imported by the current pipeline. Retain their
internal dependencies if moving them: `plot_followup.py`,
`plot_manuscript_scan.py`, `plot_results.py`, `rerun_wide_intervals.py`, and
`summarize.py` import `run_comparison`; `test_statistics.py` imports
`summarize`. In particular, `evaluate_photon_loss.py` uses the earlier fixed
photon rate, while the current scenarios are calculated by
`analyze_stratified_refit.py`.

`resume_after_space_guard.py` is an operational restart utility retained for
history. It is not a scientific result or reproduction entry point.

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
commands recompute aggregate intervals and the six-selection comparison from saved
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
