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
    for extension in ['pdf', 'png']:
        fig.savefig(OUTPUT / ('figure.' + extension), bbox_inches='tight', dpi=200)
    plt.close(fig)


OUTPUT = output_directory()

plt.rcParams.update({'font.size': 11, 'axes.labelsize': 12, 'axes.titlesize': 13,
                     'legend.fontsize': 9, 'pdf.fonttype': 42, 'ps.fonttype': 42})
data = rows(HERE / 'data/comparisons.csv')
fig, axes = plt.subplots(2, 2, figsize=(11.3, 7.1), sharex=True, layout='constrained')
for row, feature in enumerate(['electron', 'electron_qa2']):
    for col, typ in enumerate(['vector', 'scalar']):
        ax = axes[row, col]
        for comp, label, color in [('bdt_over_cuts', 'BDT / cuts', '#2878b5'),
                                   ('likelihood_over_cuts', 'Likelihood / cuts', '#df7926'),
                                   ('bdt_over_likelihood', 'BDT / likelihood', '#555555')]:
            selected = sorted([r for r in data if r['kind'] == 'method' and
                               r['feature_set'] == feature and r['signal_type'] == typ
                               and r['comparison'] == comp], key=lambda r: float(r['mass_GeV']))
            x = np.array([float(r['mass_GeV']) for r in selected])
            y, lo, hi = np.array([[float(r[k]) for k in ['advantage_pct', 'ci95_low_advantage_pct', 'ci95_high_advantage_pct']]
                                 for r in selected]).T
            ax.vlines(x, lo, hi, color=color, linewidth=1)
            ax.plot(x, y, 'o-', ms=3.2, lw=1.3, color=color, label=label)
        ax.axhline(0., color='gray', lw=.8)
        ax.set(xscale='log', title=typ.title() + (': electron only' if not row else r': electron + $t$'))
        if col == 0:
            ax.set_ylabel('Significance advantage (%)')
        if row:
            ax.set_xlabel('Boson mass (GeV)')
        ax.grid(alpha=.15)
        ax.legend(frameon=False, fontsize=8.3)
save(fig)
