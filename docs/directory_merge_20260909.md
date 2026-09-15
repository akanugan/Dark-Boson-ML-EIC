# Directory merge — September 9, 2026

Merged `/Users/rojaemighty/Dark/next_stage` into `/Users/rojaemighty/Dark`. Removed the now-empty next_stage directory.
All 5,956 retained files matched their planned SHA-256 immediately after moving.

## Overlapping paths

| Path | Version kept | Identical contents |
|---|---|---|
| `.DS_Store` | parent | False |
| `Makefile` | next_stage | False |
| `README.md` | next_stage | False |
| `.gitignore` | next_stage | False |
| `bin/generate_scalar` | next_stage | False |
| `bin/generate_vector` | next_stage | False |
| `config/paper_cuts.csv` | next_stage | True |
| `include/DarkBosonKinematics.h` | next_stage | True |
| `src/generate_vector.cpp` | next_stage | False |
| `src/generate_scalar.cpp` | next_stage | False |

Newest is determined by filesystem modification time. Other distinct files and the frozen baseline were retained.

## Migration adjustments

Updated the signal plot project root and output path, made the importance extractor root relative to its script, restored `make plot`, and documented the unified layout. Retained parent ignore rules alongside the newer ignore file.

Replaced the old root in CSV path fields and documentation. Historical logs and XML/C training metadata retain their original creation paths. Numerical results, model parameters, ROOT data, and manuscript contents were not changed.

Checksum manifests have relocated paths and updated hashes only for files deliberately edited during this migration (including dependent manifests). They describe the migrated layout, not the original frozen bytes; original versions and before/after hashes are in the temporary recovery directory below. Unrelated pre-existing checksum discrepancies were not corrected.

Temporary recovery and full pre-move manifest: `/tmp/dark-merge-20260909`. This is temporary storage, not a permanent backup.

## Files edited for migration

- `.gitignore`
- `Makefile`
- `README.md`
- `docs/baseline_manifest.md`
- `docs/seed_robustness_protocol.md`
- `docs/tmva_t_importance_audit.md`
- `fair_study/rigorous/development_frozen/selected_models.csv`
- `fair_study/rigorous/final_results_manifest.sha256`
- `fair_study/rigorous/frozen_method_manifest.sha256`
- `fair_study/seed_robustness/run_20260814T063518Z/method_manifest.sha256`
- `fair_study/seed_robustness/run_20260814T063518Z/rep_001/scalar_m1p000/selected_box_metrics_grid_candidates.csv`
- `fair_study/seed_robustness/run_20260814T063518Z/rep_001/scalar_m1p000/selected_model_metrics_profile_candidates.csv`
- `fair_study/seed_robustness/run_20260814T063518Z/rep_001/scalar_m6p310/selected_box_metrics_grid_candidates.csv`
- `fair_study/seed_robustness/run_20260814T063518Z/rep_001/scalar_m6p310/selected_model_metrics_profile_candidates.csv`
- `fair_study/seed_robustness/run_20260814T063518Z/rep_001/vector_m10p000/selected_box_metrics_grid_candidates.csv`
- `fair_study/seed_robustness/run_20260814T063518Z/rep_001/vector_m10p000/selected_model_metrics_profile_candidates.csv`
- `fair_study/seed_robustness/run_20260814T063518Z/rep_001/vector_m1p000/selected_box_metrics_grid_candidates.csv`
- `fair_study/seed_robustness/run_20260814T063518Z/rep_001/vector_m1p000/selected_model_metrics_profile_candidates.csv`
- `fair_study/seed_robustness/run_20260814T063518Z/rep_002/scalar_m1p000/selected_box_metrics_grid_candidates.csv`
- `fair_study/seed_robustness/run_20260814T063518Z/rep_002/scalar_m1p000/selected_model_metrics_profile_candidates.csv`
- `fair_study/seed_robustness/run_20260814T063518Z/rep_002/scalar_m6p310/selected_box_metrics_grid_candidates.csv`
- `fair_study/seed_robustness/run_20260814T063518Z/rep_002/scalar_m6p310/selected_model_metrics_profile_candidates.csv`
- `fair_study/seed_robustness/run_20260814T063518Z/rep_002/vector_m10p000/selected_box_metrics_grid_candidates.csv`
- `fair_study/seed_robustness/run_20260814T063518Z/rep_002/vector_m10p000/selected_model_metrics_profile_candidates.csv`
- `fair_study/seed_robustness/run_20260814T063518Z/rep_002/vector_m1p000/selected_box_metrics_grid_candidates.csv`
- `fair_study/seed_robustness/run_20260814T063518Z/rep_002/vector_m1p000/selected_model_metrics_profile_candidates.csv`
- `fair_study/seed_robustness/run_20260814T063518Z/rep_003/scalar_m1p000/selected_box_metrics_grid_candidates.csv`
- `fair_study/seed_robustness/run_20260814T063518Z/rep_003/scalar_m1p000/selected_model_metrics_profile_candidates.csv`
- `fair_study/seed_robustness/run_20260814T063518Z/rep_003/scalar_m6p310/selected_box_metrics_grid_candidates.csv`
- `fair_study/seed_robustness/run_20260814T063518Z/rep_003/scalar_m6p310/selected_model_metrics_profile_candidates.csv`
- `fair_study/seed_robustness/run_20260814T063518Z/rep_003/vector_m10p000/selected_box_metrics_grid_candidates.csv`
- `fair_study/seed_robustness/run_20260814T063518Z/rep_003/vector_m10p000/selected_model_metrics_profile_candidates.csv`
- `fair_study/seed_robustness/run_20260814T063518Z/rep_003/vector_m1p000/selected_box_metrics_grid_candidates.csv`
- `fair_study/seed_robustness/run_20260814T063518Z/rep_003/vector_m1p000/selected_model_metrics_profile_candidates.csv`
- `fair_study/seed_robustness/run_20260814T063518Z/rep_004/scalar_m1p000/selected_box_metrics_grid_candidates.csv`
- `fair_study/seed_robustness/run_20260814T063518Z/rep_004/scalar_m1p000/selected_model_metrics_profile_candidates.csv`
- `fair_study/seed_robustness/run_20260814T063518Z/rep_004/scalar_m6p310/selected_box_metrics_grid_candidates.csv`
- `fair_study/seed_robustness/run_20260814T063518Z/rep_004/scalar_m6p310/selected_model_metrics_profile_candidates.csv`
- `fair_study/seed_robustness/run_20260814T063518Z/rep_004/vector_m10p000/selected_box_metrics_grid_candidates.csv`
- `fair_study/seed_robustness/run_20260814T063518Z/rep_004/vector_m10p000/selected_model_metrics_profile_candidates.csv`
- `fair_study/seed_robustness/run_20260814T063518Z/rep_004/vector_m1p000/selected_box_metrics_grid_candidates.csv`
- `fair_study/seed_robustness/run_20260814T063518Z/rep_004/vector_m1p000/selected_model_metrics_profile_candidates.csv`
- `fair_study/seed_robustness/run_20260814T063518Z/rep_005/scalar_m1p000/selected_box_metrics_grid_candidates.csv`
- `fair_study/seed_robustness/run_20260814T063518Z/rep_005/scalar_m1p000/selected_model_metrics_profile_candidates.csv`
- `fair_study/seed_robustness/run_20260814T063518Z/rep_005/scalar_m6p310/selected_box_metrics_grid_candidates.csv`
- `fair_study/seed_robustness/run_20260814T063518Z/rep_005/scalar_m6p310/selected_model_metrics_profile_candidates.csv`
- `fair_study/seed_robustness/run_20260814T063518Z/rep_005/vector_m10p000/selected_box_metrics_grid_candidates.csv`
- `fair_study/seed_robustness/run_20260814T063518Z/rep_005/vector_m10p000/selected_model_metrics_profile_candidates.csv`
- `fair_study/seed_robustness/run_20260814T063518Z/rep_005/vector_m1p000/selected_box_metrics_grid_candidates.csv`
- `fair_study/seed_robustness/run_20260814T063518Z/rep_005/vector_m1p000/selected_model_metrics_profile_candidates.csv`
- `fair_study/seed_robustness/run_20260814T063518Z/rep_006/scalar_m1p000/selected_box_metrics_grid_candidates.csv`
- `fair_study/seed_robustness/run_20260814T063518Z/rep_006/scalar_m1p000/selected_model_metrics_profile_candidates.csv`
- `fair_study/seed_robustness/run_20260814T063518Z/rep_006/scalar_m6p310/selected_box_metrics_grid_candidates.csv`
- `fair_study/seed_robustness/run_20260814T063518Z/rep_006/scalar_m6p310/selected_model_metrics_profile_candidates.csv`
- `fair_study/seed_robustness/run_20260814T063518Z/rep_006/vector_m10p000/selected_box_metrics_grid_candidates.csv`
- `fair_study/seed_robustness/run_20260814T063518Z/rep_006/vector_m10p000/selected_model_metrics_profile_candidates.csv`
- `fair_study/seed_robustness/run_20260814T063518Z/rep_006/vector_m1p000/selected_box_metrics_grid_candidates.csv`
- `fair_study/seed_robustness/run_20260814T063518Z/rep_006/vector_m1p000/selected_model_metrics_profile_candidates.csv`
- `fair_study/seed_robustness/run_20260814T063518Z/rep_007/scalar_m1p000/selected_box_metrics_grid_candidates.csv`
- `fair_study/seed_robustness/run_20260814T063518Z/rep_007/scalar_m1p000/selected_model_metrics_profile_candidates.csv`
- `fair_study/seed_robustness/run_20260814T063518Z/rep_007/scalar_m6p310/selected_box_metrics_grid_candidates.csv`
- `fair_study/seed_robustness/run_20260814T063518Z/rep_007/scalar_m6p310/selected_model_metrics_profile_candidates.csv`
- `fair_study/seed_robustness/run_20260814T063518Z/rep_007/vector_m10p000/selected_box_metrics_grid_candidates.csv`
- `fair_study/seed_robustness/run_20260814T063518Z/rep_007/vector_m10p000/selected_model_metrics_profile_candidates.csv`
- `fair_study/seed_robustness/run_20260814T063518Z/rep_007/vector_m1p000/selected_box_metrics_grid_candidates.csv`
- `fair_study/seed_robustness/run_20260814T063518Z/rep_007/vector_m1p000/selected_model_metrics_profile_candidates.csv`
- `fair_study/seed_robustness/run_20260814T063518Z/rep_008/scalar_m1p000/selected_box_metrics_grid_candidates.csv`
- `fair_study/seed_robustness/run_20260814T063518Z/rep_008/scalar_m1p000/selected_model_metrics_profile_candidates.csv`
- `fair_study/seed_robustness/run_20260814T063518Z/rep_008/scalar_m6p310/selected_box_metrics_grid_candidates.csv`
- `fair_study/seed_robustness/run_20260814T063518Z/rep_008/scalar_m6p310/selected_model_metrics_profile_candidates.csv`
- `fair_study/seed_robustness/run_20260814T063518Z/rep_008/vector_m10p000/selected_box_metrics_grid_candidates.csv`
- `fair_study/seed_robustness/run_20260814T063518Z/rep_008/vector_m10p000/selected_model_metrics_profile_candidates.csv`
- `fair_study/seed_robustness/run_20260814T063518Z/rep_008/vector_m1p000/selected_box_metrics_grid_candidates.csv`
- `fair_study/seed_robustness/run_20260814T063518Z/rep_008/vector_m1p000/selected_model_metrics_profile_candidates.csv`
- `fair_study/seed_robustness/run_20260814T063518Z/rep_009/scalar_m1p000/selected_box_metrics_grid_candidates.csv`
- `fair_study/seed_robustness/run_20260814T063518Z/rep_009/scalar_m1p000/selected_model_metrics_profile_candidates.csv`
- `fair_study/seed_robustness/run_20260814T063518Z/rep_009/scalar_m6p310/selected_box_metrics_grid_candidates.csv`
- `fair_study/seed_robustness/run_20260814T063518Z/rep_009/scalar_m6p310/selected_model_metrics_profile_candidates.csv`
- `fair_study/seed_robustness/run_20260814T063518Z/rep_009/vector_m10p000/selected_box_metrics_grid_candidates.csv`
- `fair_study/seed_robustness/run_20260814T063518Z/rep_009/vector_m10p000/selected_model_metrics_profile_candidates.csv`
- `fair_study/seed_robustness/run_20260814T063518Z/rep_009/vector_m1p000/selected_box_metrics_grid_candidates.csv`
- `fair_study/seed_robustness/run_20260814T063518Z/rep_009/vector_m1p000/selected_model_metrics_profile_candidates.csv`
- `fair_study/seed_robustness/run_20260814T063518Z/rep_010/scalar_m1p000/selected_box_metrics_grid_candidates.csv`
- `fair_study/seed_robustness/run_20260814T063518Z/rep_010/scalar_m1p000/selected_model_metrics_profile_candidates.csv`
- `fair_study/seed_robustness/run_20260814T063518Z/rep_010/scalar_m6p310/selected_box_metrics_grid_candidates.csv`
- `fair_study/seed_robustness/run_20260814T063518Z/rep_010/scalar_m6p310/selected_model_metrics_profile_candidates.csv`
- `fair_study/seed_robustness/run_20260814T063518Z/rep_010/vector_m10p000/selected_box_metrics_grid_candidates.csv`
- `fair_study/seed_robustness/run_20260814T063518Z/rep_010/vector_m10p000/selected_model_metrics_profile_candidates.csv`
- `fair_study/seed_robustness/run_20260814T063518Z/rep_010/vector_m1p000/selected_box_metrics_grid_candidates.csv`
- `fair_study/seed_robustness/run_20260814T063518Z/rep_010/vector_m1p000/selected_model_metrics_profile_candidates.csv`
- `fair_study/seed_robustness/run_20260814T063518Z/result_manifest.sha256`
- `fair_study/t_seed_robustness/run_t_20260814_final/rep_001/vector_m10p000/selected_model_metrics_profile_candidates.csv`
- `fair_study/t_seed_robustness/run_t_20260820_final/rep_001/scalar_m10p000/selected_box_metrics_grid_candidates.csv`
- `fair_study/t_seed_robustness/run_t_20260820_final/rep_001/scalar_m10p000/selected_model_metrics_profile_candidates.csv`
- `fair_study/t_seed_robustness/run_t_20260820_final/rep_001/vector_m10p000/selected_box_metrics_grid_candidates.csv`
- `fair_study/t_seed_robustness/run_t_20260820_final/rep_001/vector_m10p000/selected_model_metrics_profile_candidates.csv`
- `fair_study/t_seed_robustness/run_t_20260820_final/rep_002/scalar_m10p000/selected_box_metrics_grid_candidates.csv`
- `fair_study/t_seed_robustness/run_t_20260820_final/rep_002/scalar_m10p000/selected_model_metrics_profile_candidates.csv`
- `fair_study/t_seed_robustness/run_t_20260820_final/rep_002/vector_m10p000/selected_box_metrics_grid_candidates.csv`
- `fair_study/t_seed_robustness/run_t_20260820_final/rep_002/vector_m10p000/selected_model_metrics_profile_candidates.csv`
- `fair_study/t_seed_robustness/run_t_20260820_final/rep_003/scalar_m10p000/selected_box_metrics_grid_candidates.csv`
- `fair_study/t_seed_robustness/run_t_20260820_final/rep_003/scalar_m10p000/selected_model_metrics_profile_candidates.csv`
- `fair_study/t_seed_robustness/run_t_20260820_final/rep_003/vector_m10p000/selected_box_metrics_grid_candidates.csv`
- `fair_study/t_seed_robustness/run_t_20260820_final/rep_003/vector_m10p000/selected_model_metrics_profile_candidates.csv`
- `fair_study/t_seed_robustness/run_t_20260820_final/rep_004/scalar_m10p000/selected_box_metrics_grid_candidates.csv`
- `fair_study/t_seed_robustness/run_t_20260820_final/rep_004/scalar_m10p000/selected_model_metrics_profile_candidates.csv`
- `fair_study/t_seed_robustness/run_t_20260820_final/rep_004/vector_m10p000/selected_box_metrics_grid_candidates.csv`
- `fair_study/t_seed_robustness/run_t_20260820_final/rep_004/vector_m10p000/selected_model_metrics_profile_candidates.csv`
- `fair_study/t_seed_robustness/run_t_20260820_final/rep_005/scalar_m10p000/selected_box_metrics_grid_candidates.csv`
- `fair_study/t_seed_robustness/run_t_20260820_final/rep_005/scalar_m10p000/selected_model_metrics_profile_candidates.csv`
- `fair_study/t_seed_robustness/run_t_20260820_final/rep_005/vector_m10p000/selected_box_metrics_grid_candidates.csv`
- `fair_study/t_seed_robustness/run_t_20260820_final/rep_005/vector_m10p000/selected_model_metrics_profile_candidates.csv`
- `fair_study/t_seed_robustness/run_t_20260820_final/rep_006/scalar_m10p000/selected_box_metrics_grid_candidates.csv`
- `fair_study/t_seed_robustness/run_t_20260820_final/rep_006/scalar_m10p000/selected_model_metrics_profile_candidates.csv`
- `fair_study/t_seed_robustness/run_t_20260820_final/rep_006/vector_m10p000/selected_box_metrics_grid_candidates.csv`
- `fair_study/t_seed_robustness/run_t_20260820_final/rep_006/vector_m10p000/selected_model_metrics_profile_candidates.csv`
- `fair_study/t_seed_robustness/run_t_20260820_final/rep_007/scalar_m10p000/selected_box_metrics_grid_candidates.csv`
- `fair_study/t_seed_robustness/run_t_20260820_final/rep_007/scalar_m10p000/selected_model_metrics_profile_candidates.csv`
- `fair_study/t_seed_robustness/run_t_20260820_final/rep_007/vector_m10p000/selected_box_metrics_grid_candidates.csv`
- `fair_study/t_seed_robustness/run_t_20260820_final/rep_007/vector_m10p000/selected_model_metrics_profile_candidates.csv`
- `fair_study/t_seed_robustness/run_t_20260820_final/rep_008/scalar_m10p000/selected_box_metrics_grid_candidates.csv`
- `fair_study/t_seed_robustness/run_t_20260820_final/rep_008/scalar_m10p000/selected_model_metrics_profile_candidates.csv`
- `fair_study/t_seed_robustness/run_t_20260820_final/rep_008/vector_m10p000/selected_box_metrics_grid_candidates.csv`
- `fair_study/t_seed_robustness/run_t_20260820_final/rep_008/vector_m10p000/selected_model_metrics_profile_candidates.csv`
- `fair_study/t_seed_robustness/run_t_20260820_final/rep_009/scalar_m10p000/selected_box_metrics_grid_candidates.csv`
- `fair_study/t_seed_robustness/run_t_20260820_final/rep_009/scalar_m10p000/selected_model_metrics_profile_candidates.csv`
- `fair_study/t_seed_robustness/run_t_20260820_final/rep_009/vector_m10p000/selected_box_metrics_grid_candidates.csv`
- `fair_study/t_seed_robustness/run_t_20260820_final/rep_009/vector_m10p000/selected_model_metrics_profile_candidates.csv`
- `fair_study/t_seed_robustness/run_t_20260820_final/rep_010/scalar_m10p000/selected_box_metrics_grid_candidates.csv`
- `fair_study/t_seed_robustness/run_t_20260820_final/rep_010/scalar_m10p000/selected_model_metrics_profile_candidates.csv`
- `fair_study/t_seed_robustness/run_t_20260820_final/rep_010/vector_m10p000/selected_box_metrics_grid_candidates.csv`
- `fair_study/t_seed_robustness/run_t_20260820_final/rep_010/vector_m10p000/selected_model_metrics_profile_candidates.csv`
- `fair_study/t_seed_robustness/run_t_20260820_final/result_manifest.sha256`
- `scripts/extract_t_importance.mjs`
- `scripts/plot_signal_cross_sections.py`
