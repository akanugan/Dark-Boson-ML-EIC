#!/usr/bin/env python3
"""Summarize completed outside-support diagnostics; no generation or input mutation."""
from pathlib import Path
import csv,json,math,statistics as st
BASE=Path(__file__).resolve().parent
records=[json.loads(s) for s in (BASE/'support_diagnostics.jsonl').read_text().splitlines()]
flags=list(csv.DictReader((BASE.parent/'background_audit/convergence_flags.csv').open()))
flag_by_seed={int(f['seed']):f for f in flags}
rows=[]
for r in records:
    config=dict(item.split('=',1) for item in r['configuration'].split(';') if '=' in item)
    path=Path(r['file']);g=r['groups']['outside'];total=r['groups']['all']
    mass=float(config['cut_mass_GeV']);route=path.parts[-3];rep=int(path.parts[-2].split('_')[1]);seed=int(config['seed'])
    assert r['miss_probability_mismatches']==0
    assert abs(r['reconstructed_stored_sigma_pb']/r['stored_sigma_total_pb']-1)<1e-10
    assert abs(total['effective_cross_section_pb']/g['effective_cross_section_pb']-1)<1e-12
    assert abs(g['event_sampling_error_pb']/r['stored_sigma_error_pb']-1)<1e-9
    energy_under_2=sum(g['electron_energy_effective_pb'][:5])/g['effective_cross_section_pb']
    row=dict(mass_GeV=mass,route=route,replicate=rep,seed=seed,
             sigma_pb=g['effective_cross_section_pb'],sigma_error_pb=r['stored_sigma_error_pb'],
             effective_n=g['effective_n'],max_weight_fraction=g['max_effective_weight_fraction'],
             photon_py_positive_fraction=g['photon_py_positive_fraction'],
             azimuth_mirror_integrated=int(config.get('azimuth_mirror_integrated','0')),
             electron_energy_lt2_fraction=energy_under_2,
             electron_energy_mean_GeV=g['electron_energy_GeV']['mean'],
             electron_energy_median_GeV=g['electron_energy_GeV']['p50'],
             electron_eta_mean=g['electron_eta']['mean'],
             electron_eta_median=g['electron_eta']['p50'],
             t_mean_GeV2=g['t_GeV2']['mean'],t_q10_GeV2=g['t_GeV2']['p10'],
             t_median_GeV2=g['t_GeV2']['p50'],t_q90_GeV2=g['t_GeV2']['p90'],root_file=r['file'])
    if route=='original_lab':
        flag=flag_by_seed[seed]
        row['saved_flagged_rate_pb']=float(flag['sigma_pb'])
        row['replay_relative_difference']=row['sigma_pb']/row['saved_flagged_rate_pb']-1
        assert abs(row['replay_relative_difference'])<1e-7
    rows.append(row)
rows.sort(key=lambda x:(x['mass_GeV'],x['route'],x['seed']))
def csvwrite(name,data):
    fields=list(dict.fromkeys(k for r in data for k in r))
    with (BASE/name).open('w',newline='') as f:
        w=csv.DictWriter(f,fieldnames=fields);w.writeheader();w.writerows(data)
csvwrite('support_summary.csv',rows)
groups=[]
for m in sorted({r['mass_GeV'] for r in rows}):
    for route in ['original_lab','transformed_lab','independent_lab']:
        rs=[r for r in rows if r['mass_GeV']==m and r['route']==route]
        n=len(rs);rates=[r['sigma_pb'] for r in rs]
        groups.append(dict(mass_GeV=m,route=route,n=n,mean_rate_pb=st.mean(rates),
              seed_sd_pb=st.stdev(rates) if n>1 else '',seed_sem_pb=st.stdev(rates)/math.sqrt(n) if n>1 else '',
              quadrature_mean_error_pb=math.sqrt(sum(r['sigma_error_pb']**2 for r in rs))/n,
              min_rate_pb=min(rates),max_rate_pb=max(rates),
              mean_electron_energy_lt2_fraction=st.mean(r['electron_energy_lt2_fraction'] for r in rs),
              mean_electron_energy_GeV=st.mean(r['electron_energy_mean_GeV'] for r in rs),
              mean_electron_eta=st.mean(r['electron_eta_mean'] for r in rs),
              mean_t_median_GeV2=st.mean(r['t_median_GeV2'] for r in rs)))
csvwrite('support_group_summary.csv',groups)
pairs=[]
for old in [r for r in rows if r['route']=='original_lab']:
    new=next(r for r in rows if r['route']=='transformed_lab' and r['seed']==old['seed'])
    indep=next(g for g in groups if g['route']=='independent_lab' and g['mass_GeV']==old['mass_GeV'])
    pairs.append(dict(mass_GeV=old['mass_GeV'],seed=old['seed'],original_sigma_pb=old['sigma_pb'],
           transformed_sigma_pb=new['sigma_pb'],independent_mean_sigma_pb=indep['mean_rate_pb'],
           transformed_over_original=new['sigma_pb']/old['sigma_pb'],
           transformed_vs_independent_percent=100*(new['sigma_pb']/indep['mean_rate_pb']-1),
           original_electron_energy_lt2_fraction=old['electron_energy_lt2_fraction'],
           transformed_electron_energy_lt2_fraction=new['electron_energy_lt2_fraction'],
           independent_electron_energy_lt2_fraction=indep['mean_electron_energy_lt2_fraction'],
           original_electron_eta_mean=old['electron_eta_mean'],transformed_electron_eta_mean=new['electron_eta_mean'],
           original_t_median_GeV2=old['t_median_GeV2'],transformed_t_median_GeV2=new['t_median_GeV2']))
csvwrite('support_pairs.csv',pairs)
md=['# Focused outside-support diagnostics','',
    'Checked all 24 completed ROOT outputs. The six original-generator replays reproduce their retained flagged rates to the printed precision. Transformed calculations change only the exact coordinate mapping (log electron-energy coordinate and analytic azimuthal mirror integration); physical assumptions, cuts, photon losses, and attempt/adaptation budgets are unchanged. Original files remain preserved.','',
    'Folded samples intentionally retain one representative per azimuthal mirror pair and integrate both halves analytically. Their positive photon-py fraction of one is expected and is not a support failure. Signed azimuths must be restored before classifier use.','',
    '## Same-seed comparisons','',
    '| Mass (GeV) | Seed | Original outside rate (pb) | Transformed rate (pb) | Three-new-seed mean (pb) | Rate recovery factor |',
    '|---|---:|---:|---:|---:|---:|']
for p in pairs:
    md.append(f"| {p['mass_GeV']:g} | {p['seed']} | {p['original_sigma_pb']:.8f} | {p['transformed_sigma_pb']:.8f} | {p['independent_mean_sigma_pb']:.8f} | {p['transformed_over_original']:.3f} |")
md+=['','At 1.585 GeV the original calculation misses one mirror half: invariant electron-energy and t shapes can look correct while the normalization is about half. At 2.512 and 6.31 GeV the invariant shapes also change substantially.','',
     '## Low-electron-energy coverage','',
     '| Mass (GeV) | Seed | Original fraction E_e < 2 GeV | Transformed fraction | Three-new-seed mean fraction | Original mean eta_e | Transformed mean eta_e |',
     '|---|---:|---:|---:|---:|---:|---:|']
for p in pairs:
    md.append(f"| {p['mass_GeV']:g} | {p['seed']} | {100*p['original_electron_energy_lt2_fraction']:.2f}% | {100*p['transformed_electron_energy_lt2_fraction']:.2f}% | {100*p['independent_electron_energy_lt2_fraction']:.2f}% | {p['original_electron_eta_mean']:.3f} | {p['transformed_electron_eta_mean']:.3f} |")
md+=['','## Independent-seed repeatability','',
     '| Mass (GeV) | Mean outside rate (pb) | Across-seed SD (pb) | SD / mean | Typical quoted per-seed error (pb) |',
     '|---|---:|---:|---:|---:|']
for g in groups:
    if g['route']!='independent_lab':continue
    rs=[r for r in rows if r['route']=='independent_lab' and r['mass_GeV']==g['mass_GeV']]
    md.append(f"| {g['mass_GeV']:g} | {g['mean_rate_pb']:.8f} | {g['seed_sd_pb']:.8f} | {100*g['seed_sd_pb']/g['mean_rate_pb']:.3f}% | {st.mean(r['sigma_error_pb'] for r in rs):.8f} |")
md+=['','The rate and invariant-shape recovery is repeatable across these three independently chosen transformed seeds and is consistent with the transformed replays. Three seeds are a bounded pilot, not a comprehensive convergence proof. The rate-only folded ROOT outputs have not replaced any training/validation/test inputs or final classifier results.','',
     'Checks: zero loss-probability mismatches; reconstructed event sums recover all stored cross sections within relative 1e-10; event-weight sampling errors reproduce stored TFoam errors within relative 1e-9. These errors are proposal-conditioned and did not detect the original missed support.','',
     'Files: `support_diagnostics.jsonl` has all diagnostic records; `support_summary.csv` has one row per ROOT; `support_pairs.csv` has the six same-seed comparisons; `support_group_summary.csv` summarizes routes and independent scatter.']
(BASE/'support_summary.md').write_text('\n'.join(md)+'\n')
print('\n'.join(md))
