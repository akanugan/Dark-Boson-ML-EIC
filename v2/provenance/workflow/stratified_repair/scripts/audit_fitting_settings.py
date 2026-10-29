#!/usr/bin/env python3
"""Read-only comparison of repair fitting commands against historical commands."""
import csv
import gzip
import hashlib
import json
from pathlib import Path
import time

ROOT = Path(__file__).resolve().parents[1]
OLD = ROOT.parent / 'stratified_refit'
HASHES = {}


def sha(path):
    path = Path(path).resolve(strict=True)
    stamp = path.stat()
    key = (str(path), stamp.st_size, stamp.st_mtime_ns)
    if key not in HASHES:
        h = hashlib.sha256()
        with path.open('rb') as stream:
            for chunk in iter(lambda: stream.read(1048576), b''):
                h.update(chunk)
        after = path.stat()
        if (stamp.st_size, stamp.st_mtime_ns) != (after.st_size, after.st_mtime_ns):
            raise RuntimeError('Input changed during audit: ' + str(path))
        HASHES[key] = h.hexdigest()
    return HASHES[key]


def load(path):
    return json.loads(Path(path).read_text())


def require(value, message):
    if not value:
        raise RuntimeError(message)


def original_command(marker):
    saved = load(marker)
    expected = hashlib.sha256((json.dumps(saved['arguments']) + sha(saved['arguments'][0])).encode()).hexdigest()
    require(expected == saved['signature'], 'Historical/current executable signature mismatch: ' + str(marker))
    return saved


def same_args(old_args, new_args, label):
    normalized = [x.replace(str(ROOT), str(OLD)) for x in new_args]
    require(old_args == normalized, 'Fitting parameter/path mapping changed: ' + label)


def raw_xml_hash(path):
    opener = gzip.open if path.suffix == '.gz' else open
    h = hashlib.sha256()
    with opener(path, 'rb') as stream:
        for chunk in iter(lambda: stream.read(1048576), b''):
            h.update(chunk)
    return h.hexdigest()


def main():
    start = time.time()
    inventory = load(ROOT / 'inventory.json')['affected']
    train, validation, pending = [], [], []
    for row in inventory:
        if row['split'] not in ('train', 'validation'):
            continue
        before, after = Path(row['old_point']), Path(row['new_point'])
        cfg_old, cfg_new = load(before / 'sample_config.json'), load(after / 'sample_config.json')
        require(cfg_old == cfg_new, 'Sample/rate configuration changed: ' + str(after))
        signals = {}
        original_fit = load(before / 'fit_complete.json')
        for split in ('train', 'validation', 'test'):
            a, b = before / 'data' / f'signal_{split}.root', after / 'data' / f'signal_{split}.root'
            require(a.resolve(strict=True) == b.resolve(strict=True), 'Original signal identity changed: ' + str(b))
            digest = sha(a)
            if split in ('train', 'validation'):
                require(original_fit['signal_' + split + '_sha256'] == digest,
                        'Signal content differs from historical fitting record: ' + str(a))
            signals[split] = dict(resolved_path=str(a.resolve()), sha256=digest)
        result = dict(point=str(after.relative_to(ROOT)), split=row['split'], signals=signals,
                      exact_sample_configuration=True, commands=[])
        if row['split'] == 'train':
            require((after / 'fit_complete.json').is_file(), 'Training repair incomplete: ' + str(after))
            markers = sorted(before.glob('*/*/*/trained.json')) + sorted(before.glob('*/boxes/*.done.json'))
            require(len(markers) == 22, 'Wrong original candidate command count')
            for marker in markers:
                relative = marker.relative_to(before)
                old, new = original_command(marker), original_command(after / relative)
                same_args(old['arguments'], new['arguments'], str(after / relative))
                a, b = old['arguments'], new['arguments']
                trained = relative.name == 'trained.json'
                unchanged = (1, 2, 4) if trained else (1, 3, 4, 5, 6)
                changed = 3 if trained else 2
                for index in unchanged:
                    require(Path(a[index]).resolve() == Path(b[index]).resolve(), 'Unchanged input path changed: ' + str(relative))
                    require(sha(a[index]) == sha(b[index]), 'Unchanged input content changed')
                require(sha(a[changed]) != sha(b[changed]), 'Repaired training photons were not substituted')
                result['commands'].append(dict(marker=str(relative), executable_sha256=sha(a[0]),
                    parameter_strings_identical=True, random_seed=a[-2] if trained else a[-1],
                    changed_input_sha256=dict(original=sha(a[changed]), repaired=sha(b[changed])),
                    original_signature=old['signature'], repair_signature=new['signature']))
            train.append(result)
        else:
            completed = after / 'validation_reselect_complete.json'
            if not completed.exists():
                pending.append(str(after.relative_to(ROOT)))
                continue
            meta = load(completed)
            for feature in ('electron', 'electron_qa2'):
                for q in (40, 80, 160):
                    relative = Path(feature) / 'boxes' / f'q{q}.done.json'
                    old = original_command(before / relative)
                    repaired = after / feature / 'boxes' / f'q{q}.repair.done.json'
                    new = load(repaired)
                    same_args(old['arguments'], new['arguments'], str(repaired))
                    provenance = {name: new[name] for name in ('arguments', 'executable_sha256', 'input_sha256')}
                    require(hashlib.sha256(json.dumps(provenance, sort_keys=True).encode()).hexdigest() == new['signature'], 'Repaired command provenance signature mismatch')
                    require(new['executable_sha256'] == sha(old['arguments'][0]), 'Rectangular optimizer binary changed')
                    for source, digest in new['input_sha256'].items():
                        require(sha(source) == digest, 'Validation command input changed: ' + source)
                    a, b = old['arguments'], new['arguments']
                    for index in (1, 2, 3, 5):
                        require(sha(a[index]) == sha(b[index]), 'Validation repair changed training or signal input')
                    for index in (4, 6):
                        require(sha(a[index]) != sha(b[index]), 'New validation photons not substituted')
                    result['commands'].append(dict(marker=str(repaired.relative_to(after)),
                        executable_sha256=sha(a[0]), parameter_strings_identical=True,
                        random_seed=a[-1], original_signature=old['signature'], repair_signature=new['signature']))
                for method, tag, profiles in (
                    ('bdt', 'BDTG', ('depth2', 'depth3', 'depth4', 'depth3_800')),
                    ('likelihood', 'PDERS', ('h02', 'h04', 'h08', 'h16'))):
                    for profile in profiles:
                        relative = Path(feature) / method / profile / 'dataset' / 'weights' / f'TMVAClassification_{tag}.weights.xml.gz'
                        require(raw_xml_hash(before / relative) == raw_xml_hash(after / relative), 'Validation repair retrained a candidate XML')
            for source, digest in meta['input_sha256'].items():
                require(sha(source) == digest, 'Completed validation reselection input changed')
            validation.append(result)
    require(len(train) == 4, 'Expected all four training repairs complete')
    report = dict(passed=True, state='complete' if len(validation) == 4 else 'training_verified_validation_pending',
        training_points=4, training_model_commands=64, training_rectangular_commands=24,
        validation_points_checked=len(validation), validation_rectangular_commands=6 * len(validation),
        pending_validation_points=pending, training_audits=train, validation_audits=validation,
        interpretation='Exactly the original fitting parameters, profiles, seeds and executable bytes. '
                       'Original signals are identical. Only the diagnosed photon split and output paths change. '
                       'For each completed validation-only repair, original trained XML contents and rectangular settings are also verified. ',
        script_sha256=sha(Path(__file__)), seconds=time.time() - start)
    path = ROOT / 'fitting_settings_audit.json'
    temporary = path.with_suffix('.json.tmp')
    temporary.write_text(json.dumps(report, indent=2) + '\n')
    temporary.replace(path)
    print(json.dumps({k: v for k, v in report.items() if not k.endswith('_audits')}, indent=2))


if __name__ == '__main__':
    main()
