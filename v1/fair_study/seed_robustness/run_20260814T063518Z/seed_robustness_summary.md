# Seed-robust fair BDT-versus-cuts study

Run: `run_20260814T063518Z`. Independent complete replicas: 10.
Paired event bootstraps per replica: 2000; hierarchical draws: 20000; hierarchical seed: 8300099.
Primary features are recoil-electron quantities only. Each method uses
the same weighted training, validation, and sealed-test samples.
BDT profile/threshold and rectangular bounds are selected on validation;
the final comparison is paired on the same test events.

| Signal | Mass [GeV] | Selected profiles | Geometric mean RZ ratio | Hierarchical 95% interval | Coupling advantage, median [95%] | Verdict |
|---|---:|---|---:|---:|---:|---|
| vector | 1 | depth2:2;depth3:4;depth4:0;depth3_800:4 | 0.9998 | [0.9994, 1.0001] | -0.01% [-0.03%, +0.00%] | practical equivalence |
| vector | 10 | depth2:6;depth3:1;depth4:3;depth3_800:0 | 0.9988 | [0.9972, 1.0004] | -0.06% [-0.14%, +0.02%] | practical equivalence |
| scalar | 1 | depth2:5;depth3:3;depth4:2;depth3_800:0 | 1.0006 | [0.9983, 1.0026] | +0.03% [-0.08%, +0.13%] | practical equivalence |
| scalar | 6.31 | depth2:6;depth3:4;depth4:0;depth3_800:0 | 0.9982 | [0.9964, 0.9999] | -0.09% [-0.18%, -0.00%] | practical equivalence |

Intervals use a hierarchical paired bootstrap: complete generator/
training replicas are resampled, then one paired event-bootstrap draw
is taken within every sampled replica. The paired event bootstrap keeps
BDT and rectangular decisions on each event together.

This is conditional parton-level evidence after Table I preselection.
It does not repair the photon-model mismatch, missing event-level DIS,
selected-signal discrepancy, scalar-amplitude validation, or absent
detector response. It must not be described as detector-level EIC reach.
