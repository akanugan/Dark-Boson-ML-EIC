#!/usr/bin/env python3
"""Plot selection summaries without reading event files."""
import os
os.environ['MPLCONFIGDIR'] = '/tmp/dark-mpl-cache'
import argparse
import csv
import json
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

METHODS = [('bdt', 'BDT', '#2878b5'), ('likelihood', 'Likelihood', '#df7926'),
           ('cuts', 'Cuts', '#1b9e77')]
TYPES = ('vector', 'scalar')
FEATURES = ('electron', 'electron_qa2')
REQUIRED = ('signal_type', 'mass_GeV', 'kind', 'feature_set', 'method',
            'comparison', 'advantage_pct', 'ci95_low_advantage_pct',
            'ci95_high_advantage_pct', 'nonzero_gain_resolved', 'target_10pct_met')


def values(row):
    return tuple(float(row[name]) for name in
                 ('advantage_pct', 'ci95_low_advantage_pct', 'ci95_high_advantage_pct'))


def rows(path):
    with path.open(newline='') as file:
        reader = csv.DictReader(file)
        missing = set(REQUIRED) - set(reader.fieldnames or ())
        if missing:
            raise ValueError(f'Missing summary columns in {path}: {sorted(missing)}')
        result = list(reader)
    if not result:
        raise ValueError('Empty summary: ' + str(path))
    keys = set()
    for row in result:
        key = (row['signal_type'], float(row['mass_GeV']), row['kind'],
               row['feature_set'], row['method'], row['comparison'])
        if key in keys:
            raise ValueError('Duplicate summary contrast: ' + str(key))
        keys.add(key)
        if row['signal_type'] not in TYPES or key[1] <= 0:
            raise ValueError('Unexpected signal type or mass in ' + str(path))
        y, lo, hi = values(row)
        if not np.all(np.isfinite([y, lo, hi])) or lo > hi:
            raise ValueError('Invalid plotted estimate or interval in ' + str(path))
    # Exact kind/feature/method names come from analyze.py.
    expected = {('direct_t', 'both', method, method + '_t_over_electron')
                for method, _, _ in METHODS}
    expected |= {('method', feature, 'comparison', comparison)
                 for feature in FEATURES
                 for comparison in ('bdt_over_cuts', 'likelihood_over_cuts',
                                    'bdt_over_likelihood')}
    groups = {(key[0], key[1]) for key in keys}
    for typ, mass in groups:
        actual = {key[2:] for key in keys if key[:2] == (typ, mass)}
        if actual != expected:
            raise ValueError(f'Incomplete/unexpected contrast set for {typ}, {mass}: {path}')
    return result


def save(fig, path):
    for suffix in ('.png', '.pdf'):
        fig.savefig(path.with_suffix(suffix), dpi=180)
    plt.close(fig)
    return str(path.with_suffix('.png'))


def estimates(ax, x, selected, label, color, line=True):
    if not selected:
        raise ValueError('Missing plotted contrast for ' + label)
    y, lo, hi = np.array([values(row) for row in selected]).T
    # Percentile intervals need not contain their point estimate. Draw their
    # actual endpoints instead of clipping negative error lengths to zero.
    midpoint = (lo + hi) / 2
    ax.errorbar(x, midpoint, yerr=[midpoint - lo, hi - midpoint],
                fmt='none', capsize=2, color=color, lw=1)
    ax.plot(x, y, 'o-' if line else 'o', ms=4, label=label, color=color)


def select(data, typ, kind, *, method=None, feature=None, comparison=None):
    return sorted([row for row in data if row['signal_type'] == typ and
                   row['kind'] == kind and
                   (method is None or row['method'] == method) and
                   (feature is None or row['feature_set'] == feature) and
                   (comparison is None or row['comparison'] == comparison)],
                  key=lambda row: float(row['mass_GeV']))


def context(out, data):
    gate_path, status_path = out / 'fit_protocol_gate.json', out / 'analysis_status.json'
    gate = json.loads(gate_path.read_text()) if gate_path.exists() else {}
    status = json.loads(status_path.read_text()) if status_path.exists() else {}
    fraction = float(gate.get('t_smearing_fraction', 0))
    groups = len({(row['signal_type'], row['mass_GeV']) for row in data})
    expected = int(status.get('expected_groups', gate.get('expected_groups', groups)))
    if status.get('state') == 'complete' and groups != expected:
        raise ValueError(f'Completed status expects {expected} groups, summary contains {groups}')
    suffix = (f'\nAssumed {100 * fraction:g}% Gaussian t resolution; fixed nominal selections'
              if fraction else '')
    if groups != expected:
        suffix += f'\nPartial: {groups}/{expected} boson/mass groups'
    return fraction, groups, expected, suffix


def nominal_plots(out, data, suffix):
    figures = out / 'figures'
    figures.mkdir(exist_ok=True)
    generated = []
    masses = sorted({float(row['mass_GeV']) for row in data})
    single = len(masses) == 1
    fig, axes = plt.subplots(1, 2, figsize=(11, 4.3), layout='constrained')
    for ax, typ in zip(axes, TYPES):
        for index, (method, label, color) in enumerate(METHODS):
            selected = select(data, typ, 'direct_t', method=method)
            x = [index] if single else [float(row['mass_GeV']) for row in selected]
            estimates(ax, x, selected, label, color, line=not single)
        ax.axhline(0, color='gray', lw=1)
        title = typ.capitalize() + (f', {masses[0]:g} GeV' if single else '')
        ax.set(ylabel='Significance gain from adding t (%)', title=title)
        if single:
            ax.set_xticks(range(3), [label for _, label, _ in METHODS])
            ax.set_xlim(-.4, 2.4)
        else:
            ax.set(xscale='log', xlabel='Boson mass (GeV)')
            ax.legend()
        ax.grid(alpha=.15)
    fig.suptitle('Benefit of t; paired pointwise 95% intervals' + suffix, fontsize=10)
    generated.append(save(fig, figures / 't_information_gain'))
    for feature, title in [('electron', 'Electron only'), ('electron_qa2', 'Electron plus t')]:
        fig, axes = plt.subplots(1, 2, figsize=(11, 4.3), layout='constrained')
        for ax, typ in zip(axes, TYPES):
            for index, (method, label, color) in enumerate(METHODS[:2]):
                selected = select(data, typ, 'method', feature=feature,
                                  comparison=method + '_over_cuts')
                x = [index] if single else [float(row['mass_GeV']) for row in selected]
                estimates(ax, x, selected, label, color, line=not single)
            ax.axhline(0, color='gray', lw=1)
            ax.set(ylabel='Significance advantage over cuts (%)',
                   title=typ.capitalize() + (f', {masses[0]:g} GeV' if single else ''))
            if single:
                ax.set_xticks(range(2), [label for _, label, _ in METHODS[:2]])
                ax.set_xlim(-.4, 1.4)
            else:
                ax.set(xscale='log', xlabel='Boson mass (GeV)')
                ax.legend()
            ax.grid(alpha=.15)
        fig.suptitle(title + '; paired pointwise 95% intervals' + suffix, fontsize=10)
        generated.append(save(fig, figures / f'method_comparison_{feature}'))
    return generated


def six_selection_plot(out, data):
    """All three methods, with/without t, relative to one common preselection."""
    from matplotlib.lines import Line2D
    figures = out / 'figures'
    figures.mkdir(exist_ok=True)
    fig, axes = plt.subplots(1, 2, figsize=(12, 5.3), sharey=True)
    fig.subplots_adjust(left=.085, right=.99, bottom=.14, top=.76, wspace=.08)
    methods = [('cuts', 'Rectangular cuts', '#1b9e77', '^'),
               ('likelihood', 'Likelihood', '#df7926', 's'),
               ('bdt', 'BDT', '#2878b5', 'o')]
    expected = {(typ, float(row['mass_GeV']), feature, method)
                for typ in TYPES for row in data for feature in FEATURES for method, *_ in methods}
    actual = {(r['signal_type'], float(r['mass_GeV']), r['feature_set'], r['method']) for r in data}
    if len(actual) != len(data) or actual != expected:
        raise ValueError('Missing or duplicated six-selection plot values')
    ymax = 1.
    ymin = 1.
    for ax, typ in zip(axes, TYPES):
        for method, label, color, marker in methods:
            for feature, style in [('electron', '--'), ('electron_qa2', '-')]:
                selected = sorted([r for r in data if r['signal_type'] == typ and
                                   r['method'] == method and r['feature_set'] == feature],
                                  key=lambda r: float(r['mass_GeV']))
                x = np.array([float(r['mass_GeV']) for r in selected])
                y = np.array([float(r['geometric_mean_RZ']) for r in selected])
                lo = np.array([float(r['ci95_low_RZ']) for r in selected])
                hi = np.array([float(r['ci95_high_RZ']) for r in selected])
                if not np.all(np.isfinite([y, lo, hi])) or np.any(lo > hi):
                    raise ValueError('Invalid common-baseline interval')
                ax.fill_between(x, lo, hi, color=color, alpha=.075, linewidth=0)
                ax.plot(x, y, linestyle=style, color=color, marker=marker,
                        markersize=4, linewidth=1.7,
                        markerfacecolor=color if feature == 'electron_qa2' else 'white',
                        markeredgewidth=1)
                ymin, ymax = min(ymin, float(lo.min())), max(ymax, float(hi.max()))
        ax.axhline(1, color='#777777', linestyle=':', linewidth=1)
        ax.set(xscale='log', xlabel='Boson mass (GeV)', title=typ.capitalize())
        ax.tick_params(labelsize=11)
        ax.xaxis.label.set_size(12)
        ax.title.set_size(13)
        ax.grid(alpha=.16)
    margin = .06 * (ymax - ymin)
    axes[0].set_ylim(ymin - margin, ymax + margin)
    axes[0].set_ylabel('Signal significance relative\nto preselection', fontsize=12)
    handles = [Line2D([], [], color=color, marker=marker, linewidth=1.7, label=label)
               for method, label, color, marker in methods]
    handles += [Line2D([], [], color='#333333', linestyle='--', label='Electron only'),
                Line2D([], [], color='#333333', linestyle='-', label=r'Electron + $t$')]
    fig.legend(handles=handles, loc='upper center', bbox_to_anchor=(.5, .91),
               ncol=5, frameon=False, fontsize=10.5, handlelength=2.4, columnspacing=1.5)
    fig.suptitle('Three selections, with and without t', y=.985, fontsize=14)
    fig.text(.5, .81, 'Common preselection within each mass; pointwise 95% intervals',
             ha='center', fontsize=10)
    return save(fig, figures / 'selection_comparison')


def smearing_overlay(out, nominal):
    """Combine nominal, 10%, and 20% summaries without reading event files."""
    prefix = out / 'figures/t_smearing_10gev'
    paths = [out / 'smearing' / label / 'summary.csv' for label in ('10pct', '20pct')]
    if not all(path.exists() for path in paths):
        for suffix in ('.png', '.pdf'):
            prefix.with_suffix(suffix).unlink(missing_ok=True)
        return []
    datasets = [nominal] + [rows(path) for path in paths]
    for path, expected_fraction, data in zip(paths, (.1, .2), datasets[1:]):
        fraction, groups, expected, _ = context(path.parent, data)
        if fraction != expected_fraction or groups != 2 or expected != 2 or \
                {float(row['mass_GeV']) for row in data} != {10.0}:
            raise ValueError('Unexpected smearing summary scope: ' + str(path))
    fig, axes = plt.subplots(2, 2, figsize=(11, 7.5), layout='constrained', sharex=True)
    for column, typ in enumerate(TYPES):
        for method, label, color in METHODS:
            selected = []
            for data in datasets:
                matches = [row for row in select(data, typ, 'direct_t', method=method)
                           if float(row['mass_GeV']) == 10]
                if len(matches) != 1:
                    raise ValueError('Missing nominal/smeared 10 GeV direct-t contrast')
                selected.append(matches[0])
            estimates(axes[0, column], [0, 10, 20], selected, label, color)
        for method, label, color in METHODS[:2]:
            selected = []
            for data in datasets:
                matches = [row for row in select(data, typ, 'method', feature='electron_qa2',
                                                 comparison=method + '_over_cuts')
                           if float(row['mass_GeV']) == 10]
                if len(matches) != 1:
                    raise ValueError('Missing nominal/smeared 10 GeV method contrast')
                selected.append(matches[0])
            estimates(axes[1, column], [0, 10, 20], selected, label, color)
        axes[0, column].set(title=typ.capitalize() + ', 10 GeV',
                            ylabel='Significance gain from adding t (%)')
        axes[1, column].set(ylabel='Significance advantage over cuts (%)',
                            xlabel=r'Assumed fractional t resolution $\sigma_t/t$ (%)')
        for ax in axes[:, column]:
            ax.axhline(0, color='gray', lw=1)
            ax.set_xticks([0, 10, 20])
            ax.grid(alpha=.15)
            ax.legend()
    fig.suptitle('Gaussian t-smearing benchmark; fixed nominal selections\n'
                 'Paired pointwise 95% intervals; assumed response, not detector calibration', fontsize=11)
    return [save(fig, prefix)]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--results', type=Path, required=True)
    out = parser.parse_args().results
    data = rows(out / 'summary.csv')
    fraction, groups, expected, suffix = context(out, data)
    generated = []
    absolute = out / 'selection_results.csv'
    if absolute.exists():
        with absolute.open(newline='') as stream:
            generated.append(six_selection_plot(out, list(csv.DictReader(stream))))
    generated += nominal_plots(out, data, suffix)
    if fraction == 0:
        generated += smearing_overlay(out, data)
    flags = [row for row in data if row['nonzero_gain_resolved'] == 'True' and
             row['target_10pct_met'] != 'True']
    followup = out / 'precision_followup.csv'
    if flags:
        with followup.open('w', newline='') as file:
            writer = csv.DictWriter(file, fieldnames=list(flags[0]))
            writer.writeheader()
            writer.writerows(flags)
    else:
        followup.unlink(missing_ok=True)
    summary = dict(summary_rows=len(data), complete_groups=groups,
                   expected_groups=expected, t_smearing_fraction=fraction,
                   resolved_gains_missing_relative_precision_target=len(flags),
                   figures=generated,
                   interpretation='Intervals are pointwise; inspect family95 columns before making multiple-comparison claims. '
                                  'Numerical precision and photon-response variation are distinct. '
                                  'Smearing applies to fixed nominal selections and assumes a response, not a detector calibration.')
    (out / 'plot_status.json').write_text(json.dumps(summary, indent=2) + '\n')
    print(json.dumps(summary, indent=2))


if __name__ == '__main__':
    main()
