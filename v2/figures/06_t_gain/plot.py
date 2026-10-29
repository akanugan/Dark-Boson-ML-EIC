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

METHODS = [('bdt', 'BDT', '#2878b5'), ('likelihood', 'Likelihood', '#df7926'), ('cuts', 'Cuts', '#1b9e77')]
TYPES = ('vector', 'scalar')

def values(row):
    return tuple(float(row[name]) for name in
                 ('advantage_pct', 'ci95_low_advantage_pct', 'ci95_high_advantage_pct'))

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

def plot(data):
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
    fig.suptitle('Benefit of t; paired pointwise 95% intervals', fontsize=10)
    save(fig)


if __name__ == '__main__':
    OUTPUT = output_directory()
    plot(rows(HERE / 'data/t_gain.csv'))
