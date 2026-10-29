# Historical independent-run results (original Figure 8)

These values belong only to the earlier BDT-versus-cuts study and its original Figure 8. They are retained for provenance; use [`revision/stratified_repair/`](../../revision/stratified_repair/) for the current three-method results. The current Figure 8 shows [signal–photon efficiency curves](../../figures/08_roc/).

In this original-study table, both methods use the same inputs and the published photon-background normalization. Each benchmark uses ten independent event generation and training runs.

CSV coupling advantages are fractions (multiply by 100 for percent). Intervals combine resampling of independent runs and events. Adjusted lower bounds use the four electron-only tests or the two electron-plus-t tests, respectively. This table does not describe the separate alternative photon-normalization comparison.

| Inputs | Signal | Mass (GeV) | Coupling advantage, median [95%] | Adjusted lower | BDT wins |
|---|---|---:|---:|---:|---:|
| electron_only | vector | 1 | -0.009% [-0.029%, +0.004%] | -0.032% | 4/10 |
| electron_only | vector | 10 | -0.057% [-0.142%, +0.021%] | -0.153% | 2/10 |
| electron_only | scalar | 1 | +0.031% [-0.083%, +0.132%] | -0.102% | 8/10 |
| electron_only | scalar | 6.31 | -0.088% [-0.182%, -0.005%] | -0.194% | 0/10 |
| electron_plus_t | vector | 10 | +1.208% [+1.081%, +1.326%] | +1.081% | 10/10 |
| electron_plus_t | scalar | 10 | +1.361% [+1.206%, +1.529%] | +1.206% | 10/10 |

[Download the full-precision CSV](values.csv). The `source_summary` column identifies the original numerical output included in the project.
