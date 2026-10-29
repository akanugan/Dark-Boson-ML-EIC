# Photon-integration diagnostics

> Recorded execution documentation. Its commands describe the original production layout. Use the [study guide](../../../README.md) for public code locations and reproduction commands.

**DIAGNOSTIC PROVENANCE:** this folder records the integration and sampling checks behind the photon-rate audit. It includes both successful calculations and earlier samplers with known incomplete phase-space support. Those failed samplers are retained to explain the diagnosis; their numbers are not production photon rates.

Read [`results/findings.md`](results/findings.md) with the validity flags in the diagnostic CSVs. Its statements about files awaiting replacement describe the audit stage; the six components have since been repaired. The report's source-project link to `../stratified_repair/results.md` refers to a local report not included here. The public correction records are [the repair protocol](../protocols/photon_repair.md) and [corrected results](../stratified_repair/README.md).

Use [`../stratified_repair/photon_calibration_rates.csv`](../stratified_repair/photon_calibration_rates.csv) for the current nominal calibration rates. `revision/build.sh --benchmarks` builds these diagnostic implementations; it does not select which calculation is valid or reproduce the current selector comparison.

Other links inside the preserved findings report point to source-project audit notes and plots that are not included in this export. They are historical references, not public reproduction inputs; use the CSVs, public repair protocol, and corrected tables linked above. The report itself is kept unchanged to preserve its recorded checksum.
