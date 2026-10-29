# v2 shared generation and fitting code

These are current dependencies, copied into v2 so this version can build independently of v1 code.

| Source | Role |
|---|---|
| `generate_vector.cpp` | Vector signal generation; its massless-vector limit also supplied the inclusive photon sample used by unchanged Figure 3. |
| `generate_scalar.cpp` | Scalar signal generation. |
| `train_tmva.cpp` | Fits candidate BDT configurations. |
| `optimize_rectangular_fair.cpp` | Optimizes rectangular selections. |
| [`../include/DarkBosonKinematics.h`](../include/DarkBosonKinematics.h) | Shared kinematic definitions. |

From `v2/`, run `revision/build.sh` to build these programs and the current photon, likelihood, score-export, and repair tools. The likelihood implementation is [`../revision/src/train_likelihood.cpp`](../revision/src/train_likelihood.cpp); current workflow details are in [`../revision/scripts/README.md`](../revision/scripts/README.md).

Current Figure 3 has a standalone [per-figure entry point](../figures/03_photon_shapes/README.md). Original multi-figure utilities are preserved under [`../../v1/src/`](../../v1/src/README.md) and are not part of this current build.
