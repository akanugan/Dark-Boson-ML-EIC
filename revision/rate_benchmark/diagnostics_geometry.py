#!/usr/bin/env python3
"""Summarize read-only CM support geometry diagnostics."""
from pathlib import Path
import csv,json,math,statistics as st
BASE=Path(__file__).resolve().parent
summary={}
def corr(a,b):
    ma,mb=st.mean(a),st.mean(b)
    return sum((x-ma)*(y-mb) for x,y in zip(a,b))/math.sqrt(sum((x-ma)**2 for x in a)*sum((y-mb)**2 for y in b))
for tag,box in [('m0p032',[(.74,.81),(.02,.12),(.08,.45),(0,.25)]),('m10p000',[(.74,.81),(.06,.70),(0,.09),(0,.25)])]:
    rows=list(csv.DictReader((BASE/('diagnostics_mapping_'+tag+'.csv')).open()))
    vals=[[float(r[f'cm_x{j}']) if j<3 else 2*min(float(r['cm_x3']),1-float(r['cm_x3'])) for j in range(4)] for r in rows]
    widths=list(csv.DictReader((BASE/('diagnostics_widths_'+tag+'.csv')).open()))
    result={'checked_weight_proportional_points':len(rows),'coordinates':'historical log-uniform t, linear pair mass, linear decay cos(theta), folded azimuth = 2*min(original full-azimuth x3,1-x3)',
            'correlations':{f'{i},{j}':corr([v[i] for v in vals],[v[j] for v in vals]) for i in range(4) for j in range(i+1,4)},
            'mixture_box':box,'box_unit_volume':math.prod(b-a for a,b in box),
            'design_points_inside_box':sum(all(a<=z<=b for (a,b),z in zip(box,v)) for v in vals),
            'box_coverage_warning':'Same points motivated box design; not an independent coverage or convergence validation.',
            'local_widths_original_full_azimuth_coordinates':{}}
    for key in ['width_x0','width_x1','width_x2','width_x3','product_local_axis_widths']:
        a=sorted(float(r[key]) for r in widths)
        result['local_widths_original_full_azimuth_coordinates'][key]={'min':a[0],'p10':a[10],'median':st.median(a),'p90':a[90],'max':a[-1]}
    summary[tag]=result
(BASE/'diagnostics_geometry.json').write_text(json.dumps(summary,indent=2)+'\n')
md=['# Why adaptive CM outside-photon integration can miss the dominant contribution','',
    'This is a read-only diagnostic of completed lab samples. No new Monte Carlo events or integrals were generated. The historical and lab densities already agree after the coordinate Jacobian at the 100 weight-proportional checked events for each mass (see diagnostics_mapping.md). That check gives no evidence of a physical density or constant-Jacobian inconsistency at those events.','',
    'The inverse historical CM coordinates show strongly correlated support. At the low-mass preselection, the correlation between the log-t coordinate and linear pair-mass coordinate is -0.948, and between pair mass and decay polar cosine is -0.842. At 10 GeV, the latter correlation is -0.826. Dominant events lie near folded azimuth coordinate 0 (the observed medians are about 0.063 at both masses).','',
    'The historical decay polar axis is the original CM z axis; it is not aligned with the narrow allowed lab photon cone after the pair boost. Consequently the lab outside-acceptance condition and electron cuts become a narrow moving region in the CM coordinates. Improving only the t marginal does not follow these correlations.','',
    '## Local one-coordinate acceptance widths','',
    'At each checked point, vary one historical unit coordinate while holding the other three fixed, checking the unchanged electron cuts and outside-photon requirement. Grow a step from 1e-7 until the first detected rejection, then refine the boundary by bisection. Azimuth is periodic. This measures a local accepted neighborhood; it is not an exhaustive domain scan or proof that no rejection interval was crossed between trial steps.','',
    '| Mass | Median log-t-coordinate width | Median pair-mass-coordinate width | Median decay-cosine width | Median full-azimuth-coordinate width |',
    '|---|---:|---:|---:|---:|']
for tag in ['m0p032','m10p000']:
    w=summary[tag]['local_widths_original_full_azimuth_coordinates']
    md.append('| '+('0.032 GeV' if tag=='m0p032' else '10 GeV')+' | '+' | '.join(f"{w['width_x'+str(j)]['median']:.6g}" for j in range(4))+' |')
md+=['','The small conditional widths, together with strong correlations, explain why an adaptive sampler may fail to discover important outside-photon sectors even when marginal t sampling is improved. The product of these widths is merely a local geometric diagnostic. It is **not** the total support volume or an estimate of missed cross section.','',
     '## Exact sampling improvements','',
     'A mixture proposal over the original four unit CM coordinates can allocate a fixed fraction to uniform sampling over the complete domain and the remainder to a joint box covering the observed dominant region. With mixture density q(y), evaluate f_CM(y)/q(y). The uniform component keeps q positive everywhere; the box is an importance-sampling allocation rather than a physical cut or rate adjustment. The region must be judged by independent convergence and support checks, not agreement with a reference rate.','',
     'Direct IID sampling from this known mixture would provide a particularly useful independent check: unlike applying TFoam on top of the mixture map, it does not introduce another adaptive proposal that can fail to discover a sector. Its estimator is the sample mean of f_CM/q; numerical uncertainties and tails still require independent repetitions and increased sample budgets.','',
     'A more elaborate exact mapping can keep CM t and pair mass but describe the photon direction directly in the two lab cones, solving its energy from the pair mass shell and retaining the exact angular Jacobian and every physical root. This follows the moving angular support directly, but root coverage and finite-regulator cases need careful treatment. It is a design option, not an implemented or validated result here.','',
     'Raw results: diagnostics_widths_m0p032.csv and diagnostics_widths_m10p000.csv. diagnostics_geometry.json contains correlations, local width summaries, and design-box diagnostics. The box boundaries were informed by the same 100 checked points, so their coverage of those points is not independent validation.']
(BASE/'diagnostics_geometry.md').write_text('\n'.join(md)+'\n')
print('\n'.join(md))
