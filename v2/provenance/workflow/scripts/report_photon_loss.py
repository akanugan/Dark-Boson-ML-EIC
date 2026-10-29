#!/usr/bin/env python3
"""Verify the completed study and write a readable, reproducible report."""
from pathlib import Path
import csv
import hashlib
import json
import numpy as np

BASE=Path(__file__).resolve().parents[1]
OUT=BASE/'photon_loss_10gev'

def rows(path):
    with path.open() as f:return list(csv.DictReader(f))

def main():
    summary=rows(OUT/'summary.csv')
    runs=rows(OUT/'run_results.csv')
    components=rows(OUT/'component_diagnostics.csv')
    rates=rows(OUT/'scenario_rates.csv')
    shapes=rows(OUT/'shape_distances.csv')
    checks=[]
    assert len(summary)==72 and len(runs)==240 and len(components)==20
    assert all(r['exit_code']==0 for r in json.loads((OUT/'validation.json').read_text()))
    checks.append('All 20 ROOT samples pass metadata, preselection, finite-weight, positive-t and photon-loss-rule validation.')
    assert all(np.isclose(float(r['foam_error_pb']),float(r['event_error_pb']),rtol=2e-7) for r in components)
    checks.append('Attempt-level weighted-event error agrees with TFoam integration error in all 20 strata.')
    for rep in range(1,11):
        point=np.load(OUT/f'rep_{rep:03d}/nominal_RZ.npy')
        boot=np.load(OUT/f'rep_{rep:03d}/bootstrap_RZ.npy')
        assert point.shape==(3,4,2,3) and boot.shape==(2000,3,4,2,3)
        assert np.all(np.isfinite(boot)) and np.all(boot>0)
        assert np.array_equal(point[1,2],point[2,2])
        assert np.array_equal(boot[:,1,2],boot[:,2,2])
    checks.append('Full and rate-only controls agree exactly at nominal epsilon, including every paired bootstrap draw.')
    for mode in ['shape_only','rate_and_shape','rate_only']:
        for typ in ['vector','scalar']:
            for epsilon in [1e-8,1e-7,1e-6,1e-5]:
                subset=[r for r in runs if r['mode']==mode and r['boson']==typ and float(r['epsilon'])==epsilon]
                assert len(subset)==10
                for numerator,denominator,pair in [('BDT','cuts','BDT/cuts'),('likelihood','cuts','likelihood/cuts'),('BDT','likelihood','BDT/likelihood')]:
                    value=100*np.expm1(np.mean([np.log(float(r[numerator+'_RZ'])/float(r[denominator+'_RZ'])) for r in subset]))
                    target=next(r for r in summary if r['mode']==mode and r['boson']==typ and float(r['epsilon'])==epsilon and r['comparison']==pair)
                    assert np.isclose(value,float(target['advantage_pct']),rtol=1e-10)
    checks.append('All 72 aggregate pairwise point estimates reproduce directly from the 240 per-run performance rows.')
    assert all(float(r['TV_to_nominal'])==0 for r in shapes if float(r['epsilon'])==1e-6)
    assert all(float(r['TV_to_nominal'])>.05 for r in shapes if r['stage']=='Table_I' and float(r['epsilon'])!=1e-6)
    checks.append('Every nonnominal scenario changes all three inspected preselection marginals and the joint pT/t histogram; underflow/overflow retained.')
    (OUT/'verification.json').write_text(json.dumps({'state':'passed','checks':checks},indent=2))
    def table(mode):
        lines=['| Central photon miss probability | Vector: BDT vs cuts | Vector: likelihood vs cuts | Scalar: BDT vs cuts | Scalar: likelihood vs cuts |',
               '|---|---:|---:|---:|---:|']
        for epsilon in [1e-8,1e-7,1e-6,1e-5]:
            cells=[f'{epsilon:.0e}']
            for typ in ['vector','scalar']:
                for pair in ['BDT/cuts','likelihood/cuts']:
                    r=next(r for r in summary if r['mode']==mode and r['boson']==typ and r['comparison']==pair and float(r['epsilon'])==epsilon)
                    cells.append(f"{float(r['advantage_pct']):.2f}% [{float(r['ci95_low']):.2f}, {float(r['ci95_high']):.2f}]")
            lines.append('| '+' | '.join(cells)+' |')
        return '\n'.join(lines)
    text='''# Photon-loss shape robustness at 10 GeV

Completed for vector and scalar bosons using ten existing independent generation/training runs per boson. All three methods receive the same events and inputs in each comparison. Models, thresholds, rectangular cuts and signal test samples remain fixed. The new photon samples are independent of model fitting and optimization.

## What was varied and why

Davoudiasl and Liu, arXiv:2505.08871v4, Section III, assumes central photon loss probabilities between 1e-8 and 1e-5, and probability one outside |eta_gamma| > 3.5: https://arxiv.org/html/2505.08871v4#S3 . We evaluated the four decade values. This is a documented response-scenario range, not a measured EIC uncertainty band.

The effective photon background is epsilon * sigma_central + sigma_outside. Changing epsilon changes the mixture of two physically distinct photon regions, rather than merely multiplying every event by the same factor. The DIS contribution alone remains fixed at 0.0155 pb and is unrejected, so this isolates photon-response assumptions rather than changing all detector inefficiencies simultaneously.

Each independent photon realization uses 100,000 central and 40,000 outside-region weighted integration attempts. Ten realizations give 1.4 million attempts. The same photon realization is used for both boson types. No weights are capped or events removed to improve a result.

Central production uses the original phase-space coordinates restricted to the central region. Outside production uses lab coordinates to sample the rare forward/backward region efficiently. The matrix element, nuclear form factor, flux, couplings and electron preselection are unchanged. The alternative coordinate density was checked against the original density times a finite-difference coordinate Jacobian at 50 outside-region points; the largest relative discrepancy was 5.23e-6. This checks the coordinate transformation, not an independent matrix-element calculation. See mapping_check.cpp and mapping_check.log.

## Main findings

- The documented scenarios produce substantial normalized shape changes, including the joint electron-pT/t distribution. This is a shape test, not just a rate rescaling.
- The BDT retains a small advantage over the existing rectangular cuts in all four scenarios. Its pointwise intervals remain above zero. This is evidence across these specific tested scenarios, not a claim covering every possible background model.
- With the existing fixed models, likelihood gives larger numerical gains than cuts and BDT. A subsequent support diagnostic found that 82–99% of the outside-photon weighted sample receives exactly the PDERS default score 0.5, with selected thresholds falling above or below it. The large likelihood gains and run-to-run spread therefore require a representative training/validation refit before interpretation as learned separation. See uncertainty_diagnosis.md and likelihood_support_diagnostics.csv. The fixed-selector results remain a description of the existing models' response to these scenarios.
- Adequately sampling the outside component matters even at nominal epsilon=1e-6. The newly integrated photon rate is approximately 0.35045 pb, versus the old comparison's fixed 0.33266971 pb and the updated reference table's rounded 0.33 pb. The new result should not be described as a 1%-level rate agreement.
- At epsilon=1e-8, fixed BDT and cuts both give lower significance than retaining the initial preselection alone (RZ < 1). A relative BDT advantage over cuts is not automatically an advantage over doing no second-stage selection.

The reported improvement is in S/sqrt(B), not signal yield or coupling. Point estimates are geometric mean ratios over ten runs. Brackets below are pointwise 95% intervals from paired event and run resampling (2,000 event draws per run; 20,000 aggregate draws). These are not familywise-adjusted discovery claims. The photon strata are resampled separately over all attempted events, including unstored zero-weight attempts. Every method/scenario uses the same resample. Signal efficiencies use the same paired accepted-event resamples.

## Shape only: total photon rate fixed at 0.33266971 pb

'''+table('shape_only')+'''

## Photon rate and shape both varied

'''+table('rate_and_shape')+'''

## Rate only control: nominal normalized shape retained

'''+table('rate_only')+'''

## Limits on the conclusion

This evaluates the robustness of the existing nominal selectors without refitting or reoptimizing for an alternative response. It does not rank methods after scenario-specific retraining. It does not identify the cause of the reference ancillary histogram discrepancy, provide an updated reference joint distribution, or establish the correct experimental response. Existing signal, matrix-element, exact-t and unrejected-DIS assumptions remain. The old arbitrary marginal reweighting study in ../photon_shape_test is separate and is not used here.

## Files and reproduction

- plan.json: assumptions, source, fixed conditions and statistical procedure.
- rep_001 through rep_010: component ROOT files, generation metadata/logs, model hashes, paired per-event scores, per-run metrics and bootstrap arrays.
- component_diagnostics.csv: cross sections, MC errors, effective sample sizes and maximum weight fractions.
- scenario_rates.csv: calculated rates and outside-region fractions.
- shape_distances.csv: binned total-variation distances to nominal, before and after second-stage selections. These are bin-dependent descriptive distances, not reference validation p-values.
- shape_histograms.csv and component_histograms.npz: normalized marginal probabilities and component integrals, including overflow bins.
- run_results.csv: all per-run efficiencies and significance improvements.
- summary.csv: all three pairwise aggregate comparisons, for shape only, rate plus shape, and rate only.
- shape_changes.png/pdf and performance_*.png/pdf: comparison figures.
- validation.json, verification.json: completed input and numerical checks.

From the project workspace, with ROOT available and the existing trained models in revision_analysis/results:

```sh
python3 revision_analysis/scripts/run_photon_loss_generation.py
python3 revision_analysis/scripts/export_photon_loss_scores.py
python3 revision/scripts/evaluate_photon_loss.py
python3 revision/scripts/plot_photon_loss.py
python3 revision/scripts/report_photon_loss.py
```

Generation, model evaluation and paired event bootstrap each run four jobs concurrently. New generator sources are revision_analysis/src/generate_photon_regions.cpp and generate_photon_lab.cpp; binaries link the existing project headers, ROOT and libFoam. The README and plots are analysis outputs; the manuscript has not been edited for these findings.
'''
    (OUT/'README.md').write_text(text)
    roots=[BASE/'scripts'/s for s in ['run_photon_loss_generation.py','export_photon_loss_scores.py','evaluate_photon_loss.py','plot_photon_loss.py','report_photon_loss.py']]
    roots += [BASE/'src'/s for s in ['generate_photon_regions.cpp','generate_photon_lab.cpp','export_shape_scores.cpp']]
    roots += sorted(OUT.glob('rep_*/*.root'))
    roots += sorted(OUT.glob('rep_*/*_RZ.npy'))
    roots += [OUT/s for s in ['plan.json','summary.csv','run_results.csv','component_diagnostics.csv','scenario_rates.csv','shape_distances.csv','README.md']]
    manifest={str(p.relative_to(BASE)):hashlib.sha256(p.read_bytes()).hexdigest() for p in roots}
    (OUT/'sha256.json').write_text(json.dumps(manifest,indent=2))
    print('Passed',len(checks),'checks; wrote README and',len(manifest),'checksums.')

if __name__=='__main__':main()
