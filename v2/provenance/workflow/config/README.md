# Current preselection and starting rate inputs

> Recorded execution documentation. Its commands describe the original production layout. Use the [study guide](../../../README.md) for public code locations and reproduction commands.

| File | Role in the corrected study |
|---|---|
| `paper_cuts.csv` | Mass-dependent electron preselection shared by all methods. |
| `rates.csv` | Starting rate configuration. Its photon entries are from an earlier calculation and are overridden by the independent calibration; they are **not the final photon rates**. |

The current photon values are in [`../stratified_repair/photon_calibration_rates.csv`](../stratified_repair/photon_calibration_rates.csv) and the released per-point `sample_config.json` records. The nominal DIS contribution remains fixed and unrejected. See the [current analysis guide](../../../docs/current-analysis.md).
