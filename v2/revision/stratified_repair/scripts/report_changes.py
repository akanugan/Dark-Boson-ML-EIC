#!/usr/bin/env python3
"""Compare corrected inference with the preserved original study."""
import csv
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
OLD=ROOT.parent/'stratified_refit'
AFFECTED={1.585,2.512,5.,6.31}
KEY=('signal_type','mass_GeV','kind','feature_set','method','comparison')

def rows(p):
    with p.open() as f:return list(csv.DictReader(f))
def key(r):return tuple(float(r[x]) if x=='mass_GeV' else r[x] for x in KEY)
def write(p,data):
    with p.open('w',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(data[0]));w.writeheader();w.writerows(data)

def main():
    old={key(r):r for r in rows(OLD/'summary.csv')}
    new={key(r):r for r in rows(ROOT/'summary.csv')}
    if len(old)!=198 or old.keys()!=new.keys():raise RuntimeError('Incomplete comparison family')
    changes=[];unchanged_max=0.;unchanged_rows=0
    for k,n in new.items():
        o=old[k]
        delta=float(n['advantage_pct'])-float(o['advantage_pct'])
        record={x:n[x] for x in KEY}
        record.update(old_advantage_pct=float(o['advantage_pct']),new_advantage_pct=float(n['advantage_pct']),
            change_percentage_points=delta,
            old_ci95_low_pct=float(o['ci95_low_advantage_pct']),old_ci95_high_pct=float(o['ci95_high_advantage_pct']),
            new_ci95_low_pct=float(n['ci95_low_advantage_pct']),new_ci95_high_pct=float(n['ci95_high_advantage_pct']),
            old_family95_low_pct=float(o['family95_low_advantage_pct']),new_family95_low_pct=float(n['family95_low_advantage_pct']),
            affected_mass=k[1] in AFFECTED)
        changes.append(record)
        if k[1] not in AFFECTED:
            unchanged_rows+=1
            for column in ('geometric_mean_ratio','advantage_pct','ci95_low_ratio','ci95_high_ratio',
                           'family95_low_ratio','family95_high_ratio'):
                difference=abs(float(n[column])-float(o[column]));unchanged_max=max(unchanged_max,difference)
                if difference>2e-12:raise RuntimeError('Unaffected inference changed: '+str(k)+' '+column)
    write(ROOT/'before_after.csv',changes)
    component=[]
    for r in json.loads((ROOT/'photon_replacement_integrations.json').read_text()):
        tag=f"m{r['mass_GeV']:.3f}".replace('.','p')
        c=json.loads((OLD/'data'/f"rep_{r['rep']:03d}"/tag/f"{r['split']}_central.json").read_text())['sigma_pb']*1e-6
        before=r['original_sigma_pb'];after=r['sigma_pb']
        component.append(dict(mass_GeV=r['mass_GeV'],rep=r['rep'],split=r['split'],
            old_outside_rate_pb=before,new_outside_rate_pb=after,
            old_outside_fraction=before/(c+before),new_outside_fraction=after/(c+after)))
    write(ROOT/'component_changes.csv',component)
    affected=[r for r in changes if r['affected_mass']]
    biggest=max(affected,key=lambda r:abs(r['change_percentage_points']))
    state=dict(passed=True,contrasts=198,affected_contrasts=len(affected),unchanged_contrasts=unchanged_rows,
        maximum_unchanged_numeric_difference=unchanged_max,
        maximum_absolute_change_pp=abs(biggest['change_percentage_points']),largest_change=biggest,
        repaired_components=6,refitted_points=4,validation_reselected_points=4,test_only_reevaluated_points=4,
        physical_model_changed=False,calibrated_rates_changed=False,manuscript_changed=False,
        interpretation='Correction of diagnosed numerical sampling failures; not a new blinded confirmation.')
    (ROOT/'repair_comparison_audit.json').write_text(json.dumps(state,indent=2)+'\n')
    report=['# Six-file photon repair: results','',
        'The six diagnosed outside-photon files were regenerated and validated. Four mass/boson/run points were refitted, four had validation choices repeated using their retained trained models, and four were reevaluated with fixed selections. The other 208 point analyses were reused after input/provenance checks.','',
        'Physics, calibrated photon totals, DIS rates, signal events, fitting settings and inference settings are unchanged. This isolates the sampling correction. Original results remain in `../stratified_refit`; this is a correction after the earlier results were inspected, not a new blinded confirmation.','',
        f"All {unchanged_rows} contrasts at unaffected masses reproduce the original values (maximum numeric difference {unchanged_max:.3g}). The 10 GeV nominal and smearing results are unchanged.",'',
        '| Mass (GeV) | Run | Split | Old outside rate (pb) | Repaired outside rate (pb) | Outside fraction before / after |',
        '|---:|---:|---|---:|---:|---:|']
    for r in sorted(component,key=lambda x:(x['mass_GeV'],x['rep'],x['split'])):
        report.append(f"| {r['mass_GeV']:g} | {r['rep']} | {r['split']} | {r['old_outside_rate_pb']:.7f} | {r['new_outside_rate_pb']:.7f} | {100*r['old_outside_fraction']:.2f}% / {100*r['new_outside_fraction']:.2f}% |")
    report+=['','## Benefit of adding t at affected masses','',
        'Numbers are percent significance gains from adding t within each method, using geometric-mean ratios across ten runs. Intervals and all pairwise method comparisons are in `summary.csv` and `before_after.csv`.','',
        '| Boson | Mass (GeV) | Method | Before (%) | After (%) | Change (percentage points) |',
        '|---|---:|---|---:|---:|---:|']
    for r in sorted([r for r in affected if r['kind']=='direct_t'],key=lambda x:(x['signal_type'],float(x['mass_GeV']),x['method'])):
        report.append(f"| {r['signal_type']} | {float(r['mass_GeV']):g} | {r['method']} | {r['old_advantage_pct']:.3f} | {r['new_advantage_pct']:.3f} | {r['change_percentage_points']:+.3f} |")
    report+=['','## Scan-wide method comparisons','',
        'Counts below are out of 22 boson/mass comparisons. A positive lower bound means the interval excludes zero advantage. These counts describe the existing inference procedure; the repair is not a new independent experiment.','',
        '| Inputs | Comparison | Positive pointwise 95% lower bound, before / after | Positive family-adjusted 95% lower bound, before / after |',
        '|---|---|---:|---:|']
    for feature in ('electron','electron_qa2'):
        for comparison in ('bdt_over_cuts','likelihood_over_cuts','bdt_over_likelihood'):
            group=[r for r in changes if r['kind']=='method' and r['feature_set']==feature and r['comparison']==comparison]
            if len(group)!=22:raise RuntimeError('Incomplete method-comparison group')
            counts=[sum(float(r[c])>0 for r in group) for c in (
                'old_ci95_low_pct','new_ci95_low_pct','old_family95_low_pct','new_family95_low_pct')]
            report.append(f"| {'Electron variables + t' if feature=='electron_qa2' else 'Electron variables'} | {comparison} | {counts[0]} / {counts[1]} | {counts[2]} / {counts[3]} |")
    report+=['',f"Largest change among the 72 affected paired contrasts: {biggest['change_percentage_points']:+.3f} percentage points for {biggest['signal_type']}, {float(biggest['mass_GeV']):g} GeV, {biggest['feature_set']}, {biggest['comparison']}.",'',
        '## Additional checks','',
        'The fitting-settings audit confirms identical original settings, seeds and executable bytes for all refits and rectangular searches. All 64 candidate XML contents in validation-only repairs are unchanged. The evaluation-only validation helper also reproduces all shared numeric metrics for 16 original selected profiles on their unchanged original validation samples. See `fitting_settings_audit.json` and `qa/original_validation/summary.md`.','',
        'Weighted distribution checks confirm that the repaired 2.512 GeV test component restores the electron-energy-below-2-GeV fraction from 12.03% to 67.59%; the 6.31 GeV validation component restores it from 1.76% to 65.42%. The three 1.585 GeV repairs retain similar normalized invariant shapes while restoring the missing mirror contribution and its mixture weight. These are fractions within the outside component, not within the total background. See `qa/distributions/README.md` and `qa/distributions/electron_energy.png`.','',
        '## Files and interpretation','',
        '- `photon_repair_summary.md`: generation, physical schema, signed-mirror and rate checks.',
        '- `reuse_audit.json`: verification of unchanged data/models and mixed analysis provenance.',
        '- `repair_comparison_audit.json`: before/after consistency and correction scope.',
        '- `summary.csv`: all 198 paired comparisons and intervals; `selection_results.csv`: all six selections.',
        '- `before_after.csv`: complete comparison with previous point estimates and intervals.',
        '- `figures/selection_comparison.png`: corrected six-selection scan.',
        '- `figures/t_information_gain.png`: corrected benefit of t for all three methods.',
        '- `figures/method_comparison_electron.png` and `method_comparison_electron_qa2.png`: method comparisons.',
        '',
        'This repair addresses the six demonstrated sampling failures. It does not settle the reference-rate discrepancy, add missing physical contributions or propagate calibration/model uncertainty into the reported statistical intervals.','']
    (ROOT/'results.md').write_text('\n'.join(report))
    print(json.dumps(state,indent=2))

if __name__=='__main__':main()
