#!/usr/bin/env python3
"""Regenerate historical pre-stratification 10 GeV diagnostic figures.

This is not the current revised figure entry point. No event generation,
fitting, or model selection is performed. ROC curves use
rep_001's validation-selected models. Importance uses the selected t-inclusive
model in each of the ten independent runs and the original TMVA training log.
"""
import concurrent.futures as cf
import csv
import gzip
import json
import math
import re
import subprocess
from pathlib import Path
import xml.etree.ElementTree as ET

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np

BASE = Path(__file__).resolve().parents[1]
OUT = BASE / 'manuscript_assets'
SCORES = OUT / 'diagnostic_scores'


def rows(path):
    with path.open() as stream:
        return list(csv.DictReader(stream))


def write(path, values):
    with path.open('w') as stream:
        writer = csv.DictWriter(stream, fieldnames=list(values[0]))
        writer.writeheader()
        writer.writerows(values)


def model_xml(selection, method):
    configuration = rows(selection / f'{method}_selected.csv')[0]
    tag = 'BDTG' if method == 'bdt' else 'PDERS'
    path = selection / method / configuration['model_profile'] / 'dataset/weights' / f'TMVAClassification_{tag}.weights.xml'
    payload = path.read_bytes() if path.exists() else gzip.decompress(path.with_suffix('.xml.gz').read_bytes())
    return configuration, payload


def export(boson, features, method):
    source = BASE / 'results/rep_001' / f'{boson}_m10p000'
    selection = source / features
    configuration, payload = model_xml(selection, method)
    if features == 'electron_qa2':
        prefix = BASE / 'photon_shape_test/rep_001' / boson / method
        if all(Path(f'{prefix}_{kind}.csv').exists() for kind in ['signal', 'photon']):
            return boson, features, method, prefix
    prefix = SCORES / f'{boson}_{features}_{method}'
    local = prefix.with_suffix('.xml')
    local.write_bytes(payload)
    command = [BASE / 'bin/export_shape_scores', source / 'data/signal_test.root', source / 'data/photon_test.root', local,
               selection / f'{method}_selected.csv', selection / 'cuts_selected.csv', prefix, features,
               configuration['photon_xs_pb'], configuration['dis_xs_pb']]
    with prefix.with_suffix('.log').open('w') as stream:
        subprocess.run(list(map(str, command)), stdout=stream, stderr=subprocess.STDOUT, check=True)
    local.unlink()
    return boson, features, method, prefix


def roc(signal, photon):
    score = np.r_[signal['score'], photon['score']]
    order = np.argsort(-score, kind='stable')
    sw = np.r_[signal['weight'], np.zeros(len(photon))][order]
    bw = np.r_[np.zeros(len(signal)), photon['weight']][order]
    ss, bs = np.cumsum(sw), np.cumsum(bw)
    unique_end = np.r_[np.flatnonzero(np.diff(score[order]) != 0), len(score) - 1]
    x = np.r_[0.0, bs[unique_end] / bs[-1]]
    y = np.r_[0.0, ss[unique_end] / ss[-1]]
    return x, y, float(np.trapezoid(y, x))


def main():
    OUT.mkdir(exist_ok=True)
    SCORES.mkdir(exist_ok=True)
    plt.rcParams.update({'font.size': 11, 'axes.labelsize': 12, 'axes.titlesize': 13, 'legend.fontsize': 9,
                         'savefig.dpi': 220, 'pdf.fonttype': 42, 'ps.fonttype': 42})
    with cf.ThreadPoolExecutor(max_workers=4) as pool:
        futures = [pool.submit(export, boson, feature, method) for boson in ['vector', 'scalar']
                   for feature in ['electron', 'electron_qa2'] for method in ['bdt', 'likelihood']]
        exports = [future.result() for future in futures]
    datasets = {(boson, feature, method): [np.genfromtxt(Path(f'{prefix}_{kind}.csv'), delimiter=',', names=True)
                 for kind in ['signal', 'photon']] for boson, feature, method, prefix in exports}
    fig, axes = plt.subplots(1, 2, figsize=(11.2, 4.8), sharex=True, sharey=True)
    auc_rows, curve_rows, operating_rows = [], [], []
    colors = {'electron': '#252525', 'electron_qa2': '#2166ac'}
    for axis, boson in zip(axes, ['vector', 'scalar']):
        for feature in ['electron', 'electron_qa2']:
            feature_label = 'Electron' if feature == 'electron' else r'Electron + $t$'
            for method in ['bdt', 'likelihood']:
                signal, photon = datasets[boson, feature, method]
                x, y, auc = roc(signal, photon)
                method_label = 'BDT' if method == 'bdt' else 'Likelihood'
                axis.plot(x, y, color=colors[feature], ls='-' if method == 'bdt' else '--', lw=1.8,
                          label=f'{feature_label}: {method_label} ({auc:.3f})')
                auc_rows.append(dict(boson=boson, mass_GeV=10, rep=1, feature_set=feature, method=method, weighted_auc=auc))
                for cx, cy in zip(x, y):
                    curve_rows.append(dict(boson=boson, feature_set=feature, method=method, photon_efficiency=cx, signal_efficiency=cy))
                original = rows(BASE / 'results/rep_001' / f'{boson}_m10p000' / feature / f'{method}_test.csv')[0]
                for events, key in [(signal, 'bdt_signal_efficiency'), (photon, 'bdt_photon_efficiency')]:
                    efficiency = float(np.sum(events['weight'] * events['model_pass']) / np.sum(events['weight']))
                    if not math.isclose(efficiency, float(original[key]), rel_tol=1e-9, abs_tol=1e-12):
                        raise RuntimeError(f'Fixed-model export mismatch: {boson} {feature} {method} {key}')
            signal, photon = datasets[boson, feature, 'bdt']
            other_signal, other_photon = datasets[boson, feature, 'likelihood']
            for left, right in [(signal, other_signal), (photon, other_photon)]:
                if not np.array_equal(left['weight'], right['weight']) or not np.array_equal(left['cuts_pass'], right['cuts_pass']):
                    raise RuntimeError('Methods do not share identical events/cuts')
            es = float(np.sum(signal['weight'] * signal['cuts_pass']) / np.sum(signal['weight']))
            ep = float(np.sum(photon['weight'] * photon['cuts_pass']) / np.sum(photon['weight']))
            original = rows(BASE / 'results/rep_001' / f'{boson}_m10p000' / feature / 'bdt_test.csv')[0]
            for value, key in [(es, 'box_signal_efficiency'), (ep, 'box_photon_efficiency')]:
                if not math.isclose(value, float(original[key]), rel_tol=1e-9, abs_tol=1e-12):
                    raise RuntimeError(f'Cut-point mismatch: {boson} {feature} {key}')
            axis.scatter(ep, es, color=colors[feature], s=56, edgecolor='white', linewidth=.8, zorder=5,
                         label=f'{feature_label}: cuts')
            operating_rows.append(dict(boson=boson, mass_GeV=10, rep=1, feature_set=feature, photon_efficiency=ep, signal_efficiency=es,
                                       photon_xs_pb=original.get('photon_xs_pb', rows(BASE / 'results/rep_001' / f'{boson}_m10p000' / feature / 'bdt_selected.csv')[0]['photon_xs_pb'])))
        axis.set_title(f'{boson.title()} boson, 10 GeV')
        axis.set_xlabel(r'Photon efficiency $\epsilon_\gamma$')
        axis.set_xlim(0, 1)
        axis.set_ylim(0, 1)
        axis.grid(alpha=.18)
        axis.legend(loc='lower right', frameon=False)
    axes[0].set_ylabel(r'Signal efficiency $\epsilon_S$')
    fig.tight_layout()
    for extension in ['png', 'pdf']:
        fig.savefig(OUT / f'roc_current.{extension}', bbox_inches='tight')
    plt.close(fig)
    write(OUT / 'roc_auc_current.csv', auc_rows)
    write(OUT / 'roc_curves_current.csv', curve_rows)
    write(OUT / 'roc_cuts_current.csv', operating_rows)

    importance_rows = []
    for boson in ['vector', 'scalar']:
        for rep in range(1, 11):
            selection = BASE / 'results' / f'rep_{rep:03d}' / f'{boson}_m10p000' / 'electron_qa2'
            configuration, payload = model_xml(selection, 'bdt')
            variables = [node.attrib['Expression'] for node in ET.fromstring(payload).find('Variables')]
            text = (selection / 'bdt' / configuration['model_profile'] / 'run.log').read_text()
            text = re.sub(r'\x1b\[[0-9;]*m', '', text).split('Ranking input variables (method specific)...', 1)[1]
            importance = dict((name.strip(), float(value)) for name, value in re.findall(r':\s*\d+\s*:\s*(.*?)\s*:\s*([0-9.]+e[+-]\d+)', text))
            if set(importance) != set(variables) or not math.isclose(sum(importance.values()), 1, abs_tol=.001):
                raise RuntimeError(f'Training-log importance variable mismatch: {boson} {rep}')
            for variable in variables:
                importance_rows.append(dict(boson=boson, mass_GeV=10, rep=rep, model_profile=configuration['model_profile'],
                                            variable=variable, importance=importance[variable],
                                            source=str(selection / 'bdt' / configuration['model_profile'] / 'run.log')))
    write(OUT / 'importance_runs_current.csv', importance_rows)
    variable_order = ['log10(QA2)', 'log10(Qe2)', 'electron_pt', 'electron_energy', 'electron_eta']
    labels = [r'$\log_{10}t$', r'$\log_{10}Q^2$', r'$p_{T,e}$', r'$E_e$', r'$\eta_e$']
    fig, axis = plt.subplots(figsize=(8.3, 4.5))
    summary = []
    for shift, boson, color in [(-.12, 'vector', '#1b9e77'), (.12, 'scalar', '#7570b3')]:
        means, errors = [], []
        for index, variable in enumerate(variable_order):
            values = np.array([row['importance'] for row in importance_rows if row['boson'] == boson and row['variable'] == variable])
            mean, sd = values.mean(), values.std(ddof=1)
            summary.append(dict(boson=boson, variable=variable, mean_importance=mean, sample_std=sd, runs=len(values)))
            means.append(100 * mean)
            errors.append(100 * sd)
            axis.scatter(index + shift + np.linspace(-.04, .04, len(values)), 100 * values, s=15, color=color, alpha=.55)
        axis.errorbar(np.arange(len(variable_order)) + shift, means, yerr=errors, fmt='o', color=color,
                      markersize=6, linewidth=1.6, capsize=4, label=boson.title())
    axis.set_xticks(np.arange(len(variable_order)), labels)
    axis.set_ylabel('Normalized TMVA importance (%)')
    axis.set_title(r'Selected BDT models, electron + $t$, 10 GeV')
    axis.grid(axis='y', alpha=.18)
    axis.legend(frameon=False)
    fig.tight_layout()
    for extension in ['png', 'pdf']:
        fig.savefig(OUT / f'importance_current.{extension}', bbox_inches='tight')
    plt.close(fig)
    write(OUT / 'importance_summary_current.csv', summary)
    (OUT / 'diagnostics_current.json').write_text(json.dumps({
        'roc': 'rep_001 held-out signal and photon events; current validation-selected BDT and PDERS; selected calculated photon rate and fixed DIS rate determine cuts and score thresholds; plotted ROC is photon-only',
        'verification': 'exported model efficiencies and cut points match original held-out evaluations; methods share event weights and cut decisions',
        'importance': 'selected t-inclusive models in all ten 10GeV runs per boson; original TMVA method-specific training-log importance (rounded to original printed precision); variable names verified against selected model XML',
        'importance_extraction_reason': 'TMVA split-gain importance uses training statistics not serialized in model XML; a loaded-reader importance cannot recover those statistics',
        'no_new_training_or_generation': True,
    }, indent=2))
    print(json.dumps({'auc': auc_rows, 'importance': summary}, indent=2))


if __name__ == '__main__':
    main()
