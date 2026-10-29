# Current three-method comparison

This package supersedes the original BDT-versus-cuts comparison for the current results. It evaluates rectangular cuts, TMVA PDERS estimated likelihood, and BDT selections using electron inputs alone and electron inputs plus nuclear momentum transfer `t`.

Ten independent runs at eleven masses for scalar and vector signals give 220 analyses. Each analysis contains all six selections on common samples. Photon events are shared between the two boson hypotheses within each mass and run.

## Layout

| Directory | Contents |
|---|---|
| `src/` | Photon generation, stratum merging, likelihood fitting, score export, and evaluation implementations. |
| `scripts/` | Generation, fitting, evaluation, uncertainty analysis, plotting, and repair workflows. |
| `config/` | Electron preselection and input rate configurations. |
| `stratified_repair/` | Current corrected results, repair workflow, and diagnostic summaries. |
| `checks/` | Source, sampling, fitting, and result-consistency records. |
| `protocols/` | Original study design, sampling-repair scope, and review notes. |

The final photon normalization comes from a separate calibration integration. The original rate-input CSV is not, by itself, the final photon-rate table: calibration values override its photon entries for this study. The reference DIS contribution remains fixed and unrejected.

## Main numerical tables

- `stratified_repair/selection_results.csv`: 132 results for the six selections, relative to the common preselection at each mass.
- `stratified_repair/summary.csv`: 198 paired contrasts, comprising 66 within-method comparisons of adding `t` and 132 comparisons between methods with identical inputs.
- `stratified_repair/scenario_summary.csv`: 2376 descriptive photon-loss comparisons, separating shape-only, rate-only, and combined changes.
- `stratified_repair/smearing/10pct/` and `stratified_repair/smearing/20pct/`: fixed-selection resolution benchmarks at 10 GeV.

`electron` denotes the four electron inputs. The historical identifier `electron_qa2` denotes those inputs plus `log10(t/GeV²)`; `QA2` is the positive nuclear momentum-transfer variable. An advantage in percent is `100 × (ratio − 1)`. The `ci95_*` fields are pointwise intervals; `family95_*` fields use the 198-comparison adjustment. These are significance ratios, not increases in the number of produced signal events.

## What can be reproduced directly

Use the compact inputs and entry points in [`../figures/`](../figures/README.md) to recreate the current figures. Aggregate plotting requires no event generation or model fitting.

Repeating the uncertainty calculation requires the paired per-run outputs. Refitting requires the weighted events and complete configurations. Those later event/model files are not in the original `data-v1` release; see [`../DATA_DOWNLOAD.md`](../DATA_DOWNLOAD.md). Preserve the original and corrected sampler versions when following the recorded workflow: the six-file repair reused unaffected samples and changed only the diagnosed components and downstream analyses.

## Correction provenance

Six outside-acceptance photon components were regenerated after independent sampling checks found missed configurations. Four boson/mass/run points were refitted, four had validation choices repeated, and four were reevaluated with fixed selections; 208 unaffected analyses were reused after provenance checks. The 10 GeV nominal and smearing results are unchanged. These are documented corrections after earlier results were inspected.

The statistical intervals describe finite simulation and generation/fitting variation. Photon calibration uncertainty, physical-model changes, and detector systematics are not included. The photon-loss and resolution scenarios are specified response benchmarks.
