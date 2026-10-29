#!/usr/bin/env python3
"""Reproduce this figure from its accompanying numerical data."""
import argparse
import csv
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

HERE = Path(__file__).resolve().parent


def rows(path):
    with path.open(newline='') as stream:
        return list(csv.DictReader(stream))


def output_directory():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output-dir', type=Path, default=HERE / 'generated')
    out = parser.parse_args().output_dir
    out.mkdir(parents=True, exist_ok=True)
    return out


def save(fig):
    for suffix in ('.png', '.pdf'):
        fig.savefig(OUTPUT / ('figure' + suffix), dpi=180)
    plt.close(fig)

TYPES = ('vector', 'scalar')
FEATURES = ('electron', 'electron_qa2')

def plot(data):
    """All three methods, with/without t, relative to one common preselection."""
    from matplotlib.lines import Line2D
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
    save(fig)

if __name__ == '__main__':
    OUTPUT = output_directory()
    plot(rows(HERE / 'data/selections.csv'))
