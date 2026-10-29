#!/usr/bin/env python3
"""Compare six selections against their common, mass-specific preselection.

Uses completed test metrics and saved paired bootstrap draws. No fitting,
selection choices, event generation, or existing inference outputs are changed.
"""
import os
for key in ('OPENBLAS_NUM_THREADS', 'OMP_NUM_THREADS', 'VECLIB_MAXIMUM_THREADS'):
    os.environ[key] = '1'

import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
import csv
import hashlib
import json
from pathlib import Path
import time
import numpy as np

FEATURES = ('electron', 'electron_qa2')
METHODS = ('bdt', 'likelihood', 'cuts')
RESAMPLES = 1000000
SEED = 48230000 + 900000
FAMILY_SIZE = 198


def read_csv(path):
    with path.open(newline='') as stream:
        return list(csv.DictReader(stream))


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_csv(path, rows):
    temporary = path.with_suffix(path.suffix + '.tmp')
    with temporary.open('w', newline='') as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    temporary.replace(path)


def aggregate(nominal, bootstrap, seed, resamples=RESAMPLES):
    if nominal.shape != (10, 2, 3) or bootstrap.shape != (10, 2000, 2, 3):
        raise ValueError('Expected ten paired runs, two input sets and three methods')
    if not np.all(np.isfinite(nominal)) or not np.all(nominal > 0):
        raise ValueError('Invalid nominal selection performance')
    if not np.all(np.isfinite(bootstrap)) or not np.all(bootstrap > 0):
        raise ValueError('Invalid paired selection draws')
    point = np.exp(np.log(nominal).mean(axis=0)).reshape(6)
    event_log = np.log(bootstrap).reshape(10, 2000, 6)
    draws = np.empty((resamples, 6))
    rng = np.random.default_rng(seed)
    # Match the locked contrast analysis exactly, including its batch size and
    # alternating run/event random draws. Each draw retains all six selections.
    for begin in range(0, resamples, 2000):
        count = min(2000, resamples - begin)
        run_ids = rng.integers(0, 10, (count, 10))
        event_ids = rng.integers(0, 2000, (count, 10))
        draws[begin:begin + count] = np.exp(event_log[run_ids, event_ids].mean(axis=1))
    return point, draws


def contrast_indices(row):
    if row['kind'] == 'direct_t':
        method = METHODS.index(row['method'])
        return 3 + method, method
    numerator, denominator = row['comparison'].split('_over_')
    offset = 3 * FEATURES.index(row['feature_set'])
    return offset + METHODS.index(numerator), offset + METHODS.index(denominator)


def process_group(index, key, points, contrasts):
    typ, mass = key
    if sorted(rep for rep, _ in points) != list(range(1, 11)):
        raise ValueError('Missing or duplicate independent run: ' + str(key))
    nominal, bootstrap, hashes = [], [], {}
    fixed_rates = None
    for rep, folder in sorted(points):
        metrics = read_csv(folder / 'test_metrics.csv')
        if len(metrics) != 6:
            raise ValueError('Expected six selection metrics: ' + str(folder))
        rate_pairs = {(float(row['photon_xs_pb']), float(row['dis_xs_pb'])) for row in metrics}
        if len(rate_pairs) != 1 or (fixed_rates is not None and rate_pairs != fixed_rates):
            raise ValueError('Selection variants do not share fixed background rates')
        fixed_rates = rate_pairs
        matrix = np.full((2, 3), np.nan)
        for row in metrics:
            fi, mi = FEATURES.index(row['feature_set']), METHODS.index(row['method'])
            if np.isfinite(matrix[fi, mi]):
                raise ValueError('Duplicate selection metric')
            photon, dis = next(iter(rate_pairs))
            calculated = float(row['signal_efficiency']) * np.sqrt(
                (photon + dis) / (photon * float(row['photon_efficiency']) + dis))
            if not np.isclose(calculated, float(row['RZ']), rtol=2e-14, atol=0):
                raise ValueError('Significance does not match selection efficiencies')
            matrix[fi, mi] = float(row['RZ'])
        saved = np.load(folder / 'nominal_RZ.npy', allow_pickle=False)
        if not np.array_equal(matrix, saved):
            raise ValueError('Metric/array disagreement: ' + str(folder))
        nominal.append(saved)
        bootstrap.append(np.load(folder / 'bootstrap_RZ.npy', allow_pickle=False))
        for name in ('nominal_RZ.npy', 'bootstrap_RZ.npy', 'test_metrics.csv'):
            path = folder / name
            hashes[str(path)] = sha(path)
    point, draws = aggregate(np.stack(nominal), np.stack(bootstrap), SEED + index)
    largest_difference = 0.
    for row in contrasts:
        a, b = contrast_indices(row)
        if not np.isclose(point[a] / point[b], float(row['geometric_mean_ratio']), rtol=2e-13, atol=0):
            raise ValueError('Six-selection means disagree with a locked paired contrast')
        ratios = draws[:, a] / draws[:, b]
        for prefix, tail in [('ci95_', .025), ('family95_', .025 / FAMILY_SIZE)]:
            lo, hi = np.quantile(ratios, [tail, 1 - tail])
            for value, label in [(lo, 'low_ratio'), (hi, 'high_ratio')]:
                difference = abs(value - float(row[prefix + label]))
                largest_difference = max(largest_difference, difference)
                if difference > 2e-12:
                    raise ValueError('Paired intervals do not reproduce locked results')
    if len(contrasts) != 9:
        raise ValueError('Expected all nine locked comparisons in each group')
    lower, upper = np.quantile(draws, [.025, .975], axis=0)
    records = []
    for fi, feature in enumerate(FEATURES):
        for mi, method in enumerate(METHODS):
            j = 3 * fi + mi
            records.append(dict(signal_type=typ, mass_GeV=mass, feature_set=feature,
                method=method, geometric_mean_RZ=float(point[j]),
                ci95_low_RZ=float(lower[j]), ci95_high_RZ=float(upper[j]),
                gain_over_preselection_pct=float(100 * (point[j] - 1)),
                independent_runs=10, aggregate_resamples=RESAMPLES,
                interval_scope='pointwise 95%; paired run/event resampling; fixed calibrated rates',
                baseline='same mass-specific preselection for all six variants'))
    return records, dict(signal_type=typ, mass_GeV=mass, checked_runs=10,
                         checked_metrics=60, checked_contrasts=len(contrasts),
                         maximum_interval_difference=largest_difference, sources=hashes)


def self_test():
    nominal = np.arange(1., 7.).reshape(2, 3)
    a = np.tile(nominal, (10, 1, 1))
    b = np.tile(nominal, (10, 2000, 1, 1))
    point, draws = aggregate(a, b, 12, 2000)
    assert np.allclose(point, nominal.ravel(), rtol=1e-14)
    assert np.allclose(draws, point[None], rtol=1e-14)
    assert contrast_indices(dict(kind='direct_t', method='cuts')) == (5, 2)
    assert contrast_indices(dict(kind='method', feature_set='electron_qa2',
                                 comparison='bdt_over_likelihood')) == (3, 4)
    print('Synthetic pairing, common-baseline and contrast-index checks passed.')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--results', type=Path)
    parser.add_argument('--workers', type=int, default=4)
    parser.add_argument('--self-test', action='store_true')
    args = parser.parse_args()
    if args.self_test:
        self_test()
        return
    if args.results is None or not 1 <= args.workers <= 4:
        parser.error('--results and one to four workers are required')
    start = time.time()
    out = args.results.resolve()
    status = json.loads((out / 'analysis_status.json').read_text())
    if status['state'] != 'complete' or status['complete_groups'] != 22:
        raise ValueError('The full completed nominal scan is required')
    summary = read_csv(out / 'summary.csv')
    groups = {}
    for path in sorted((out / 'fits').glob('rep_*/*/analysis/analysis_complete.json')):
        meta = json.loads(path.read_text())
        groups.setdefault((meta['signal_type'], float(meta['mass_GeV'])), []).append((int(meta['rep']), path.parent))
    if len(groups) != 22 or sum(map(len, groups.values())) != 220:
        raise ValueError('Incomplete six-selection comparison')
    records, audits = [], []
    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        futures = []
        for index, (key, points) in enumerate(sorted(groups.items())):
            contrasts = [r for r in summary if (r['signal_type'], float(r['mass_GeV'])) == key]
            futures.append(pool.submit(process_group, index, key, points, contrasts))
        for future in as_completed(futures):
            rows, audit = future.result()
            records.extend(rows)
            audits.append(audit)
            print('Verified', audit['signal_type'], audit['mass_GeV'], flush=True)
    records.sort(key=lambda r: (r['signal_type'], r['mass_GeV'], r['feature_set'], r['method']))
    write_csv(out / 'selection_results.csv', records)
    audit = dict(passed=True, groups=22, points=220, selection_metrics=1320,
                 paired_contrasts=198, output_rows=len(records), seconds=time.time() - start,
                 script_sha256=sha(Path(__file__)), locked_summary_sha256=sha(out / 'summary.csv'),
                 maximum_interval_difference=max(a['maximum_interval_difference'] for a in audits),
                 interpretation='Six selections share a common preselection at each mass. Absolute bands are descriptive pointwise intervals. Use paired contrasts to assess differences.',
                 group_checks=audits)
    (out / 'comparison_audit.json').write_text(json.dumps(audit, indent=2) + '\n')
    from plot_stratified_refit import six_selection_plot
    print('Plot', six_selection_plot(out, records), flush=True)
    print('Six-selection comparison verified in', round(time.time() - start, 1), 'seconds', flush=True)


if __name__ == '__main__':
    main()
