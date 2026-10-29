# Numerical results

| File or folder | Contents |
|---|---|
| [selection_results.csv](selection_results.csv) | 132 aggregate results for the six selections relative to their common preselection. |
| [summary.csv](summary.csv) | 198 paired contrasts: adding `t` within each method and comparing methods with identical inputs. |
| [run_metrics.csv](run_metrics.csv) | 1,320 individual-run selection results. |
| [photon_calibration_rates.csv](photon_calibration_rates.csv) | Nominal photon rates and comparison with the reference. |
| [scenario_summary.csv](scenario_summary.csv) | Photon-loss variations, separated into shape-only, rate-only, and combined changes. |
| [photon_loss_10GeV.csv](photon_loss_10GeV.csv) | Compact 10 GeV photon-loss summary. |
| [smearing/10pct/](smearing/10pct/), [smearing/20pct/](smearing/20pct/) | Fixed-selection `t`-resolution benchmarks at 10 GeV. |
| [precision_followup.csv](precision_followup.csv), [full_validation_support.csv](full_validation_support.csv) | Statistical precision and validation-support diagnostics. |

`electron` denotes the electron inputs; `electron_qa2` adds `log10(t/GeV²)`. `ci95_*` columns contain pointwise intervals, while `family95_*` columns account for the 198 nominal comparisons. Percent advantages are `100 × (ratio − 1)` in the stated performance measure.

The [analysis guide](../docs/current-analysis.md) defines that measure. The [data package](../DATA_DOWNLOAD.md) adds saved arrays, selected models, and execution records here for [statistical replay](../scripts/README.md). Earlier numerical audit records are retained under [provenance](../provenance/README.md).
