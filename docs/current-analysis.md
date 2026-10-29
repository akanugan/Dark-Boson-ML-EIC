# Current analysis guide

Use [`revision/`](../revision/README.md) and the current [`figures/`](../figures/README.md) entries for the corrected three-method comparison. Earlier top-level analysis outputs remain historical records.

## Calculation

Signals are coherent scalar and vector production in electron–gold collisions with an 18 GeV electron beam and 100 GeV per nucleon ion beam. The mass-dependent electron preselection follows [Davoudiasl and Liu, arXiv:2505.08871v4](https://arxiv.org/html/2505.08871v4#S3).

Each method is evaluated with the electron observables and again with nuclear momentum transfer `t` added. Here `t = −(P′ − P)² > 0`; existing ROOT files and code also call it `QA2`. The likelihood is TMVA PDERS, a density estimate fitted to weighted training events. BDT, likelihood, and rectangular configurations and thresholds are selected on validation events using the same objective.

The performance quantity is the approximate background-dominated significance relative to preselection:

```text
R_Z = epsilon_signal × sqrt[(sigma_photon + sigma_DIS)
                           / (epsilon_photon × sigma_photon + sigma_DIS)]
```

Comparisons use ten independent runs per boson/mass group, giving 220 analyses across eleven masses and two boson types. Each uses all six selections. Events, weights, preselection, and objective are shared within a comparison.

## Photon calculation and repairs

Central photons (`|eta_gamma| ≤ 3.5`) and photons outside acceptance are generated separately. The effective rate is `epsilon × sigma_central + sigma_outside`, with nominal central miss probability `epsilon = 1e-6` and unit miss probability outside. Physical component integrals determine the mixture; event counts do not. A separate calibration fixes the common nominal photon rate at each mass.

Independent phase-space and support checks identified six deficient outside-photon files. Their replacements and the affected fitting, validation, and test steps are included in the current results. The physical assumptions, calibration totals, fitting settings, and original unaffected samples were preserved. Check records retain the original source provenance; they are records of the completed calculations rather than new results generated on download.

The selected calibration rates are approximately 26–28% above the reference below 1 GeV and 6.3% above it at 10 GeV. A separate inclusive-distribution discrepancy remains unresolved. Rate agreement and shape agreement are distinct checks.

## Results and response scenarios

At 10 GeV, adding `t` gives approximately 31–39% more simulated significance across the three methods. When all methods include `t`, BDT and likelihood add approximately 3% over rectangular cuts and perform similarly. The purpose of the comparison is to distinguish the contribution of the observable from the smaller contribution of the selection method.

At this mass, all three methods retain a positive benefit from `t` under the tested 10% and 20% Gaussian relative smearing. The [EIC Yellow Report](https://arxiv.org/abs/2103.05419) motivates the resolution scale through visible-final-state studies; the benchmarks are not a calibrated response for this invisible process. Photon-loss scenarios use central miss probabilities `1e-8`, `1e-7`, `1e-6`, and `1e-5`, keeping nominal fitted selections fixed. Shape changes at fixed total rate, rate-only changes, and combined changes are reported separately.

The reference DIS rate is retained without further rejection. Different event-level DIS efficiencies could change the relative method gains.

## Statistical interpretation and downloads

The paired analysis uses 2000 event resamples per run and one million combined run/event draws for the nominal comparisons. The 198 contrasts comprise 66 direct `t` comparisons and 132 pairwise method comparisons. `ci95_*` columns describe pointwise intervals; `family95_*` columns include the combined Bonferroni adjustment. Scenario results use descriptive pointwise intervals outside that family.

The intervals condition on the independent photon calibration and the stated physical model. They omit calibration and detector/model systematics. The [revision-data-v2 release](https://github.com/iRojae/Dark-Boson-ML-EIC/releases/tag/revision-data-v2) supports statistical replay from saved arrays and supplies the selected models. It excludes raw event files. The historical `data-v1` release belongs to the original study; its inclusive photon file is still used by the unchanged Figure 3. See the [data guide](../DATA_DOWNLOAD.md) for the distinction between plotting, statistical replay, and event-level reruns.
