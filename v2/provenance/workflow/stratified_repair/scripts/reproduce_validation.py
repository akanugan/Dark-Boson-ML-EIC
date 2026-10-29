#!/usr/bin/env python3
"""Check evaluation-only reselection against unchanged original validation data.

Prepares 16 cases. No actual evaluation runs without --execute. Never reads a
final test file or trains a model. A shared maximum of four workers is enforced.
"""
import os
for _key in ('OMP_NUM_THREADS', 'OPENBLAS_NUM_THREADS', 'VECLIB_MAXIMUM_THREADS'):
    os.environ[_key] = '1'
import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
import csv
import gzip
import hashlib
import json
from pathlib import Path
import subprocess
import time

REPAIR = Path(__file__).resolve().parents[1]
OLD = REPAIR.parent / 'stratified_refit'
BINARY = REPAIR / 'bin/rethreshold_validation'
FEATURES = ('electron', 'electron_qa2')
METHODS = (('bdt', 'BDTG'), ('likelihood', 'PDERS'))
ABS_TOL = 5e-11
REL_TOL = 5e-10


def digest(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()


def row(path):
    with path.open() as stream:
        records = list(csv.DictReader(stream))
    if len(records) != 1:
        raise RuntimeError(f'Expected exactly one metrics row: {path}')
    return records[0]


def write_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + '.tmp')
    tmp.write_text(json.dumps(value, indent=2) + '\n')
    tmp.replace(path)


def cases():
    output = []
    for mass, rep in ((5.0, 1), (6.31, 4)):
        tag = 'm' + f'{mass:.3f}'.replace('.', 'p')
        for typ in ('vector', 'scalar'):
            point = OLD / 'fits' / f'rep_{rep:03d}' / f'{typ}_{tag}'
            cfg = json.loads((point / 'sample_config.json').read_text())
            for feature in FEATURES:
                for method, tmva_tag in METHODS:
                    selected_path = point / feature / f'{method}_selected.csv'
                    selected = row(selected_path)
                    profile = selected['model_profile']
                    model = point / feature / method / profile
                    metrics_path = model / 'metrics.csv'
                    original = row(metrics_path)
                    for key in ('validation_threshold', 'validation_significance_improvement', 'model_profile'):
                        if selected[key] != original[key]:
                            raise RuntimeError(f'Selected row differs from its original candidate: {key}')
                    xml = model / 'dataset/weights' / f'TMVAClassification_{tmva_tag}.weights.xml'
                    source = xml.with_suffix('.xml.gz') if xml.with_suffix('.xml.gz').exists() else xml
                    signal = point / 'data/signal_validation.root'
                    photon = OLD / 'data' / f'rep_{rep:03d}' / tag / 'validation.root'
                    for p in (signal, photon, source, metrics_path):
                        if not p.is_file():
                            raise FileNotFoundError(p)
                        if 'test' in p.name:
                            raise RuntimeError('Final test input forbidden')
                    output.append(dict(case=f'{typ}_{tag}_rep{rep:03d}_{feature}_{method}',
                                       mass_GeV=mass, rep=rep, signal_type=typ, feature_set=feature,
                                       method=method, profile=profile, original_metrics=metrics_path,
                                       original_selected=selected_path, original_xml=source,
                                       signal_validation=signal, photon_validation=photon,
                                       photon_xs_pb=cfg['photon_xs_pb'], dis_xs_pb=cfg['dis_xs_pb']))
    assert len(output) == 16
    return output


def one(case, root):
    destination = root / case['case']
    destination.mkdir(parents=True, exist_ok=True)
    source = case['original_xml']
    raw = gzip.decompress(source.read_bytes()) if source.suffix == '.gz' else source.read_bytes()
    local_xml = destination / 'original_model.xml'
    args = [str(BINARY), str(case['signal_validation']), str(case['photon_validation']),
            str(local_xml), str(case['original_metrics']), str(destination), case['feature_set'],
            str(case['photon_xs_pb']), str(case['dis_xs_pb']), case['profile']]
    inputs = {str(case[key]): digest(case[key]) for key in
              ('original_metrics', 'original_selected', 'original_xml',
               'signal_validation', 'photon_validation')}
    inputs[str(BINARY)] = digest(BINARY)
    signature = hashlib.sha256(json.dumps(dict(arguments=args, input_sha256=inputs), sort_keys=True).encode()).hexdigest()
    marker = destination / 'comparison.json'
    if marker.exists():
        saved = json.loads(marker.read_text())
        if saved['signature'] != signature:
            raise RuntimeError('Changed completed reproduction input')
        for path, expected in saved['output_sha256'].items():
            if digest(path) != expected:
                raise RuntimeError('Changed completed reproduction output')
        return saved
    if local_xml.exists() and local_xml.read_bytes() != raw:
        raise RuntimeError('QA XML copy changed')
    local_xml.write_bytes(raw)
    started = time.time()
    write_json(destination / 'command.json', dict(arguments=args, input_sha256=inputs,
                                                 uncompressed_xml_sha256=hashlib.sha256(raw).hexdigest()))
    with (destination / 'evaluation.log').open('w') as stream:
        subprocess.run(args, stdout=stream, stderr=subprocess.STDOUT, check=True)
    expected = row(case['original_metrics'])
    actual = row(destination / 'validation_metrics.csv')
    comparisons = {}
    for key, value in actual.items():
        old, new = float(expected[key]), float(value)
        difference = abs(new - old)
        tolerance = ABS_TOL + REL_TOL * max(abs(old), abs(new))
        if key.endswith('_entries'):
            tolerance = 0.
        comparisons[key] = dict(original=old, reproduced=new, absolute_difference=difference,
                                tolerance=tolerance, passed=difference <= tolerance)
    outputs = [local_xml, destination / 'validation_metrics.csv', destination / 'command.json',
               destination / 'validation_signal_scores.csv', destination / 'validation_photon_scores.csv',
               destination / 'evaluation.log']
    result = dict(**{k: v for k, v in case.items() if not isinstance(v, Path)},
                  seconds=time.time() - started, signature=signature, input_sha256=inputs,
                  output_sha256={str(p): digest(p) for p in outputs},
                  passed=all(value['passed'] for value in comparisons.values()),
                  comparisons=comparisons, reads_final_tests=False, trains_models=False)
    write_json(marker, result)
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--execute', action='store_true')
    parser.add_argument('--workers', type=int, default=4)
    parser.add_argument('--output', type=Path, default=REPAIR / 'qa/original_validation')
    args = parser.parse_args()
    if not 1 <= args.workers <= 4:
        parser.error('--workers must be between 1 and 4, shared with other heavy jobs')
    root = args.output.absolute()
    if not root.resolve().is_relative_to((REPAIR / 'qa').resolve()):
        parser.error('QA output must be inside stratified_repair/qa')
    jobs = cases()
    plan = dict(cases=[{k: str(v) if isinstance(v, Path) else v for k, v in case.items()} for case in jobs],
                total=16, workers=args.workers, reads_final_tests=False, trains_models=False,
                comparison='Same original XML, original validation samples and original rates; evaluation-only helper must reproduce original candidate metrics',
                absolute_tolerance=ABS_TOL, relative_tolerance=REL_TOL)
    if not args.execute:
        print(json.dumps(plan, indent=2))
        return
    if not BINARY.is_file():
        raise FileNotFoundError(BINARY)
    write_json(root / 'protocol.json', plan)
    results, errors = [], []
    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        futures = {pool.submit(one, case, root): case for case in jobs}
        for future in as_completed(futures):
            case = futures[future]
            try:
                result = future.result()
                results.append(result)
                print(case['case'], 'PASS' if result['passed'] else 'DISCREPANCY', flush=True)
            except Exception as error:
                errors.append(dict(case=case['case'], error=str(error)))
                print(case['case'], 'ERROR', error, flush=True)
    results.sort(key=lambda value: value['case'])
    report = dict(state='passed' if len(results) == 16 and not errors and all(r['passed'] for r in results) else 'failed',
                  completed=len(results), total=16, errors=errors, results=results)
    write_json(root / 'summary.json', report)
    lines = ['# Original-validation reproduction check', '',
             'Same original selected XMLs, original validation events, and original rates. No models trained and no final test samples read.', '',
             '| Case | Original validation RZ | Reproduced RZ | Original threshold | Reproduced threshold | Result |',
             '|---|---:|---:|---:|---:|---|']
    for result in results:
        rz = result['comparisons']['validation_significance_improvement']
        threshold = result['comparisons']['validation_threshold']
        lines.append(f"| {result['case']} | {rz['original']:.12g} | {rz['reproduced']:.12g} | {threshold['original']:.12g} | {threshold['reproduced']:.12g} | {'PASS' if result['passed'] else 'DISCREPANCY'} |")
    lines += ['', 'All shared numeric candidate fields are compared in the JSON report, including efficiencies, weighted AUC, event counts and the original significance proxy. Numerical tolerance is absolute 5e-11 plus relative 5e-10; entry counts must match exactly. Any discrepancy requires investigation before interpreting repaired validation selections.']
    (root / 'summary.md').write_text('\n'.join(lines) + '\n')
    if report['state'] != 'passed':
        raise SystemExit(1)


if __name__ == '__main__':
    main()
