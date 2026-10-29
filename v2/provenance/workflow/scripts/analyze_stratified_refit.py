#!/usr/bin/env python3
"""Paired held-out analysis of the stratified photon refit.

This program never fits or selects a model. It refuses to read held-out exports
until fit_protocol_gate.json records passed=true. Each photon stratum is
resampled separately over its original attempted events, including unstored
zero-integrand attempts. The combined resampled shape is normalized to the
independently calibrated, fixed photon rate in sample_config.json.

Array axes are [electron, electron_qa2] x [bdt, likelihood, cuts]. Final group
summaries require all ten independent runs. The declared family comprises 66
within-method t contrasts and 132 within-feature method contrasts (198 total).
"""
import os

# Each worker owns one analysis; do not create additional BLAS worker pools.
os.environ['OPENBLAS_NUM_THREADS'] = '1'
os.environ['VECLIB_MAXIMUM_THREADS'] = '1'
os.environ['OMP_NUM_THREADS'] = '1'

import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
import csv
import gzip
import hashlib
import json
import math
from pathlib import Path
import tempfile
import time

import numpy as np

BASE = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT = BASE / 'stratified_refit'
FEATURES = ('electron', 'electron_qa2')
METHODS = ('bdt', 'likelihood', 'cuts')
FAMILY_SIZE = 198
EPSILONS = np.array([1e-8, 1e-7, 1e-6, 1e-5])
SCENARIO_MODES = ('shape_only', 'rate_and_shape', 'rate_only')
ABSOLUTE_PRECISION_BENCHMARK_PP = .2
EXPECTED_RUNS = tuple(range(1, 11))
MASSES = (.01, .032, .1, .316, 1., 1.585, 2.512, 3.981, 5., 6.31, 10.)
HEADER = ('event_id', 'source_event', 'photon_stratum', 'weight', 'raw_weight',
          'photon_miss_probability', 'logQe2', 'logt', 'raw_logt', 'pt', 'eta', 'energy',
          'score', 'score_half', 'model_pass', 'cuts_pass')
COL = {name: index for index, name in enumerate(HEADER)}
PAIRED_COLUMNS = HEADER[:HEADER.index('energy') + 1]
CONTRASTS = tuple(
    [dict(kind='direct_t', feature_set='both', method=method,
          comparison=method + '_t_over_electron', numerator=3 + index,
          denominator=index) for index, method in enumerate(METHODS)] +
    [dict(kind='method', feature_set=feature, method='comparison',
          comparison=METHODS[a] + '_over_' + METHODS[b],
          numerator=3 * feature_index + a, denominator=3 * feature_index + b)
     for feature_index, feature in enumerate(FEATURES)
     for a, b in ((0, 2), (1, 2), (0, 1))])


def atomic_json(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(mode='w', dir=path.parent, delete=False) as file:
        temporary = Path(file.name)
        json.dump(value, file, indent=2, allow_nan=False)
        file.write('\n')
    os.replace(temporary, path)


def atomic_csv(path, rows):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        raise ValueError('refusing an empty CSV without a defined schema: ' + str(path))
    with tempfile.NamedTemporaryFile(mode='w', dir=path.parent, delete=False, newline='') as file:
        temporary = Path(file.name)
        writer = csv.DictWriter(file, fieldnames=list(rows[0]), lineterminator='\n')
        writer.writeheader()
        writer.writerows(rows)
    os.replace(temporary, path)


def atomic_npy(path, values):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(mode='wb', dir=path.parent, delete=False) as file:
        temporary = Path(file.name)
        np.save(file, values, allow_pickle=False)
    os.replace(temporary, path)


def digest(path):
    hasher = hashlib.sha256()
    with Path(path).open('rb') as file:
        for block in iter(lambda: file.read(1024 * 1024), b''):
            hasher.update(block)
    return hasher.hexdigest()


def gate_check(path):
    if not path.exists():
        raise RuntimeError('held-out analysis blocked: missing fit-protocol gate ' + str(path))
    gate = json.loads(path.read_text())
    if gate.get('passed') is not True:
        raise RuntimeError('held-out analysis blocked: fit-protocol gate has not passed')
    return digest(path)


def read_export(path):
    opener = gzip.open if path.suffix == '.gz' else open
    with opener(path, 'rt') as file:
        header = tuple(next(csv.reader([file.readline().rstrip('\r\n')])))
        if header != HEADER:
            raise RuntimeError('unexpected held-out export schema: ' + str(path))
        values = np.loadtxt(file, delimiter=',', dtype=np.float64, ndmin=2)
    if values.shape[0] == 0 or values.shape[1] != len(HEADER):
        raise RuntimeError('empty or malformed held-out export: ' + str(path))
    if not np.all(np.isfinite(values)):
        raise RuntimeError('nonfinite held-out export: ' + str(path))
    for name in ('event_id', 'source_event', 'photon_stratum'):
        x = values[:, COL[name]]
        if not np.array_equal(x, np.floor(x)) or np.any(np.abs(x) > 2**53):
            raise RuntimeError('noninteger or inexact identifiers: ' + str(path))
    for name in ('score_half', 'model_pass', 'cuts_pass'):
        if not np.all(np.isin(values[:, COL[name]], (0., 1.))):
            raise RuntimeError('invalid selection flag: ' + str(path))
    if np.any(values[:, COL['weight']] < 0) or np.any(values[:, COL['raw_weight']] < 0):
        raise RuntimeError('negative physical weight: ' + str(path))
    miss = values[:, COL['photon_miss_probability']]
    if np.any(miss <= 0) or np.any(miss > 1):
        raise RuntimeError('invalid loss probability: ' + str(path))
    if not np.allclose(values[:, COL['weight']], values[:, COL['raw_weight']] * miss,
                       rtol=2e-13, atol=0):
        raise RuntimeError('physical weight/miss mismatch: ' + str(path))
    if values[:, COL['weight']].sum() <= 0:
        raise RuntimeError('zero physical sample weight: ' + str(path))
    return values


def check_pair(reference, other, path, check_cuts=False):
    if reference.shape != other.shape:
        raise RuntimeError('unpaired held-out event count: ' + str(path))
    names = PAIRED_COLUMNS + (('cuts_pass',) if check_cuts else ())
    for name in names:
        if not np.array_equal(reference[:, COL[name]], other[:, COL[name]]):
            raise RuntimeError('unpaired held-out column ' + name + ': ' + str(path))


def load_matrices(point, output, config):
    """Load eight exports without retaining eight copies of their kinematics."""
    references = {}
    flags = {}
    support = []
    for feature_index, feature in enumerate(FEATURES):
        for model_index, method in enumerate(METHODS[:2]):
            for sample in ('signal', 'photon'):
                path = point / feature / ('test_' + method + '_' + sample + '.csv.gz')
                array = read_export(path)
                if sample not in references:
                    references[sample] = array
                    flags[sample] = np.empty((len(array), 6), dtype=np.float64)
                else:
                    check_pair(references[sample], array, path)
                index = feature_index * 3 + model_index
                flags[sample][:, index] = array[:, COL['model_pass']]
                if model_index == 0:
                    flags[sample][:, feature_index * 3 + 2] = array[:, COL['cuts_pass']]
                elif not np.array_equal(flags[sample][:, feature_index * 3 + 2],
                                        array[:, COL['cuts_pass']]):
                    raise RuntimeError('cuts changed between model exports: ' + str(path))
                weight = array[:, COL['weight']]
                for region, mask in [('all', np.ones(len(array), dtype=bool))] + (
                    [('central', array[:, COL['photon_stratum']] == 0),
                     ('outside', array[:, COL['photon_stratum']] == 1)] if sample == 'photon' else []):
                    w = weight[mask]
                    total = w.sum()
                    if total <= 0:
                        raise RuntimeError('zero-weight sample component in ' + str(path))
                    support.append(dict(sample=sample, stratum=region, feature_set=feature,
                                        method=method, entries=int(mask.sum()), sumw_pb=float(total),
                                        neff=float(total**2 / np.dot(w, w)),
                                        maximum_weight_fraction=float(w.max() / total),
                                        score_half_weight_fraction=float(
                                            np.dot(w, array[mask, COL['score_half']]) / total)))
    # The relative signal efficiencies use accepted-event weights conditionally.
    signal = references['signal']
    if not np.all(signal[:, COL['photon_stratum']] == -1):
        raise RuntimeError('signal export has photon-stratum identifiers')
    if not np.array_equal(signal[:, COL['source_event']], signal[:, COL['event_id']]):
        raise RuntimeError('signal event identifiers disagree')
    signal_matrix = np.column_stack([signal[:, COL['weight']],
                                    signal[:, COL['weight'], None] * flags['signal']])

    mass_name = point.name.split('_', 1)[1]
    merge_path = output / 'data' / point.parent.name / mass_name / 'test_merge.json'
    merge = json.loads(merge_path.read_text())
    photon = references['photon']
    if not np.all(np.isin(photon[:, COL['photon_stratum']], (0, 1))):
        raise RuntimeError('invalid photon stratum')
    strata = []
    nominal_epsilon = None
    for region_index, region in enumerate(('central', 'outside')):
        mask = photon[:, COL['photon_stratum']] == region_index
        rows = photon[mask]
        attempts = int(merge['attempts_' + region])
        if attempts < len(rows) or attempts <= 0 or len(rows) == 0:
            raise RuntimeError('invalid attempted-event count for ' + region)
        ids = rows[:, COL['source_event']]
        if np.any(ids < 0) or np.any(ids >= attempts) or np.any(np.diff(ids) <= 0):
            raise RuntimeError('invalid source attempted-event ordering in ' + region)
        if not np.array_equal(rows[:, COL['event_id']], ids):
            raise RuntimeError('photon original event identifier mismatch')
        miss = rows[:, COL['photon_miss_probability']]
        if not np.all(miss == miss[0]) or (region == 'outside' and miss[0] != 1.):
            raise RuntimeError('nominal component loss probability is not constant')
        if region == 'central':
            nominal_epsilon = float(miss[0])
            if not np.isclose(nominal_epsilon, 1e-6, rtol=1e-12, atol=0):
                raise RuntimeError('the declared nominal central loss probability must be 1e-6')
            if 'epsilon_central' in merge and not np.isclose(
                    nominal_epsilon, float(merge['epsilon_central']), rtol=1e-12, atol=0):
                raise RuntimeError('export loss probability disagrees with merge metadata')
        # Keep raw component integrals so every response scenario uses the same
        # resampled events, not a new simulation or an independent bootstrap.
        weights = rows[:, COL['raw_weight']]
        integral_key = region + '_sigma_pb'
        if integral_key in merge and not np.isclose(weights.sum(), float(merge[integral_key]),
                                                     rtol=2e-7, atol=0):
            raise RuntimeError('raw photon integral disagrees with merge metadata: ' + region)
        matrix = np.column_stack([weights, weights[:, None] * flags['photon'][mask]])
        strata.append((matrix, attempts))
    return signal_matrix, strata, support, merge_path, nominal_epsilon


def resample_sums(rng, matrix, attempts, size):
    """Exact fixed-N multinomial bootstrap; unstored attempts form one zero bin."""
    entries = len(matrix)
    if entries > attempts or entries < 1 or attempts < 1:
        raise ValueError('invalid sampling budget')
    probabilities = np.r_[np.full(entries, 1. / attempts),
                          max(0., 1. - entries / attempts)]
    return rng.multinomial(attempts, probabilities, size=size)[:, :-1] @ matrix


def rz_from_sums(signal, photon, photon_rate, dis_rate):
    if np.any(signal[..., :1] <= 0) or np.any(photon[..., :1] <= 0):
        raise RuntimeError('zero bootstrap sample total')
    signal_efficiency = signal[..., 1:] / signal[..., :1]
    photon_efficiency = photon[..., 1:] / photon[..., :1]
    denominator = photon_rate * photon_efficiency + dis_rate
    if np.any(denominator <= 0):
        raise RuntimeError('undefined significance denominator')
    result = signal_efficiency * np.sqrt((photon_rate + dis_rate) / denominator)
    if not np.all(np.isfinite(result)) or np.any(result <= 0):
        raise RuntimeError('undefined or zero selection performance; no bootstrap draws discarded')
    return result.reshape(result.shape[:-1] + (2, 3))


def scenario_performance(signal, central, outside, photon_rate, dis_rate):
    """Axes: draw, mode(shape/full/rate-only), epsilon, feature, method."""
    mixture = central[:, None, :] * EPSILONS[None, :, None] + outside[:, None, :]
    shape = rz_from_sums(signal[:, None, :], mixture, photon_rate, dis_rate)
    full = rz_from_sums(signal[:, None, :], mixture, mixture[:, :, :1], dis_rate)
    # Hold the nominal normalized shape fixed while changing only its total
    # photon rate. The same paired component draws define every scenario.
    nominal_mixture = central * 1e-6 + outside
    rate_only = rz_from_sums(signal[:, None, :], nominal_mixture[:, None, :],
                             mixture[:, :, :1], dis_rate)
    return np.stack([shape, full, rate_only], axis=1)


def contrast_logs(rz):
    flat = np.log(rz).reshape(rz.shape[:-2] + (6,))
    return np.stack([flat[..., c['numerator']] - flat[..., c['denominator']]
                     for c in CONTRASTS], axis=-1)


def interval_fields(point_ratio, values, simultaneous=False):
    alpha = .025 / FAMILY_SIZE if simultaneous else .025
    lo, hi = np.quantile(values, [alpha, 1 - alpha])
    prefix = 'family95_' if simultaneous else 'ci95_'
    return {prefix + 'low_ratio': float(lo), prefix + 'high_ratio': float(hi),
            prefix + 'low_advantage_pct': float(100 * (lo - 1)),
            prefix + 'high_advantage_pct': float(100 * (hi - 1))}


def precision_fields(point_ratio, low_ratio, high_ratio, runs, event_only=False):
    gain = point_ratio - 1
    half = (high_ratio - low_ratio) / 2
    maximum = max(abs(point_ratio - low_ratio), abs(high_ratio - point_ratio))
    meaningful = (low_ratio > 1 or high_ratio < 1) and abs(gain) > 1e-12
    relative = maximum / abs(gain) if abs(gain) > 1e-12 else None
    estimated = math.ceil(runs * (relative / .1)**2) if relative is not None and np.isfinite(relative) else None
    event_multiplier = ((relative / .1)**2 if relative is not None and np.isfinite(relative)
                        else None)
    allocation_note = (
        'conditional test-event diagnostic only; proportional scaling of all test sampling budgets, '
        'with the fitted selection and calibrated rates fixed; excludes fitting variation and is not a stopping rule'
        if event_only else
        'independent-run diagnostic only; variance scaling assumes unchanged fitting and sampling; '
        'not a stopping rule')
    return dict(advantage_pct=float(100 * gain), ci95_half_width_pp=float(100 * half),
                ci95_max_distance_pp=float(100 * maximum),
                relative_uncertainty_95=relative, nonzero_gain_resolved=bool(meaningful),
                target_10pct_met=bool(meaningful and relative <= .1),
                absolute_precision_benchmark_pp=ABSOLUTE_PRECISION_BENCHMARK_PP,
                absolute_precision_0p2pp_met=bool(
                    100 * maximum <= ABSOLUTE_PRECISION_BENCHMARK_PP + 1e-12),
                absolute_precision_scope='fixed exploratory benchmark; not a stopping rule',
                estimated_runs_if_only_run_count_changed=None if event_only else estimated,
                estimated_test_event_budget_multiplier_if_only_sampling_changed=(
                    event_multiplier if event_only else None),
                allocation_note=allocation_note)


def process_point(point, output, bootstrap, seed, batch, gate_hash, force=False):
    start = time.time()
    config_path = point / 'sample_config.json'
    config = json.loads(config_path.read_text())
    rep = int(config['rep'])
    typ = config['signal_type']
    mass = float(config['mass_GeV'])
    if typ not in ('vector', 'scalar') or rep not in EXPECTED_RUNS:
        raise RuntimeError('unexpected point type or independent-run index')
    if point.parent.name != f'rep_{rep:03d}' or point.name != f'{typ}_m{mass:.3f}'.replace('.', 'p'):
        raise RuntimeError('point configuration disagrees with directory')
    photon_rate, dis_rate = float(config['photon_xs_pb']), float(config['dis_xs_pb'])
    if not (np.isfinite(photon_rate) and photon_rate > 0 and np.isfinite(dis_rate) and dis_rate >= 0):
        raise RuntimeError('invalid calibrated nominal rates')
    files = [config_path, output / 'data' / point.parent.name / point.name.split('_', 1)[1] / 'test_merge.json']
    files += [point / f / f'test_{m}_{s}.csv.gz'
              for f in FEATURES for m in METHODS[:2] for s in ('signal', 'photon')]
    source_hashes = {str(p.relative_to(output)): digest(p) for p in files}
    settings = dict(bootstrap=bootstrap, seed=seed, batch=batch, gate_sha256=gate_hash,
                    script_sha256=digest(Path(__file__)), sources=source_hashes)
    signature = hashlib.sha256(json.dumps(settings, sort_keys=True).encode()).hexdigest()
    destination = point / 'analysis'
    marker = destination / 'analysis_complete.json'
    if marker.exists():
        old = json.loads(marker.read_text())
        if old['signature'] == signature:
            for name in ('nominal_RZ.npy', 'bootstrap_RZ.npy', 'test_metrics.csv', 'precision_estimate.csv',
                         'scenario_nominal_RZ.npy', 'scenario_bootstrap_RZ.npy', 'scenario_test_metrics.csv'):
                if not (destination / name).exists():
                    raise RuntimeError('incomplete analysis cache: ' + str(destination))
            return dict(point=str(point), cached=True)
        if not force:
            raise RuntimeError('analysis inputs/settings changed; use --force to recompute derived results')
    signal, strata, support, _, epsilon = load_matrices(point, output, config)
    ss = signal.sum(axis=0)
    central_sum, outside_sum = [item[0].sum(axis=0) for item in strata]
    ps = epsilon * central_sum + outside_sum
    nominal = rz_from_sums(ss, ps, photon_rate, dis_rate)
    scenario_nominal = scenario_performance(ss[None], central_sum[None], outside_sum[None],
                                            photon_rate, dis_rate)[0]
    # Both signal and background draws are shared by every method and feature set.
    mass_index = next((i for i, m in enumerate(MASSES) if np.isclose(m, mass, rtol=1e-9)), None)
    if mass_index is None:
        raise RuntimeError('mass lies outside the declared 11-point scan')
    rng = np.random.default_rng(seed + rep * 1000 + mass_index * 10 + (typ == 'scalar'))
    draws = np.empty((bootstrap, 2, 3))
    scenario_draws = np.empty((bootstrap, len(SCENARIO_MODES), len(EPSILONS),
                               len(FEATURES), len(METHODS)))
    for begin in range(0, bootstrap, batch):
        count = min(batch, bootstrap - begin)
        signal_draw = resample_sums(rng, signal, len(signal), count)
        central_draw, outside_draw = [resample_sums(rng, mat, attempts, count) for mat, attempts in strata]
        photon_draw = epsilon * central_draw + outside_draw
        draws[begin:begin + count] = rz_from_sums(signal_draw, photon_draw, photon_rate, dis_rate)
        scenario_draws[begin:begin + count] = scenario_performance(
            signal_draw, central_draw, outside_draw, photon_rate, dis_rate)
    if not np.array_equal(draws, scenario_draws[:, 0, 2]):
        if not np.allclose(draws, scenario_draws[:, 0, 2], rtol=2e-14, atol=0):
            raise RuntimeError('nominal analysis differs from its paired shape-only scenario')
    destination.mkdir(parents=True, exist_ok=True)
    atomic_npy(destination / 'nominal_RZ.npy', nominal)
    atomic_npy(destination / 'bootstrap_RZ.npy', draws)
    atomic_npy(destination / 'scenario_nominal_RZ.npy', scenario_nominal)
    atomic_npy(destination / 'scenario_bootstrap_RZ.npy', scenario_draws)
    atomic_csv(destination / 'support_diagnostics.csv', support)
    metrics = []
    for fi, feature in enumerate(FEATURES):
        for mi, method in enumerate(METHODS):
            index = fi * 3 + mi
            lower, upper = np.quantile(draws[:, fi, mi], [.025, .975])
            metrics.append(dict(rep=rep, signal_type=typ, mass_GeV=mass,
                                feature_set=feature, method=method, photon_xs_pb=photon_rate,
                                dis_xs_pb=dis_rate, test_photon_integral_pb=float(ps[0]),
                                signal_efficiency=float(ss[index + 1] / ss[0]),
                                photon_efficiency=float(ps[index + 1] / ps[0]),
                                RZ=float(nominal[fi, mi]), conditional_ci95_low=float(lower),
                                conditional_ci95_high=float(upper), bootstrap=bootstrap,
                                interval_scope='conditional on this fitted selection and fixed calibrated rates'))
    atomic_csv(destination / 'test_metrics.csv', metrics)
    scenario_metrics = []
    for mode_index, mode in enumerate(SCENARIO_MODES):
        for epsilon_index, varied_epsilon in enumerate(EPSILONS):
            total = varied_epsilon * central_sum[0] + outside_sum[0]
            for fi, feature in enumerate(FEATURES):
                for mi, method in enumerate(METHODS):
                    lower, upper = np.quantile(scenario_draws[:, mode_index, epsilon_index, fi, mi], [.025, .975])
                    scenario_metrics.append(dict(rep=rep, signal_type=typ, mass_GeV=mass,
                         mode=mode, epsilon=float(varied_epsilon), feature_set=feature, method=method,
                         photon_rate_used_pb=float(photon_rate if mode_index == 0 else total),
                         calculated_photon_integral_pb=float(total),
                         outside_weight_fraction=float(outside_sum[0] / (
                             ps[0] if mode == 'rate_only' else total)),
                         calculated_mixture_outside_weight_fraction=float(outside_sum[0] / total),
                         RZ=float(scenario_nominal[mode_index, epsilon_index, fi, mi]),
                         conditional_ci95_low=float(lower), conditional_ci95_high=float(upper),
                         interval_scope='descriptive pointwise; fixed fitted selections; excluded from nominal 198-comparison family'))
    atomic_csv(destination / 'scenario_test_metrics.csv', scenario_metrics)
    ratios = np.exp(contrast_logs(draws))
    points = np.exp(contrast_logs(nominal))
    precision = []
    for index, contrast in enumerate(CONTRASTS):
        fields = interval_fields(points[index], ratios[:, index])
        precision.append(dict(rep=rep, signal_type=typ, mass_GeV=mass,
                              **{k: v for k, v in contrast.items() if k not in ('numerator', 'denominator')},
                              ratio=float(points[index]), **fields,
                              **precision_fields(points[index], fields['ci95_low_ratio'], fields['ci95_high_ratio'],
                                                 1, event_only=True),
                              interval_scope='conditional on this fitted selection; excludes between-run variation'))
    atomic_csv(destination / 'precision_estimate.csv', precision)
    atomic_json(marker, dict(signature=signature, settings=settings, rep=rep, signal_type=typ,
                             mass_GeV=mass, axes=dict(feature=FEATURES, method=METHODS),
                             scenario_axes=dict(mode=SCENARIO_MODES, epsilon=EPSILONS.tolist(), feature=FEATURES, method=METHODS),
                             seconds=time.time() - start,
                             bootstrap='paired fixed-N per photon stratum, zero attempts included; conditional accepted signal; fixed calibrated total photon rate'))
    return dict(point=str(point), cached=False, seconds=time.time() - start)


def aggregate_group(nominal, bootstrap, rng, resamples, batch=2000):
    """Return nine paired geometric contrasts, resampling runs and their event draws."""
    if nominal.shape != (10, 2, 3) or bootstrap.ndim != 4 or bootstrap.shape[0] != 10 or bootstrap.shape[2:] != (2, 3):
        raise ValueError('aggregate requires ten paired independent runs')
    if not np.all(np.isfinite(nominal)) or np.any(nominal <= 0) or not np.all(np.isfinite(bootstrap)) or np.any(bootstrap <= 0):
        raise ValueError('invalid aggregate performance values')
    return aggregate_contrasts(nominal, bootstrap, rng, resamples, batch)


def aggregate_contrasts(nominal, bootstrap, rng, resamples, batch=2000):
    """Aggregate nominal or response-scenario arrays, preserving all paired axes."""
    event_log = contrast_logs(bootstrap)
    point = np.exp(contrast_logs(nominal).mean(axis=0))
    result = np.empty((resamples,) + event_log.shape[2:])
    for begin in range(0, resamples, batch):
        count = min(batch, resamples - begin)
        run_ids = rng.integers(0, 10, (count, 10))
        event_ids = rng.integers(0, bootstrap.shape[1], (count, 10))
        result[begin:begin + count] = np.exp(event_log[run_ids, event_ids].mean(axis=1))
    return point, result


def summarize(output, aggregate_resamples, seed, expected_groups=22, expected_points=220):
    groups = {}
    for path in sorted((output / 'fits').glob('rep_*/*/analysis/analysis_complete.json')):
        meta = json.loads(path.read_text())
        key = (meta['signal_type'], float(meta['mass_GeV']))
        groups.setdefault(key, []).append((int(meta['rep']), path.parent))
    results = []
    scenario_results = []
    pending = []
    for group_index, (key, runs) in enumerate(sorted(groups.items())):
        if tuple(sorted(r for r, _ in runs)) != EXPECTED_RUNS:
            pending.append(dict(signal_type=key[0], mass_GeV=key[1], completed_runs=sorted(r for r, _ in runs)))
            continue
        paths = [p for _, p in sorted(runs)]
        rates = [json.loads((p.parent / 'sample_config.json').read_text()) for p in paths]
        for rate_name in ('photon_xs_pb', 'dis_xs_pb'):
            if not all(float(r[rate_name]) == float(rates[0][rate_name]) for r in rates):
                raise RuntimeError('independent runs use different calibrated nominal rates')
        nominal = np.stack([np.load(p / 'nominal_RZ.npy', allow_pickle=False) for p in paths])
        bootstrap = np.stack([np.load(p / 'bootstrap_RZ.npy', allow_pickle=False) for p in paths])
        point, dist = aggregate_group(nominal, bootstrap, np.random.default_rng(seed + group_index), aggregate_resamples)
        for index, contrast in enumerate(CONTRASTS):
            fields = interval_fields(point[index], dist[:, index])
            results.append(dict(signal_type=key[0], mass_GeV=key[1],
                                **{k: v for k, v in contrast.items() if k not in ('numerator', 'denominator')},
                                geometric_mean_ratio=float(point[index]), **fields,
                                **interval_fields(point[index], dist[:, index], simultaneous=True),
                                **precision_fields(point[index], fields['ci95_low_ratio'], fields['ci95_high_ratio'], 10),
                                family_size=FAMILY_SIZE, independent_runs=10,
                                event_bootstrap_per_run=bootstrap.shape[1], aggregate_resamples=aggregate_resamples,
                                photon_xs_pb=float(rates[0]['photon_xs_pb']), dis_xs_pb=float(rates[0]['dis_xs_pb']),
                                interval_method='percentile bootstrap; family interval uses Bonferroni tail probabilities',
                                calibration_uncertainty='fixed independent nominal rate; integration calibration uncertainty not propagated'))
        # Response scenarios are descriptive, outside the 198 nominal tests.
        # Their pointwise intervals need no extreme Bonferroni tail estimation.
        scenario_nominal = np.stack([np.load(p / 'scenario_nominal_RZ.npy', allow_pickle=False) for p in paths])
        scenario_bootstrap = np.stack([np.load(p / 'scenario_bootstrap_RZ.npy', allow_pickle=False) for p in paths])
        scenario_point, scenario_dist = aggregate_contrasts(
            scenario_nominal, scenario_bootstrap, np.random.default_rng(seed + group_index + 100000), 20000, batch=200)
        for mode_index, mode in enumerate(SCENARIO_MODES):
            for epsilon_index, epsilon in enumerate(EPSILONS):
                for index, contrast in enumerate(CONTRASTS):
                    fields = interval_fields(scenario_point[mode_index, epsilon_index, index],
                                             scenario_dist[:, mode_index, epsilon_index, index])
                    scenario_results.append(dict(signal_type=key[0], mass_GeV=key[1], mode=mode,
                         epsilon=float(epsilon),
                         **{k: v for k, v in contrast.items() if k not in ('numerator', 'denominator')},
                         geometric_mean_ratio=float(scenario_point[mode_index, epsilon_index, index]),
                         advantage_pct=float(100 * (scenario_point[mode_index, epsilon_index, index] - 1)),
                         **fields, independent_runs=10, aggregate_resamples=20000,
                         interval_scope='descriptive pointwise 95%; excluded from nominal 198-comparison family',
                         selection_scope='same nominal fitted selections and thresholds in every scenario'))
        print('Summarized', key, flush=True)
    if results:
        atomic_csv(output / 'summary.csv', results)
        atomic_csv(output / 'scenario_summary.csv', scenario_results)
    status = dict(complete_groups=len(results) // len(CONTRASTS), expected_groups=expected_groups,
                  state='complete' if len(results) // len(CONTRASTS) == expected_groups else 'partial',
                  completed_independent_points=sum(len(r) for r in groups.values()), expected_points=expected_points,
                  incomplete_groups=pending, family_size=FAMILY_SIZE,
                  primary_contrasts=66, method_contrasts=132,
                  descriptive_scenario_rows=len(scenario_results),
                  required_aggregate_resamples=aggregate_resamples)
    atomic_json(output / 'analysis_status.json', status)
    return status


def self_test():
    """Synthetic invariants only: no project event or fitted-model files are read."""
    rng = np.random.default_rng(231)
    # All-pass selections have RZ=1 regardless of component rates or zero attempts.
    signal = np.tile(np.array([1., 2., 3., 4.])[:, None], (1, 7))
    central = np.tile(np.array([.3, .6, .9])[:, None], (1, 7))
    outside = np.tile(np.array([.2, .4])[:, None], (1, 7))
    sb = resample_sums(rng, signal, 4, 200)
    cb = resample_sums(rng, central, 5, 200)
    ob = resample_sums(rng, outside, 3, 200)
    keep = cb[:, 0] + ob[:, 0] > 0
    rz = rz_from_sums(sb[keep], cb[keep] + ob[keep], .35, .0155)
    assert np.allclose(rz, np.ones_like(rz), rtol=0, atol=2e-15)
    assert np.allclose(contrast_logs(rz), np.zeros((len(rz), 9)), rtol=0, atol=2e-15)
    # Duplicated feature selections have exactly zero paired t uncertainty.
    signal_flags = np.array([[1, 0, 1], [1, 1, 0], [0, 1, 1], [1, 1, 1.]])
    photon_flags = np.array([[1, 0, 1], [0, 1, 1], [1, 1, 0.]])
    sm = np.column_stack([np.ones(4), signal_flags, signal_flags])
    pm = np.column_stack([np.ones(3), photon_flags, photon_flags])
    nominal = rz_from_sums(sm.sum(0), pm.sum(0), .35, .0155)
    assert np.array_equal(contrast_logs(nominal)[:3], np.zeros(3))
    # A simple analytic efficiency/RZ check.
    expected = .75 * np.sqrt((.35 + .0155) / (.35 * 2 / 3 + .0155))
    assert np.isclose(nominal[0, 0], expected, rtol=1e-14)
    # Fixed-N stratum bootstrap matches analytic variance including zero attempts.
    weighted = np.array([[1.], [2.], [4.]])
    sample = resample_sums(np.random.default_rng(9), weighted, 10, 100000)
    variance = float((weighted**2).sum() - weighted.sum()**2 / 10)
    assert abs(float(sample.var()) / variance - 1) < .025
    # Geometric aggregation preserves the pairing of all feature/method contrasts.
    pn = np.tile(nominal, (10, 1, 1))
    pb = np.tile(nominal, (10, 50, 1, 1))
    point, dist = aggregate_group(pn, pb, np.random.default_rng(5), 5000)
    assert np.allclose(point[:3], 1., rtol=0, atol=1e-15)
    assert np.array_equal(dist[:, :3], np.ones((5000, 3)))
    assert np.allclose(dist, point[None, :], rtol=2e-15, atol=0)
    # All response scenarios reuse the same components, with a separate total-rate
    # control; nominal shape-only scenario must equal the primary calculation.
    sc = scenario_performance(sm.sum(0)[None], pm.sum(0)[None] * 1e6,
                              pm.sum(0)[None] * .2, .35, .0155)
    base = rz_from_sums(sm.sum(0)[None], pm.sum(0)[None] * 1.2, .35, .0155)
    assert sc.shape == (1, len(SCENARIO_MODES), len(EPSILONS), len(FEATURES), len(METHODS))
    assert np.allclose(sc[:, 0, 2], base, rtol=2e-15, atol=0)
    # The full-rate and rate-only controls coincide at nominal epsilon. At all
    # other epsilon values the rate-only control retains nominal efficiencies.
    assert np.array_equal(sc[:, 1, 2], sc[:, 2, 2])
    independent_rate_control = rz_from_sums(
        sm.sum(0)[None, None, :], (pm.sum(0) * 1.2)[None, None, :],
        ((pm.sum(0)[0] * 1e6) * EPSILONS + pm.sum(0)[0] * .2)[None, :, None], .0155)
    assert np.allclose(sc[:, 2], independent_rate_control, rtol=2e-15, atol=0)
    # Different component pass fractions distinguish a real shape change from
    # the rate-only control; equal component shapes alone cannot test this.
    central_different = np.array([[2., 1., 1.2, 1.4, 1.2, .6, .8]]) * 1e6
    outside_different = np.array([[.2, .02, .04, .06, .08, .1, .12]])
    controls = scenario_performance(sm.sum(0)[None], central_different, outside_different, .35, .0155)
    for index, epsilon in enumerate(EPSILONS):
        expected_rate_only = rz_from_sums(
            sm.sum(0)[None], central_different * 1e-6 + outside_different,
            epsilon * central_different[:, :1] + outside_different[:, :1], .0155)
        assert np.allclose(controls[:, 2, index], expected_rate_only, rtol=2e-15, atol=0)
    assert not np.allclose(controls[:, 1, 0], controls[:, 2, 0])
    sn = np.tile(sc[0], (10, 1, 1, 1, 1))
    sb = np.tile(sc[0], (10, 20, 1, 1, 1, 1))
    sp, sd = aggregate_contrasts(sn, sb, np.random.default_rng(8), 200)
    assert sp.shape == (len(SCENARIO_MODES), len(EPSILONS), len(CONTRASTS))
    assert sd.shape == (200, len(SCENARIO_MODES), len(EPSILONS), len(CONTRASTS))
    assert np.allclose(sd, sp[None], rtol=2e-15, atol=0)
    conditional = precision_fields(1.03, 1.028, 1.032, 1, event_only=True)
    assert conditional['estimated_runs_if_only_run_count_changed'] is None
    assert conditional['estimated_test_event_budget_multiplier_if_only_sampling_changed'] is not None
    assert conditional['absolute_precision_0p2pp_met']
    # Near-zero changes retain an absolute precision diagnostic without a
    # misleading assertion of resolved relative precision.
    near_zero = precision_fields(1., .999, 1.001, 10)
    assert near_zero['relative_uncertainty_95'] is None
    assert not near_zero['target_10pct_met'] and near_zero['absolute_precision_0p2pp_met']
    assert near_zero['estimated_test_event_budget_multiplier_if_only_sampling_changed'] is None
    assert len(CONTRASTS) * 22 == FAMILY_SIZE
    print('Synthetic tests passed: normalization, pairing, direct-t contrasts, zero attempts, bootstrap variance, geometric aggregation, rate-only control, precision diagnostics, family size.')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', '--results', dest='output', type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument('--gate-file', type=Path)
    parser.add_argument('--workers', type=int, default=4)
    parser.add_argument('--bootstrap', type=int, default=2000)
    parser.add_argument('--aggregate-resamples', type=int, default=1000000)
    parser.add_argument('--batch', type=int, default=32)
    parser.add_argument('--seed', type=int, default=48230000)
    parser.add_argument('--rep', type=int, action='append')
    parser.add_argument('--mass', type=float, action='append')
    parser.add_argument('--signal-type', choices=('scalar', 'vector'), action='append')
    parser.add_argument('--summarize-only', action='store_true')
    parser.add_argument('--force', action='store_true')
    parser.add_argument('--self-test', action='store_true')
    args = parser.parse_args()
    if args.self_test:
        self_test()
        return
    if args.workers < 1 or args.workers > 4 or args.bootstrap < 2000 or args.batch < 1:
        parser.error('workers must be 1–4, bootstrap >=2000, batch >=1')
    if args.aggregate_resamples < 1000000:
        parser.error('at least 1,000,000 aggregate resamples are required for the 198-comparison tails')
    output = args.output.resolve()
    gate_path = args.gate_file or output / 'fit_protocol_gate.json'
    gate_hash = gate_check(gate_path)
    gate = json.loads(gate_path.read_text())
    expected_groups = int(gate.get('expected_groups', 22))
    expected_points = int(gate.get('expected_points', 220))
    if expected_groups <= 0 or expected_points <= 0:
        parser.error('gate expected_groups and expected_points must be positive')
    if not args.summarize_only:
        points = []
        for config_path in sorted((output / 'fits').glob('rep_*/*/sample_config.json')):
            config = json.loads(config_path.read_text())
            if args.rep and int(config['rep']) not in args.rep:
                continue
            if args.mass and not any(np.isclose(float(config['mass_GeV']), m, rtol=1e-9) for m in args.mass):
                continue
            if args.signal_type and config['signal_type'] not in args.signal_type:
                continue
            # Sample configuration can precede fitting. Only completed exports
            # are eligible, and all eight files must exist before opening any.
            point = config_path.parent
            files = [point / f / f'test_{m}_{s}.csv.gz'
                     for f in FEATURES for m in METHODS[:2] for s in ('signal', 'photon')]
            if all(p.exists() for p in files):
                points.append(point)
        with ThreadPoolExecutor(max_workers=args.workers) as pool:
            futures = [pool.submit(process_point, p, output, args.bootstrap, args.seed,
                                   args.batch, gate_hash, args.force) for p in points]
            completed = 0
            atomic_json(output / 'analysis_status.json', dict(state='running', completed_points=0,
                        eligible_points=len(points), expected_points=expected_points,
                        expected_groups=expected_groups, workers=args.workers))
            for future in as_completed(futures):
                try:
                    result = future.result()
                except BaseException as error:
                    for pending_future in futures:
                        pending_future.cancel()
                    atomic_json(output / 'analysis_status.json', dict(state='failed', completed_points=completed,
                                eligible_points=len(points), expected_points=expected_points,
                                expected_groups=expected_groups, error=str(error)))
                    raise
                completed += 1
                print(json.dumps(result), flush=True)
                atomic_json(output / 'analysis_status.json', dict(state='running', completed_points=completed,
                            eligible_points=len(points), expected_points=expected_points,
                            expected_groups=expected_groups, workers=args.workers))
    print(json.dumps(summarize(output, args.aggregate_resamples, args.seed + 900000,
                               expected_groups, expected_points), indent=2))


if __name__ == '__main__':
    main()
