# Current corrected results

**CURRENT RESULTS:** ten independent runs at eleven masses for scalar and vector bosons, with cuts, estimated likelihood, and BDT selections, each with and without `t`. This is the result set used by current Figures 4–9.

| Files | Meaning |
|---|---|
| `selection_results.csv` | 132 aggregate selection results relative to preselection. |
| `summary.csv` | 198 paired contrasts: 66 benefits of adding `t` and 132 comparisons between methods. |
| `run_metrics.csv` | 1,320 individual-run selection results. |
| `scenario_summary.csv`, `photon_loss_10GeV.csv` | Photon-loss response scenarios and the compact 10 GeV summary. |
| `photon_calibration_rates.csv` | Final nominal photon calibration and comparison with the updated reference rates. |
| `smearing/10pct/`, `smearing/20pct/` | Fixed-selection `t`-resolution benchmarks at 10 GeV. |
| `precision_followup.csv`, `full_validation_support.csv` | Precision and validation-support diagnostics. |
| `before_after.csv`, `component_changes.csv`, `photon_repair_summary.csv` | Repair audit: historical and corrected values appear together; these are not alternative current result sets. |
| `generate_photon_repairs.py`, `scripts/`, `src/` | Recorded six-component repair workflow and its tools. |

The [revision-data-v2 release](https://github.com/iRojae/Dark-Boson-ML-EIC/releases/tag/revision-data-v2) restores the saved arrays, run records, and selected models here. It supports [statistical replay](../scripts/README.md), not fresh fitting or event prediction without the excluded raw events. Current plotting commands are in [`../../figures/`](../../figures/README.md).

Historical path names in audit records identify the source calculation. The repair reused 208 analyses and repeated the affected fitting, validation, or evaluation for twelve; the 10 GeV nominal and smearing results were unaffected. See the [repair protocol](../protocols/photon_repair.md).
