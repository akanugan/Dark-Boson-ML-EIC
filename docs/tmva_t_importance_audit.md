# TMVA exact-t variable-importance extraction audit

- Source run: `/Users/rojaemighty/Dark/fair_study/t_seed_robustness/run_t_20260820_final`
- Scope: 10 independent replicas each for the 10 GeV vector and scalar benchmarks.
- Model selection: for every replica, the selected profile and TMVA seed were read from `selected_model_metrics.csv`; the matching `logs/tmva_<profile>.log` was then used.
- Extraction: the five values were parsed from TMVA's method-specific `Variable Importance` ranking table. Output labels are standardized as `Q^2`, `pT,e`, `eta_e`, `E_e`, and `t`.
- Aggregation: `mean_importance` is the arithmetic mean over the 10 replicas. `sample_sd` uses the sample definition with denominator n-1. The `n` column is 10 for every signal-feature group.
- Validation: 20 selected logs were read; each supplied exactly five distinct features; every per-log importance sum agreed with unity within 0.002.

## Selected logs

| Signal | Replica | TMVA seed | Profile | Importance sum | Log |
|---|---:|---:|---|---:|---|
| vector | rep_001 | 9410031 | depth4 | 1.000100 | `/Users/rojaemighty/Dark/fair_study/t_seed_robustness/run_t_20260820_final/rep_001/vector_m10p000/logs/tmva_depth4.log` |
| vector | rep_002 | 9420031 | depth4 | 1.000100 | `/Users/rojaemighty/Dark/fair_study/t_seed_robustness/run_t_20260820_final/rep_002/vector_m10p000/logs/tmva_depth4.log` |
| vector | rep_003 | 9430031 | depth3_800 | 1.000000 | `/Users/rojaemighty/Dark/fair_study/t_seed_robustness/run_t_20260820_final/rep_003/vector_m10p000/logs/tmva_depth3_800.log` |
| vector | rep_004 | 9440031 | depth3 | 1.000100 | `/Users/rojaemighty/Dark/fair_study/t_seed_robustness/run_t_20260820_final/rep_004/vector_m10p000/logs/tmva_depth3.log` |
| vector | rep_005 | 9450031 | depth3_800 | 1.000100 | `/Users/rojaemighty/Dark/fair_study/t_seed_robustness/run_t_20260820_final/rep_005/vector_m10p000/logs/tmva_depth3_800.log` |
| vector | rep_006 | 9460031 | depth4 | 1.000000 | `/Users/rojaemighty/Dark/fair_study/t_seed_robustness/run_t_20260820_final/rep_006/vector_m10p000/logs/tmva_depth4.log` |
| vector | rep_007 | 9470031 | depth3_800 | 1.000000 | `/Users/rojaemighty/Dark/fair_study/t_seed_robustness/run_t_20260820_final/rep_007/vector_m10p000/logs/tmva_depth3_800.log` |
| vector | rep_008 | 9480031 | depth4 | 0.999900 | `/Users/rojaemighty/Dark/fair_study/t_seed_robustness/run_t_20260820_final/rep_008/vector_m10p000/logs/tmva_depth4.log` |
| vector | rep_009 | 9490031 | depth3_800 | 1.000100 | `/Users/rojaemighty/Dark/fair_study/t_seed_robustness/run_t_20260820_final/rep_009/vector_m10p000/logs/tmva_depth3_800.log` |
| vector | rep_010 | 9500031 | depth3_800 | 1.000100 | `/Users/rojaemighty/Dark/fair_study/t_seed_robustness/run_t_20260820_final/rep_010/vector_m10p000/logs/tmva_depth3_800.log` |
| scalar | rep_001 | 9410131 | depth3_800 | 1.000000 | `/Users/rojaemighty/Dark/fair_study/t_seed_robustness/run_t_20260820_final/rep_001/scalar_m10p000/logs/tmva_depth3_800.log` |
| scalar | rep_002 | 9420131 | depth3 | 0.999900 | `/Users/rojaemighty/Dark/fair_study/t_seed_robustness/run_t_20260820_final/rep_002/scalar_m10p000/logs/tmva_depth3.log` |
| scalar | rep_003 | 9430131 | depth4 | 1.000000 | `/Users/rojaemighty/Dark/fair_study/t_seed_robustness/run_t_20260820_final/rep_003/scalar_m10p000/logs/tmva_depth4.log` |
| scalar | rep_004 | 9440131 | depth3 | 1.000000 | `/Users/rojaemighty/Dark/fair_study/t_seed_robustness/run_t_20260820_final/rep_004/scalar_m10p000/logs/tmva_depth3.log` |
| scalar | rep_005 | 9450131 | depth3 | 1.000000 | `/Users/rojaemighty/Dark/fair_study/t_seed_robustness/run_t_20260820_final/rep_005/scalar_m10p000/logs/tmva_depth3.log` |
| scalar | rep_006 | 9460131 | depth4 | 0.999900 | `/Users/rojaemighty/Dark/fair_study/t_seed_robustness/run_t_20260820_final/rep_006/scalar_m10p000/logs/tmva_depth4.log` |
| scalar | rep_007 | 9470131 | depth2 | 1.000000 | `/Users/rojaemighty/Dark/fair_study/t_seed_robustness/run_t_20260820_final/rep_007/scalar_m10p000/logs/tmva_depth2.log` |
| scalar | rep_008 | 9480131 | depth4 | 1.000000 | `/Users/rojaemighty/Dark/fair_study/t_seed_robustness/run_t_20260820_final/rep_008/scalar_m10p000/logs/tmva_depth4.log` |
| scalar | rep_009 | 9490131 | depth4 | 1.000000 | `/Users/rojaemighty/Dark/fair_study/t_seed_robustness/run_t_20260820_final/rep_009/scalar_m10p000/logs/tmva_depth4.log` |
| scalar | rep_010 | 9500131 | depth3 | 1.000000 | `/Users/rojaemighty/Dark/fair_study/t_seed_robustness/run_t_20260820_final/rep_010/scalar_m10p000/logs/tmva_depth3.log` |

Extractor: `/Users/rojaemighty/.codex/.chatgpt-projects/g-p-6a7861ca81a08191b2a7987fb13fc4cc/analysis/tmva_importance/extract_t_importance.mjs`
CSV: `/Users/rojaemighty/.codex/.chatgpt-projects/g-p-6a7861ca81a08191b2a7987fb13fc4cc/output/csv/tmva_t_importance_10gev.csv`
