# Current three-method comparison

This package supersedes the original BDT-versus-cuts comparison for the current results. It evaluates rectangular cuts, TMVA PDERS estimated likelihood, and BDT selections using electron inputs alone and electron inputs plus nuclear momentum transfer `t`.

All commands in this version use `v2/` as the working directory. The unchanged internal paths keep the original release archives and export checksums valid from there.

Ten independent runs at eleven masses for scalar and vector signals give 220 analyses. Each analysis contains all six selections on common samples. Photon events are shared between the two boson hypotheses within each mass and run.

## Layout

| Directory | Contents |
|---|---|
| [`src/`](src/README.md) | Current scientific tools, the pre-repair sampler used by unaffected samples, and separately identified earlier evaluators. |
| [`scripts/`](scripts/README.md) | Current aggregate entry points and full-pipeline helpers, plus clearly listed earlier revision pilots. |
| [`config/`](config/README.md) | Electron preselection and starting rate inputs; the photon entries are overridden by calibration. |
| [`stratified_repair/`](stratified_repair/README.md) | Current corrected results, repair workflow, and before/after diagnostics. |
| [`checks/`](checks/README.md) | Source, sampling, fitting, and result-consistency records. |
| [`protocols/`](protocols/README.md) | Recorded designs and their scope; earlier plans are not the final execution configuration. |
| [`rate_benchmark/`](rate_benchmark/README.md) | Integration diagnostics, including failed samplers retained to explain the repairs. |

The final photon normalization comes from a separate calibration integration, recorded in [`stratified_repair/photon_calibration_rates.csv`](stratified_repair/photon_calibration_rates.csv). Calibration values override the photon entries in `config/rates.csv`. The reference DIS contribution remains fixed and unrejected. The build also uses four [shared top-level C++ tools](../src/README.md); they are current dependencies despite their original locations.

## Main numerical tables

- `stratified_repair/selection_results.csv`: 132 results for the six selections, relative to the common preselection at each mass.
- `stratified_repair/summary.csv`: 198 paired contrasts, comprising 66 within-method comparisons of adding `t` and 132 comparisons between methods with identical inputs.
- `stratified_repair/scenario_summary.csv`: 2376 descriptive photon-loss comparisons, separating shape-only, rate-only, and combined changes.
- `stratified_repair/smearing/10pct/` and `stratified_repair/smearing/20pct/`: fixed-selection resolution benchmarks at 10 GeV.

`electron` denotes the four electron inputs. The historical identifier `electron_qa2` denotes those inputs plus `log10(t/GeV²)`; `QA2` is the positive nuclear momentum-transfer variable. An advantage in percent is `100 × (ratio − 1)`. The `ci95_*` fields are pointwise intervals; `family95_*` fields use the 198-comparison adjustment. These are significance ratios, not increases in the number of produced signal events.

## What can be reproduced directly

Use the compact inputs and entry points in [`../figures/`](../figures/README.md) to recreate the current figures. Aggregate plotting requires no event generation or model fitting. The unchanged inclusive photon comparison in Figure 3 uses an original `data-v1` ROOT file; the corrected comparison plots use the bundled tables.

The [revision-data-v2 release](https://github.com/iRojae/Dark-Boson-ML-EIC/releases/tag/revision-data-v2) provides paired per-run analysis arrays and selected models. It supports statistical reaggregation with the commands in [`scripts/README.md`](scripts/README.md). It excludes the raw events and candidate-model artifacts needed for prediction, refitting, or repeating the repair. The original `data-v1` release also lacks those later samples; see [`../DATA_DOWNLOAD.md`](../DATA_DOWNLOAD.md). Preserve the pre-repair and corrected sampler versions when following the recorded workflow: the six-file repair reused unaffected samples and changed only the diagnosed components and downstream analyses.

## Correction provenance

Six outside-acceptance photon components were regenerated after independent sampling checks found missed configurations. Four boson/mass/run points were refitted, four had validation choices repeated, and four were reevaluated with fixed selections; 208 unaffected analyses were reused after provenance checks. The 10 GeV nominal and smearing results are unchanged. These are documented corrections after earlier results were inspected.

The statistical intervals describe finite simulation and generation/fitting variation. Photon calibration uncertainty, physical-model changes, and detector systematics are not included. The photon-loss and resolution scenarios are specified response benchmarks.
