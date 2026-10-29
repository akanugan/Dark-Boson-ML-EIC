# Sealed ML-versus-rectangular final-test results

Positive coupling values favor BDT. Intervals are paired event-bootstrap
intervals for the sealed test sample only; training and generator-model
systematics require the separate seed study.
For the 22 electron-only primary tests, the CSV also gives a conservative
one-sided 95% familywise Bonferroni lower bound (quantile 0.05/22).

| Signal | Mass | Features | Profile | Box grid | BDT R_Z | Box R_Z | Coupling advantage [95% interval] |
|---|---:|---|---|---:|---:|---:|---:|
| scalar | 0.01 | electron only | depth2 | 160 | 1.0006 | 1.0046 | -0.20% [-0.33, -0.07] |
| scalar | 0.01 | electron + truth QA2 | depth2 | 160 | 1.0031 | 1.0046 | -0.08% [-0.20, +0.04] |
| scalar | 0.032 | electron only | depth3_800 | 40 | 0.9993 | 1.0010 | -0.09% [-0.18, +0.01] |
| scalar | 0.032 | electron + truth QA2 | depth4 | 40 | 0.9992 | 1.0010 | -0.09% [-0.19, +0.01] |
| scalar | 0.1 | electron only | depth3 | 80 | 1.0020 | 1.0004 | +0.08% [-0.04, +0.21] |
| scalar | 0.1 | electron + truth QA2 | depth2 | 160 | 1.0021 | 1.0004 | +0.09% [-0.03, +0.20] |
| scalar | 0.316 | electron only | depth2 | 160 | 0.9988 | 1.0006 | -0.09% [-0.19, +0.01] |
| scalar | 0.316 | electron + truth QA2 | depth2 | 160 | 1.0003 | 1.0006 | -0.01% [-0.15, +0.12] |
| scalar | 1 | electron only | depth2 | 160 | 1.0493 | 1.0480 | +0.06% [-0.11, +0.23] |
| scalar | 1 | electron + truth QA2 | depth2 | 40 | 1.0472 | 1.0495 | -0.11% [-0.28, +0.07] |
| scalar | 1.585 | electron only | depth2 | 40 | 1.1077 | 1.1041 | +0.16% [+0.03, +0.29] |
| scalar | 1.585 | electron + truth QA2 | depth3 | 40 | 1.1102 | 1.1080 | +0.10% [-0.07, +0.27] |
| scalar | 2.512 | electron only | depth4 | 80 | 1.1017 | 1.1020 | -0.01% [-0.13, +0.11] |
| scalar | 2.512 | electron + truth QA2 | depth2 | 160 | 1.1154 | 1.1067 | +0.39% [+0.20, +0.59] |
| scalar | 3.981 | electron only | depth2 | 40 | 1.0366 | 1.0383 | -0.08% [-0.23, +0.06] |
| scalar | 3.981 | electron + truth QA2 | depth3 | 80 | 1.0779 | 1.0723 | +0.26% [+0.07, +0.44] |
| scalar | 5 | electron only | depth4 | 160 | 1.0251 | 1.0291 | -0.20% [-0.32, -0.08] |
| scalar | 5 | electron + truth QA2 | depth3_800 | 40 | 1.0852 | 1.0727 | +0.58% [+0.44, +0.71] |
| scalar | 6.31 | electron only | depth3 | 80 | 1.0242 | 1.0242 | +0.00% [-0.16, +0.16] |
| scalar | 6.31 | electron + truth QA2 | depth3_800 | 40 | 1.1132 | 1.1022 | +0.49% [+0.30, +0.68] |
| scalar | 10 | electron only | depth2 | 160 | 1.0484 | 1.0482 | +0.01% [-0.16, +0.18] |
| scalar | 10 | electron + truth QA2 | depth3_800 | 80 | 1.3053 | 1.2697 | +1.37% [+1.15, +1.59] |
| vector | 0.01 | electron only | depth3 | 40 | 1.0000 | 1.0000 | +0.00% [-0.00, +0.00] |
| vector | 0.01 | electron + truth QA2 | depth2 | 40 | 0.9995 | 0.9987 | +0.04% [+0.02, +0.07] |
| vector | 0.032 | electron only | depth2 | 40 | 0.9998 | 1.0000 | -0.01% [-0.02, +0.01] |
| vector | 0.032 | electron + truth QA2 | depth3 | 40 | 0.9999 | 0.9998 | +0.01% [-0.00, +0.01] |
| vector | 0.1 | electron only | depth4 | 40 | 0.9999 | 1.0001 | -0.01% [-0.02, +0.01] |
| vector | 0.1 | electron + truth QA2 | depth2 | 40 | 0.9996 | 1.0001 | -0.02% [-0.04, -0.01] |
| vector | 0.316 | electron only | depth3_800 | 40 | 0.9999 | 0.9998 | +0.00% [-0.01, +0.02] |
| vector | 0.316 | electron + truth QA2 | depth3_800 | 40 | 0.9992 | 0.9999 | -0.04% [-0.07, -0.01] |
| vector | 1 | electron only | depth3 | 160 | 0.9998 | 0.9989 | +0.04% [-0.01, +0.10] |
| vector | 1 | electron + truth QA2 | depth2 | 160 | 0.9989 | 1.0003 | -0.07% [-0.14, +0.00] |
| vector | 1.585 | electron only | depth4 | 160 | 0.9988 | 1.0009 | -0.11% [-0.19, -0.03] |
| vector | 1.585 | electron + truth QA2 | depth3_800 | 40 | 1.0113 | 1.0111 | +0.01% [-0.03, +0.05] |
| vector | 2.512 | electron only | depth4 | 40 | 0.9940 | 0.9986 | -0.23% [-0.40, -0.06] |
| vector | 2.512 | electron + truth QA2 | depth4 | 80 | 1.0283 | 1.0275 | +0.04% [-0.03, +0.11] |
| vector | 3.981 | electron only | depth3_800 | 40 | 0.9997 | 1.0000 | -0.01% [-0.03, +0.00] |
| vector | 3.981 | electron + truth QA2 | depth4 | 40 | 1.0433 | 1.0382 | +0.24% [+0.14, +0.35] |
| vector | 5 | electron only | depth2 | 160 | 1.0000 | 1.0000 | +0.00% [-0.00, +0.01] |
| vector | 5 | electron + truth QA2 | depth4 | 80 | 1.0617 | 1.0506 | +0.52% [+0.43, +0.62] |
| vector | 6.31 | electron only | depth2 | 40 | 0.9997 | 1.0000 | -0.01% [-0.07, +0.05] |
| vector | 6.31 | electron + truth QA2 | depth3_800 | 40 | 1.0901 | 1.0817 | +0.38% [+0.25, +0.52] |
| vector | 10 | electron only | depth4 | 80 | 1.0015 | 1.0027 | -0.06% [-0.21, +0.10] |
| vector | 10 | electron + truth QA2 | depth3_800 | 160 | 1.2828 | 1.2536 | +1.14% [+0.96, +1.32] |
