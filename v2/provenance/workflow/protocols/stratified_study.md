# Corrected photon fitting and momentum-transfer comparison

Started 24 October 2026, before generating or reading this study's final test samples.

## Objective

Measure the benefit of adding exact simulated t within rectangular cuts, estimated likelihood (TMVA PDERS), and BDT, across 11 masses for scalar and vector bosons. Compare methods under identical input, sampling, weighting, preselection, validation objective and test conditions. The purpose is an accurate comparison, irrespective of which method wins.

Target approximately 10% relative precision on clearly nonzero improvements, assessed with pointwise 95% intervals. Separately report whether the maximum distance from the estimate to its 95% interval endpoints is at most 0.2 percentage points; this provides an absolute precision benchmark near zero. Neither target is a sequential stopping rule or a guaranteed property of a fixed event budget. Final test observations must not be used to tune profiles or thresholds. Initial fitting allocation is ten independent runs per point. If this first fixed allocation misses the precision target, report that outcome; a larger confirmatory allocation requires a documented budget and fresh independent evaluation, rather than repeatedly testing until an ordinary 95% interval becomes sufficiently narrow.

## Samples and physical normalization

- Masses in GeV: .010,.032,.100,.316,1,1.585,2.512,3.981,5,6.310,10.
- Photon central and outside regions are generated separately, with |eta_gamma|=3.5 as boundary. Each split initially uses 100,000 central and 40,000 outside weighted integration attempts; TFoam settings are 2500cells/1500samples and 1000cells/1000samples, respectively. Four generation/fitting jobs at a time.
- Central photon loss is1e-6 nominally; outside loss is1. Four documented response scenarios 1e-8,1e-7,1e-6,1e-5 will be evaluated with fixed selectors, using common samples. These are response benchmarks, not a measured detector uncertainty band.
- The same matrix element, form factor, 18GeV electron and100GeV/nucleon gold beam configuration are retained. The central mapping uses original coordinates; the outside mapping uses the previously checked lab coordinates. Component integrations must have nonzero support, appropriate effective statistics and no dominating event before interpretation.
- Merge physical raw weights as source foam_weight times source pb_per_foam_weight; set merged normalization to1 and retain source stratum/attempt identifiers. Apply the miss probability afterward. Merely concatenating source weights is incorrect.
- A separate calibration integration (rep000) determines each mass's common photon rate before model fitting, independently of final tests. Published effective DIS rates remain fixed and unrejected. All selectors and both input sets use the same calibration rate.
- Existing independently generated signal training/validation samples may be reused with source paths and checksums recorded. They are fitting/development data, not newly blinded samples. Fresh final signal samples use50,000attempts per boson/mass/run, and fresh final photon components use the budgets above.
- Photon samples are shared between boson types, input sets and methods within each mass/run. Independent runs and fitting/validation/final-test splits use distinct seeds. No old event files or prior results are overwritten.

## Fitting and pilot gate

First fit three independent runs at .032 and10GeV for both boson types. These were chosen for the previously identified low-mass sampling problem and main positive benchmark, not from new final outcomes.

Two input sets: log10(Qe2),pt,eta,energy; and those plus log10(t).

- BDT candidates: depth2,depth3,depth4,depth3_800.
- Likelihood candidates: PDERS RMS Gaussian volume h02,h04,h08,h16. The ProcessSetup correction after XML reading remains mandatory. Density fitting requires representative examples; it is not an analytic matrix-element likelihood.
- Rectangular candidate grids40,80,160 with20restarts, plus the unchanged preselection as an explicit all-pass validation candidate.
- Select candidates and thresholds by validation significance objective RZ=epsS*sqrt((Bphoton+BDIS)/(Bphoton*epsPhoton+BDIS)). No final test data enter selection.
- Inspect weighted likelihood score0.5 fractions by photon region on validation data. A selected model with more than1% outside weight at exactly0.5 triggers support review before the full scan. Repeat this check across the completed full scan before generating final tests. This is a numerical warning proxy, not proof that all score0.5 events have zero estimated density. A failed check is investigated using development data; no favorable test results are required to pass.
- Record run variation and physical component rates. Passing the support check is not a statement that target precision or experimental validity is established.

## Evaluation and uncertainty

Only after fitting choices and final budgets are locked are fresh final test samples generated/read. Every method and feature set uses the same signal/background events. Record paired scores and selections once, compressing redundant tables and model XMLs losslessly. Remove only newly generated duplicate TMVA diagnostic trees; retain event files, provenance and model information.

The event bootstrap is paired across all six selections (three methods times two feature sets). Resample photon strata separately, retaining unstored zero-weight attempts when propagating stratum normalization; use conditional signal resampling for efficiencies. Normalize nominal photon shapes to the independent common calibration rate. These intervals condition on that rate; its integration uncertainty is recorded but not propagated. Distinguish shape-only, rate-only, and full response changes in robustness checks. A rate-only control keeps the nominal mixture efficiencies and changes only the total photon rate.

There are66 direct t/electron contrasts and132 pairwise method contrasts. Report pointwise95% intervals and conservative Bonferroni simultaneous intervals for the combined198-comparison family; a positive pointwise interval is not a familywise claim. Use2000paired event draws per point and1million aggregate run/event draws for numerical precision in the simultaneous tails. More bootstrap draws improve numerical quantile estimates, not the underlying physical precision or the adequacy of ten independent fitting runs. Summaries require all ten runs in a mass/boson group. Per-run event-uncertainty scaling excludes fitting variation and must not be interpreted as a required number of independent fits.

The newly fitted comparisons supersede claims about likelihood gains driven by old default scores. Differences from the reference ancillary shapes remain a separate modeling question. Smearing checks must use the updated models/backgrounds consistently before manuscript interpretation. Keep the manuscript unchanged during the pilot; after the full results are verified, update figures and manuscript conservatively around the resulting evidence. Do not upload the manuscript to GitHub or submit it externally as part of this numerical revision.

## Storage and status

Budget approximately40–50GiB additional peak storage while retaining both component and merged photon samples, with compressed candidate scores/models and shared photon data. Stop starting new heavy work below15GiB free. Component data, calibration, model hashes, command success markers, pilot gate and phase status are stored alongside this protocol. Generation and fitting are resume-safe; changed successful commands require explicit new output/protocol handling.

Operational storage adjustment, 25 October 2026: after fitting and all photon generation completed, a 15GiB reserve paused final evaluation at167/220 completed points. The user approved clearing the two identified VS Code caches, recovering5.77GiB. A remaining-output budget of approximately5GiB against17GiB available permits a10GiB reserve for the remaining evaluation/analysis phase, selected with DARK_STUDY_MIN_FREE_GIB=10 on the next safe coordinator restart. This changes only operational disk checks; no events, model choices, thresholds, calibrated rates, statistical settings, or locked protocol gates change. Keep all event/model files and stop new commands below the revised reserve.

Presentation correction after the completed study, 25 October 2026: the primary figure compares all six selections directly: rectangular cuts, likelihood and BDT, each with electron-only inputs and with electron plus t. The vertical quantity is RZ=Z_selection/Z_preselection, with the same mass-specific preselection shared by all six variants. Geometric means and pointwise 95% intervals use the saved paired run/event draws. The new extraction reproduces every existing paired contrast and interval before plotting; it does not refit models or change the locked statistical comparisons. Method-over-cuts and within-method t-benefit figures are secondary views. Run scripts/compare_selections.py --results stratified_refit to regenerate the primary CSV, audit and figure. Once selection_results.csv exists, scripts/plot_stratified_refit.py also regenerates the primary figure.
