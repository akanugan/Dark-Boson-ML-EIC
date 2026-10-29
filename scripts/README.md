# Original-study wrappers

**OLD STUDY ONLY:** these shell and Python entry points generate, fit, evaluate, or summarize the original signal pilot and BDT-versus-cuts studies. They do not produce the corrected three-method results.

| Scripts | Original role |
|---|---|
| `run_signal_pilot.sh`, `combine_signal_outputs.sh`, `validate_dataset.py` | Signal-event pilot and merged weighted tables. |
| `run_ml_study.sh`, `validate_ml_outputs.py`, `make_plots.sh` | First BDT production and plots. |
| `run_fair_pilot.sh`, `summarize_fair_pilot.py`, `plot_fair_pilot.py` | Original matched-input BDT-versus-cuts pilot. |
| `run_rigorous_development.sh`, `select_rigorous_models.py`, `finalize_rigorous_selection.py`, `generate_sealed_tests.sh`, `evaluate_sealed_tests.sh`, `run_sealed_evaluation.py`, `summarize_rigorous_final.py` | Original model selection and held-out scan. |
| `run_seed_robustness.sh`, `summarize_seed_robustness.py`, `run_t_seed_robustness.sh`, `summarize_t_seed_robustness.py` | Original independently repeated benchmarks. |
| `plot_bdt_comparison.py`, `extract_t_importance.mjs` | Original comparison and importance summaries. |
| `reproduce_plot.sh`, `plot_vector_scalar.py`, `plot_signal_cross_sections.py` | Original signal cross-section plotting; these curves remain useful, but the canonical current Figure 2 entry point is under `figures/`. |

Use [`revision/scripts/README.md`](../revision/scripts/README.md) for the current calculation and [`figures/README.md`](../figures/README.md) for current figures. None of the current figure entry points or corrected-analysis drivers calls these top-level wrappers. Shared C++ dependencies remain under [`src/`](../src/README.md).
