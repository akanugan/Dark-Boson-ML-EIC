# EIC invisible dark-boson reproduction and ML study

This unified project contains the original cross-section reproduction and
the subsequent ML study. It creates weighted, event-level scalar and vector
signal samples, sequential Table I cut flows, and deterministic
training/validation/test assignments. The original baseline is preserved
in `frozen_baseline/`.

The exact source, cut table, scan results, and validation figure used at the
handoff are preserved under `frozen_baseline/`. Their hashes are recorded in
`docs/baseline_manifest.md`.

## Publication manuscript

The editable MDPI Particles draft is in [`paper/latex/main.tex`](paper/latex/main.tex),
with its figures and template files included. Build it with:

```sh
make paper
```

Open [`paper/latex/main.pdf`](paper/latex/main.pdf) for the compiled manuscript.
On macOS, you can also double-click `paper/latex/build.command`.
See [`paper/latex/README.md`](paper/latex/README.md) for author placeholders and submission notes.
The original Word manuscript remains in `paper/ML Paper.docx`.

## Reproduce the original comparison

Run `./scripts/reproduce_plot.sh` (or `make plot`) to plot the preserved
`results/vector_scan_fresh.csv` and `results/scalar_scan.csv` tables.
The comparison is written to `plots/vector_scalar_cross_section_validation.pdf`
and `.png`. Build the extended generators and ML tools with `make`.
See `docs/directory_merge_20260909.md` for the directory migration record.

## Run the signal pilot

```bash
./scripts/run_signal_pilot.sh
```

Defaults are 20,000 weighted events per signal type and mass. For a larger
production run, override `SIGNAL_EVENTS`, `VECTOR_CELLS`, `VECTOR_SAMPLES`,
`SCALAR_CELLS`, and `SCALAR_SAMPLES`. Example:

```bash
SIGNAL_EVENTS=200000 VECTOR_CELLS=1500 VECTOR_SAMPLES=500 \
SCALAR_CELLS=8000 SCALAR_SAMPLES=1000 ./scripts/run_signal_pilot.sh
```

Important outputs:

- `results/signal_cutflow.csv`: cumulative weighted cross section after each cut.
- `data/signal_events.csv`: common ML-ready signal table.
- `data/root/`: ROOT files retaining all generated observables and metadata.
- `logs/`: generator output for each signal type and mass.
- `docs/pilot_summary.md`: numerical validation and low-mass limitations.

Validate the merged output with:

```bash
python3 scripts/validate_dataset.py
```

The event weight is stored in pb. Do not count events without using this
weight when computing efficiencies or cross sections.

## Physics status

The signal equations, beams, form factor, coupling, laboratory transformation,
and Table I cuts are inherited from the frozen reproduction. The scalar source
has an optional ROOT-output mode; with identical seed and integration settings,
its original inclusive and selected results are unchanged digit for digit.

These samples define **our equations-as-written baseline**. They must not be
rescaled by the unexplained factor near three in the publication's selected
curves.

## Background status

See `docs/background_generation_status.md` and `docs/analysis_definition.md`.
The paper identifies coherent bremsstrahlung and DIS backgrounds but does not
provide the event files or settings needed to reproduce both samples uniquely.
For the completed proof of concept, coherent photons are generated with the
massless-vector limit of our matrix element, while DIS is conservatively left
unrejected by ML. The raw photon sample does not reproduce the old public
one-dimensional marginals, so the resulting ML gain is explicitly a
model-dependent parton-level result rather than an experimental projection.

## Completed proof-of-concept ML study

The project now also contains our clearly scoped parton-level study.
Read `docs/analysis_definition.md` before using its results. Reproduce it with:

```bash
./scripts/run_ml_study.sh
./scripts/make_plots.sh
```

Final outputs are in `results/ml/ml_metrics.csv`, `models/`, and `plots/`.
The study uses a coherent photon-background model and conservatively assumes
that ML does not reject the published DIS rate. It is suitable as a proof of
concept, not as a detector-level forecast.

## Fair same-complexity comparison

The primary ML question is now tested with the same parton-level complexity as
the reference paper. The published Table I cuts remain the common
preselection. Inside that selected region, a BDT and an independently optimized
rectangular selection are compared on the same held-out weighted events.

Two feature sets are kept separate:

- `electron`: `log10(Qe2)`, electron `pT`, `eta`, and energy. This is the fair
  comparison using the variables in the published Table I selection.
- `electron_qa2`: the same variables plus exact generator-level `log10(QA2)`.
  This is an idealized upper-bound study, not a detector-level observable
  claim.

Run representative points with:

```bash
./scripts/run_fair_pilot.sh
```

Read `docs/fair_analysis_design.md` before interpreting the output. Numerical
results and the comparison plot are written to `fair_study/results/`.
