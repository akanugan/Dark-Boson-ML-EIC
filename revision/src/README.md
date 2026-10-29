# Current tools and earlier revision tools

| Status | Sources | Role |
|---|---|---|
| **CURRENT** | `generate_photon_regions.cpp`, `merge_photon_strata.cpp`, `train_likelihood.cpp`, `export_refit_scores.cpp` | Separate photon strata, combine their physical weights, fit the estimated likelihood, and export the six selections' scores. |
| **CURRENT PRE-REPAIR DEPENDENCY** | `generate_photon_lab.cpp` | Sampler used for the original stratified generation and retained unaffected samples. The six repaired components instead use [`../stratified_repair/src/generate_photon_lab.cpp`](../stratified_repair/src/generate_photon_lab.cpp). |
| **EARLIER REVISION ONLY** | `evaluate_three_way.cpp`, `evaluate_t_smearing.cpp`, `export_shape_scores.cpp` | Earlier scan, smearing, and shape-pilot tools; their outputs are not the corrected results. |
| **STANDALONE UTILITY** | `export_photon_shape.cpp` | ROOT-to-CSV shape export; not called by the current corrected pipeline. |

The [current build](../scripts/README.md) also compiles four [shared top-level tools](../../src/README.md) and the three repair tools. Build availability does not make an earlier evaluator's output current. Use [`../stratified_repair/`](../stratified_repair/README.md) for the reported results.
