#!/usr/bin/env python3
"""Reselect validation-only repairs without retraining or reading final tests.

Default is a plan. --execute is required after the repair overlay is ready.
"""
import os
for _key in ('OMP_NUM_THREADS', 'OPENBLAS_NUM_THREADS', 'VECLIB_MAXIMUM_THREADS'):
    os.environ[_key] = '1'
import argparse
import csv
import gzip
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys
import time

REPAIR = Path(__file__).resolve().parents[1]
REVISION = REPAIR.parent
sys.path.insert(0, str(REVISION / 'scripts'))
import run_stratified_refit as original


def digest(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as f:
        for block in iter(lambda: f.read(1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()


def writable(path):
    path = Path(path)
    if not path.parent.resolve().is_relative_to(REPAIR.resolve()):
        raise RuntimeError(f'Output escapes repair root: {path}')
    if path.is_symlink():
        path.unlink()
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def copy_real(source, destination):
    source, destination = Path(source), writable(destination)
    if source.resolve() == destination.resolve():
        raise RuntimeError('Refusing to use original file as output')
    if destination.exists() and digest(destination) == digest(source):
        return
    shutil.copy2(source, destination)
    if destination.is_symlink() or digest(destination) != digest(source):
        raise RuntimeError('Real-file copy verification failed')


def write_csv(path, records):
    path = writable(path)
    with path.open('w', newline='') as f:
        w = csv.DictWriter(f, fieldnames=list(records[0]))
        w.writeheader()
        w.writerows(records)


def write_json(path, data):
    path = writable(path)
    path.write_text(json.dumps(data, indent=2) + '\n')


def run(args, log, marker, sources):
    args = list(map(str, args))
    provenance = dict(arguments=args, executable_sha256=digest(args[0]),
                      input_sha256={str(p): digest(p) for p in sources})
    signature = hashlib.sha256(json.dumps(provenance, sort_keys=True).encode()).hexdigest()
    marker, log = Path(marker), Path(log)
    if marker.exists() and not marker.is_symlink():
        saved = json.loads(marker.read_text())
        if saved['signature'] != signature:
            raise RuntimeError(f'Changed completed reselection command: {marker}')
        return saved
    writable(log)
    started = time.time()
    with log.open('w') as f:
        f.write(json.dumps(args) + '\n')
        f.flush()
        subprocess.run(args, stdout=f, stderr=subprocess.STDOUT, check=True)
    result = dict(signature=signature, seconds=time.time() - started, **provenance)
    write_json(marker, result)
    return result


def real_xml(old_model, new_model, tag):
    relative = Path('dataset/weights') / f'TMVAClassification_{tag}.weights.xml'
    old_xml, new_xml = old_model / relative, new_model / relative
    source = old_xml if old_xml.exists() else old_xml.with_suffix('.xml.gz')
    if not source.is_file():
        raise FileNotFoundError(source)
    raw = gzip.decompress(source.read_bytes()) if source.suffix == '.gz' else source.read_bytes()
    writable(new_xml)
    if new_xml.exists() and new_xml.read_bytes() != raw:
        raise RuntimeError(f'Candidate XML differs from original: {new_xml}')
    new_xml.write_bytes(raw)
    if new_xml.is_symlink() or hashlib.sha256(new_xml.read_bytes()).hexdigest() != hashlib.sha256(raw).hexdigest():
        raise RuntimeError('Candidate XML is not an identical real-file copy')
    return new_xml, dict(original=str(source), original_file_sha256=digest(source),
                         uncompressed_xml_sha256=hashlib.sha256(raw).hexdigest())


def check_args(args):
    point, old = args.point.absolute(), args.original_point.absolute()
    if not point.resolve().is_relative_to(REPAIR.resolve()) or point.resolve() == old.resolve():
        raise RuntimeError('A distinct output point inside stratified_repair is required')
    cfg_path = point / 'sample_config.json'
    cfg = json.loads(cfg_path.read_text())
    old_cfg = json.loads((old / 'sample_config.json').read_text())
    for key in ('rep', 'mass_GeV', 'signal_type', 'signal_xs_pb', 'photon_xs_pb', 'dis_xs_pb'):
        if str(cfg[key]) != str(old_cfg[key]):
            raise RuntimeError(f'Validation repair changed fixed configuration {key}')
    mass, rep = float(cfg['mass_GeV']), int(cfg['rep'])
    if not ((mass == 5.0 and rep == 1) or (mass == 6.31 and rep == 4)):
        raise RuntimeError('Helper is limited to the two validation-only repair points')
    if cfg['signal_type'] not in ('vector', 'scalar'):
        raise RuntimeError('Unknown boson type')
    signal_train, signal_validation = old / 'data/signal_train.root', old / 'data/signal_validation.root'
    photon_train, photon_validation = args.photon_train.absolute(), args.photon_validation.absolute()
    old_photon_train = old.parents[2] / 'data' / f'rep_{rep:03d}' / original.label(mass) / 'train.root'
    for p in (signal_train, signal_validation, photon_train, photon_validation, old_photon_train):
        if not p.is_file():
            raise FileNotFoundError(p)
        if 'test' in p.name:
            raise RuntimeError(f'Final test input forbidden: {p}')
    if digest(photon_train) != digest(old_photon_train):
        raise RuntimeError('Validation-only reselection requires unchanged photon training')
    return point, old, cfg, signal_train, signal_validation, photon_train, photon_validation


def input_manifest(point, old, sigtrain, sigval, phtrain, phval, binaries):
    """Everything read to choose selections; no final-test paths are included."""
    paths = [point / 'sample_config.json', old / 'sample_config.json',
             sigtrain, sigval, phtrain, phval, Path(__file__),
             Path(original.__file__), *binaries]
    for feature in original.FEATURES:
        for method, tag, profiles in [('bdt', 'BDTG', original.BDT_PROFILES),
                                      ('likelihood', 'PDERS', original.LIKELIHOOD_PROFILES)]:
            for profile in profiles:
                model = old / feature / method / profile
                paths.append(model / 'metrics.csv')
                xml = model / 'dataset/weights' / f'TMVAClassification_{tag}.weights.xml'
                paths.append(xml if xml.exists() else xml.with_suffix('.xml.gz'))
        paths.extend(old / feature / 'boxes' / f'q{q}.csv' for q in (40, 80, 160))
    return {str(path.absolute()): digest(path) for path in paths}


def output_paths(point):
    """Only helper-owned validation artifacts; excludes later test/fit markers."""
    paths = [point / 'validation_support.csv']
    for feature in original.FEATURES:
        dest = point / feature
        for method in ('bdt', 'likelihood', 'cuts'):
            paths.extend([dest / f'{method}_selected.csv', dest / f'{method}_candidates.csv'])
        for q in (40, 80, 160):
            path = dest / 'boxes' / f'q{q}.csv'
            paths.extend([path, path.with_suffix('.repair.log'),
                          path.with_suffix('.repair.done.json')])
        for method, tag, profiles in [('bdt', 'BDTG', original.BDT_PROFILES),
                                      ('likelihood', 'PDERS', original.LIKELIHOOD_PROFILES)]:
            for profile in profiles:
                model = dest / method / profile
                paths.extend([model / 'metrics.csv', model / 'original_metrics.csv',
                              model / 'dataset/weights' / f'TMVAClassification_{tag}.weights.xml.gz'])
                evaluation = model / 'reselection'
                paths.extend(evaluation / name for name in
                             ('validation_metrics.csv', 'validation_signal_scores.csv.gz',
                              'validation_photon_scores.csv.gz', 'validation.log', 'complete.json'))
            prefix = dest / f'validation_{method}'
            paths.extend(dest / (prefix.name + suffix) for suffix in
                         ('_signal.csv.gz', '_photon.csv.gz', '_support.csv', '_metrics.csv'))
            paths.extend([prefix.with_suffix('.repair.log'),
                          prefix.with_suffix('.repair.done.json')])
    return paths


def output_manifest(point):
    return {str(path.absolute()): digest(path) for path in output_paths(point)}


def verify_completed(point, inputs):
    marker = point / 'validation_reselect_complete.json'
    if not marker.exists():
        return None
    saved = json.loads(marker.read_text())
    if saved.get('resume_manifest_version') != 1:
        raise RuntimeError('Completed validation repair lacks strict resume manifests')
    if saved.get('input_sha256') != inputs:
        raise RuntimeError('Inputs to completed validation reselection changed; refusing to redo it')
    try:
        outputs = output_manifest(point)
    except (FileNotFoundError, OSError) as error:
        raise RuntimeError('Output of completed validation reselection is missing') from error
    if saved.get('output_sha256') != outputs:
        raise RuntimeError('Outputs of completed validation reselection changed; refusing to rewrite them')
    return saved


def execute(args):
    point, old, cfg, sigtrain, sigval, phtrain, phval = check_args(args)
    plan = dict(point=str(point), original_point=str(old), mass_GeV=cfg['mass_GeV'],
                rep=cfg['rep'], signal_type=cfg['signal_type'],
                signal_train=str(sigtrain), signal_validation=str(sigval),
                photon_train=str(phtrain), photon_validation=str(phval),
                features=original.FEATURES,
                bdt_profiles=original.BDT_PROFILES,
                likelihood_profiles=original.LIKELIHOOD_PROFILES,
                cuts_quantiles=[40, 80, 160], cuts_restarts=20,
                reads_final_tests=False, retrains_tmva=False)
    if not args.execute:
        print(json.dumps(plan, indent=2))
        return
    binary = REPAIR / 'bin/rethreshold_validation'
    exporter = REVISION / 'bin/export_refit_scores'
    rectangles = original.PROJECT / 'bin/optimize_rectangular_fair'
    for b in (binary, exporter, rectangles):
        if not b.is_file():
            raise FileNotFoundError(b)
    inputs = input_manifest(point, old, sigtrain, sigval, phtrain, phval,
                            (binary, exporter, rectangles))
    completed = verify_completed(point, inputs)
    if completed is not None:
        print(json.dumps(dict(state=completed['state'], point=str(point),
                              seconds=completed['seconds'], verified_resume=True), indent=2))
        return
    started = time.time()
    px, dx = cfg['photon_xs_pb'], cfg['dis_xs_pb']
    sx, mass, rep, typ = cfg['signal_xs_pb'], float(cfg['mass_GeV']), int(cfg['rep']), cfg['signal_type']
    support, models = [], []
    for feature in original.FEATURES:
        dest, old_dest = point / feature, old / feature
        dest.mkdir(parents=True, exist_ok=True)
        for method, tag, profiles in [('bdt', 'BDTG', original.BDT_PROFILES),
                                      ('likelihood', 'PDERS', original.LIKELIHOOD_PROFILES)]:
            candidates = []
            for profile in profiles:
                old_model, model = old_dest / method / profile, dest / method / profile
                model.mkdir(parents=True, exist_ok=True)
                xml, provenance = real_xml(old_model, model, tag)
                template = model / 'original_metrics.csv'
                copy_real(old_model / 'metrics.csv', template)
                old_row = original.rows(template)[0]
                evaluation = model / 'reselection'
                evaluation.mkdir(parents=True, exist_ok=True)
                run([binary, sigval, phval, xml, template, evaluation, feature, px, dx, profile],
                    evaluation / 'validation.log', evaluation / 'complete.json',
                    [sigval, phval, xml, template])
                values = original.rows(evaluation / 'validation_metrics.csv')[0]
                row = dict(old_row)
                row.update(values)
                row['evaluation_mode'] = 'validation_all'
                for key in ('train_signal_entries', 'train_background_entries', 'random_seed', 'model_profile'):
                    if row[key] != old_row[key]:
                        raise RuntimeError(f'Original training metadata changed: {key}')
                write_csv(model / 'metrics.csv', [row])
                candidates.append(row)
                models.append(dict(feature_set=feature, method=method, profile=profile,
                                   **provenance))
                for sample in ('signal', 'photon'):
                    original.compress(evaluation / f'validation_{sample}_scores.csv')
                original.compress(xml)
            selected = max(candidates, key=lambda r: float(r['validation_significance_improvement']))
            write_csv(dest / f'{method}_candidates.csv', candidates)
            write_csv(dest / f'{method}_selected.csv', [selected])
        candidates = []
        for q in (40, 80, 160):
            old_q = old_dest / 'boxes' / f'q{q}.csv'
            record = original.rows(old_q)[0]
            if int(record['quantiles']) != q or int(record['restarts']) != 20:
                raise RuntimeError('Original rectangular grid/restart settings disagree')
            seed = record['optimizer_seed']
            path = dest / 'boxes' / f'q{q}.csv'
            writable(path)
            run([rectangles, sigtrain, phtrain, sigval, phval, sigval, phval, path,
                 typ, mass, sx, px, dx, feature, q, 20, seed],
                path.with_suffix('.repair.log'), path.with_suffix('.repair.done.json'),
                [sigtrain, phtrain, sigval, phval, old_q])
            candidates.extend(original.rows(path))
        selected, candidates = original.select_cuts(candidates, feature)
        write_csv(dest / 'cuts_candidates.csv', candidates)
        write_csv(dest / 'cuts_selected.csv', [selected])
        for method, tag in [('bdt', 'BDTG'), ('likelihood', 'PDERS')]:
            row = original.rows(dest / f'{method}_selected.csv')[0]
            model = dest / method / row['model_profile']
            old_model = old_dest / method / row['model_profile']
            xml, _ = real_xml(old_model, model, tag)
            prefix = dest / f'validation_{method}'
            run([exporter, sigval, phval, xml, dest / f'{method}_selected.csv',
                 dest / 'cuts_selected.csv', prefix, feature, px, dx],
                prefix.with_suffix('.repair.log'), prefix.with_suffix('.repair.done.json'),
                [sigval, phval, xml, dest / f'{method}_selected.csv', dest / 'cuts_selected.csv'])
            for record in original.rows(dest / f'validation_{method}_support.csv'):
                if record['sample'] == 'photon' and record['stratum'] == 'outside':
                    support.append(dict(rep=rep, signal_type=typ, mass_GeV=mass,
                                        feature_set=feature, method=method,
                                        profile=row['model_profile'], **record))
            for sample in ('signal', 'photon'):
                original.compress(dest / f'validation_{method}_{sample}.csv')
            original.compress(xml)
    write_csv(point / 'validation_support.csv', support)
    result = dict(**plan, seconds=time.time() - started, state='validation_reselected_only',
                  original_models_identical=models, support=support,
                  photon_train_sha256=digest(phtrain), photon_validation_sha256=digest(phval),
                  signal_train_sha256=digest(sigtrain), signal_validation_sha256=digest(sigval))
    if input_manifest(point, old, sigtrain, sigval, phtrain, phval,
                      (binary, exporter, rectangles)) != inputs:
        raise RuntimeError('Validation-reselection input changed during execution')
    result.update(resume_manifest_version=1, input_sha256=inputs,
                  output_sha256=output_manifest(point))
    write_json(point / 'validation_reselect_complete.json', result)
    print(json.dumps(dict(state=result['state'], point=str(point), seconds=result['seconds']), indent=2))


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--point', type=Path, required=True)
    p.add_argument('--original-point', type=Path, required=True)
    p.add_argument('--photon-train', type=Path, required=True)
    p.add_argument('--photon-validation', type=Path, required=True)
    p.add_argument('--execute', action='store_true', help='Explicitly run only after repair overlay is ready')
    execute(p.parse_args())


if __name__ == '__main__':
    main()
