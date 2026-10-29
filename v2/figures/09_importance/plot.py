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
importance_rows = rows(HERE / 'data/importance.csv')
for row in importance_rows:
    row['importance'] = float(row['importance'])
order = ['log10(QA2)', 'log10(Qe2)', 'electron_pt', 'electron_energy', 'electron_eta']
labels = [r'$\log_{10}t$', r'$\log_{10}Q^2$', r'$p_{T,e}$', r'$E_e$', r'$\eta_e$']
fig, ax = plt.subplots(figsize=(8.3, 4.5))
summary = []
for shift, typ, color in [(-.12, 'vector', '#1b9e77'), (.12, 'scalar', '#7570b3')]:
    means, errors = [], []
    for index, variable in enumerate(order):
        values = np.array([r['importance'] for r in importance_rows if r['boson'] == typ and r['variable'] == variable])
        assert len(values) == 10
        mean, sd = values.mean(), values.std(ddof=1)
        summary.append(dict(boson=typ, variable=variable, mean_importance=mean, sample_std=sd, runs=10))
        means.append(100 * mean)
        errors.append(100 * sd)
        ax.scatter(index + shift + np.linspace(-.04, .04, 10), 100 * values, s=15, color=color, alpha=.55)
    ax.errorbar(np.arange(5) + shift, means, yerr=errors, fmt='o', color=color,
                markersize=6, lw=1.6, capsize=4, label=typ.title())
ax.set_xticks(np.arange(5), labels)
ax.set(ylabel='Normalized TMVA importance (%)', title=r'Selected BDT models, electron + $t$, 10 GeV')
ax.grid(axis='y', alpha=.18)
ax.legend(frameon=False)
fig.tight_layout()
save(fig)
