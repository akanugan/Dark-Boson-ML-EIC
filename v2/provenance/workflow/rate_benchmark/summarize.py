#!/usr/bin/env python3
"""Summarize every successful integral and preserve failed-support diagnostics."""

import csv
import json
import math
import statistics
from pathlib import Path

BASE = Path(__file__).resolve().parent


def write_csv(path, data):
    if not data:
        return
    with path.open('w', newline='') as handle:
        writer = csv.DictWriter(handle, fieldnames=list(data[0]))
        writer.writeheader()
        writer.writerows(data)


def main():
    rows = []
    for stage, directory in [('initial', 'runs'), ('transformed', 'runs_transformed'),
                             ('focused', 'runs_focused'), ('stability', 'runs_stability'),
                             ('mixture', 'runs_mixture')]:
        for path in sorted((BASE / directory).glob('*/*/rep_*/result.json')):
            row = json.loads(path.read_text())
            row['stage'] = stage
            rows.append(row)
    summary = []
    for stage, mass, route in sorted({(r['stage'], r['mass_GeV'], r['route']) for r in rows}):
        data = [r for r in rows if (r['stage'], r['mass_GeV'], r['route']) == (stage, mass, route)]
        central = route.startswith('central')
        factor = 1e-6 if central else 1
        values = [factor*r['sigma_pb'] for r in data]
        errors = [factor*r['sigma_error_pb'] for r in data]
        mean = statistics.mean(values)
        sd = statistics.stdev(values) if len(values)>1 else math.nan
        rms = math.sqrt(statistics.mean(v*v for v in errors))
        summary.append(dict(
            stage=stage, mass_GeV=mass, route=route, successful_replicas=len(data),
            mean_effective_pb=mean, seed_sd_pb=sd, seed_sd_pct=100*sd/mean,
            rms_reported_error_pb=rms, scatter_over_reported_error=sd/rms,
            min_effective_pb=min(values), max_effective_pb=max(values),
            sem_from_seeds_pb=sd/math.sqrt(len(values)),
            error_scope='Conditional integration errors and empirical seed scatter; not physical-model uncertainty',
            support_status=('documented_incomplete_support' if
                route.startswith('effective_cm') or
                (route.startswith('outside_cm') and 'iid' not in route)
                else 'inspect_independent_numerical_checks'),
        ))
    write_csv(BASE/'route_summary.csv', summary)
    write_csv(BASE/'all_integrations.csv', rows)
    combined = []
    for stage, mass in sorted({(r['stage'], r['mass_GeV']) for r in rows}):
        suffixes = {'initial':[''], 'transformed':['_logfold'],
                    'focused':['_focused'], 'stability':['_large','_regulator'],
                    'mixture':[]}[stage]
        for suffix in suffixes:
            central_name='central_cm'+suffix
            central=next((r for r in summary if r['stage']==stage and r['mass_GeV']==mass and r['route']==central_name),None)
            if central is None or central['successful_replicas']!=3:
                continue
            outside_name='outside_lab'+suffix
            outside = next((r for r in summary if r['stage']==stage and r['mass_GeV']==mass and r['route']==outside_name),None)
            if outside is None or outside['successful_replicas']!=3:
                continue
            total = central['mean_effective_pb']+outside['mean_effective_pb']
            error = math.hypot(central['sem_from_seeds_pb'],outside['sem_from_seeds_pb'])
            combined.append(dict(stage=stage,mass_GeV=mass,
                route=central_name+' + '+outside_name,mean_effective_pb=total,
                seed_based_sem_pb=error,
                scope='Three independent seeds per component; inspect numerical stability and support diagnostics before accepting as final; known failed CM outside estimates are excluded from this sum'))
    write_csv(BASE/'component_sums.csv',combined)
    report = ['# Photon-rate integration benchmark','',
        'All physics and selections are fixed. Coordinate changes and budgets are recorded in the protocols.',
        'The tables preserve finite estimates, including documented support failures; NaN adaptations remain in status files and logs.',
        'A completed process and a small internal error do not by themselves establish convergence.','',
        '| Stage | Cut mass | Route | Finite seeds | Mean effective pb | Seed SD % | Support status |',
        '|---|---:|---|---:|---:|---:|---|']
    for r in summary:
        report.append(f"| {r['stage']} | {r['mass_GeV']:g} | {r['route']} | {r['successful_replicas']} | {r['mean_effective_pb']:.9g} | {r['seed_sd_pct']:.3g} | {r['support_status']} |")
    report += ['', 'Central rows include the photon-loss factor of 1e-6; outside rows have factor 1.',
        'Effective rows integrate the loss-weighted density directly. Folded-azimuth files integrate both mirrors analytically.',
        '', '| Stage | Cut mass | Component sum | Effective pb | Seed-based SEM pb |',
        '|---|---:|---|---:|---:|']
    for r in combined:
        report.append(f"| {r['stage']} | {r['mass_GeV']:g} | {r['route']} | {r['mean_effective_pb']:.9g} | {r['seed_based_sem_pb']:.3g} |")
    report += ['', 'Sources and binaries are hashed in environment.json and transformed_environment.json.',
        'Historical targets for exact reproduction: .032 GeV 2.2706536 pb; 10 GeV .33266971 pb.',
        'Current rounded reference Table I: .032 GeV 2.06 pb; 10 GeV .33 pb.',
        'https://arxiv.org/html/2505.08871v4#S3', '',
        'Any claim of physical accuracy must additionally address model assumptions and the residual reference discrepancy.',
        'This benchmark does not change existing classifier samples, models, calibration rates or manuscript files.', '']
    (BASE/'summary.md').write_text('\n'.join(report))
    print('\n'.join(report))


if __name__=='__main__':
    main()
