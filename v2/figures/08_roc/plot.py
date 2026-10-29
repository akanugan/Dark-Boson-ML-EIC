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


import gzip
import math

OUTPUT = output_directory()

plt.rcParams.update({'font.size': 11, 'axes.labelsize': 12, 'axes.titlesize': 13,
                     'legend.fontsize': 9, 'pdf.fonttype': 42, 'ps.fonttype': 42})

curves = {}
with gzip.open(HERE / 'data/roc_curves.csv.gz', 'rt', newline='') as stream:
    for row in csv.DictReader(stream):
        key = (row['boson'], row['feature_set'], row['method'])
        curves.setdefault(key, ([], []))
        curves[key][0].append(float(row['photon_efficiency']))
        curves[key][1].append(float(row['signal_efficiency']))
aucs = {(r['boson'], r['feature_set'], r['method']): float(r['auc'])
        for r in rows(HERE / 'data/roc_auc.csv')}
cuts = {(r['boson'], r['feature_set']): r for r in rows(HERE / 'data/roc_cuts.csv')}
if len(curves) != 8 or len(aucs) != 8 or len(cuts) != 4:
    raise ValueError('Expected all eight ROC curves and four cut operating points')
fig, axes = plt.subplots(1, 2, figsize=(11.2, 4.8), sharex=True, sharey=True)
for ax, typ in zip(axes, ['vector', 'scalar']):
    for feature, color in [('electron', '#252525'), ('electron_qa2', '#2166ac')]:
        feature_label = 'Electron' if feature == 'electron' else r'Electron + $t$'
        for method in ['bdt', 'likelihood']:
            key = (typ, feature, method)
            x, y = map(np.asarray, curves[key])
            if np.any(np.diff(x) < 0) or np.any(np.diff(y) < 0):
                raise ValueError('ROC curve is not monotonic')
            auc = aucs[key]
            measured = float(np.trapezoid(y, x))
            if not math.isclose(measured, auc, rel_tol=2e-13, abs_tol=2e-13):
                raise ValueError('Stored AUC disagrees with the full ROC vertices')
            label = 'BDT' if method == 'bdt' else 'Likelihood'
            ax.plot(x, y, color=color, ls='-' if method == 'bdt' else '--', lw=1.8,
                    label=f'{feature_label}: {label} ({auc:.3f})')
        cut = cuts[(typ, feature)]
        es, ep = float(cut['signal_efficiency']), float(cut['photon_efficiency'])
        ax.scatter(ep, es, color=color, s=56, edgecolor='white', lw=.8, zorder=5,
                   label=feature_label + ': cuts')
    ax.set(title=typ.title() + ' boson, 10 GeV', xlabel=r'Photon efficiency $\epsilon_\gamma$',
           xlim=(0, 1), ylim=(0, 1))
    ax.grid(alpha=.18)
    ax.legend(loc='lower right', frameon=False)
axes[0].set_ylabel(r'Signal efficiency $\epsilon_S$')
fig.tight_layout()
save(fig)
