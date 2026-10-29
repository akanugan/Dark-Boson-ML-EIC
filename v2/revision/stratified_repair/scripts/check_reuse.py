#!/usr/bin/env python3
"""Audit the 208 reused and 12 corrected paired analyses before aggregation.

Reads hashes/metadata; never fits, selects, generates events, or changes the old
study. Mixed gate ancestry is intentional and is explicitly recorded. This is
a correction after earlier tests were inspected, not a new blinded confirmation.
"""

import argparse
import csv
import gzip
import hashlib
import json
from pathlib import Path
import tempfile
import time


FEATURES = ('electron', 'electron_qa2')
METHOD_TAGS = {'bdt': 'BDTG', 'likelihood': 'PDERS'}
METHOD_PROFILES = {'bdt': ('depth2', 'depth3', 'depth4', 'depth3_800'),
                   'likelihood': ('h02', 'h04', 'h08', 'h16')}
MASSES = (.01, .032, .1, .316, 1., 1.585, 2.512, 3.981, 5., 6.31, 10.)
TYPES = ('scalar', 'vector')
CORRECTED_SPLITS = {
    (4, 1.585): 'train', (7, 1.585): 'train',
    (1, 5.): 'validation', (4, 6.31): 'validation',
    (5, 1.585): 'test', (5, 2.512): 'test',
}
CACHE_FILES = (
    'analysis_complete.json', 'nominal_RZ.npy', 'bootstrap_RZ.npy',
    'test_metrics.csv', 'precision_estimate.csv', 'support_diagnostics.csv',
    'scenario_nominal_RZ.npy', 'scenario_bootstrap_RZ.npy',
    'scenario_test_metrics.csv',
)
RATE_KEYS = ('signal_type', 'mass_GeV', 'rep', 'signal_xs_pb',
             'photon_xs_pb', 'dis_xs_pb', 'photon_xs_mc_error_pb')


def read_json(path):
    return json.loads(Path(path).read_text())


def rows(path):
    with Path(path).open(newline='') as stream:
        return list(csv.DictReader(stream))


def point_path(rep, typ, mass):
    return Path('fits') / f'rep_{rep:03d}' / f'{typ}_m{mass:.3f}'.replace('.', 'p')


def expected_sources(point):
    mass_label = point.name.split('_', 1)[1]
    result = {str(point / 'sample_config.json'),
              str(Path('data') / point.parent.name / mass_label / 'test_merge.json')}
    result.update(str(point / f / f'test_{method}_{sample}.csv.gz')
                  for f in FEATURES for method in METHOD_TAGS
                  for sample in ('signal', 'photon'))
    return result


class Hashes:
    def __init__(self):
        self.cache = {}
        self.files = 0
        self.bytes = 0

    def get(self, path):
        path = Path(path).resolve(strict=True)
        before = path.stat()
        key = (str(path), before.st_size, before.st_mtime_ns)
        if key in self.cache:
            return self.cache[key]
        digest = hashlib.sha256()
        with path.open('rb') as stream:
            for chunk in iter(lambda: stream.read(1024 * 1024), b''):
                digest.update(chunk)
        after = path.stat()
        if (before.st_size, before.st_mtime_ns) != (after.st_size, after.st_mtime_ns):
            raise RuntimeError('File changed during audit: ' + str(path))
        self.files += 1
        self.bytes += before.st_size
        self.cache[key] = digest.hexdigest()
        return self.cache[key]


def require(condition, message):
    if not condition:
        raise RuntimeError(message)


def check_marker(marker_path, point, root, expected_gate_hash, hashes):
    meta = read_json(marker_path)
    settings = meta['settings']
    require(settings['gate_sha256'] == expected_gate_hash,
            'Wrong analysis-gate ancestry: ' + str(marker_path))
    signature = hashlib.sha256(json.dumps(settings, sort_keys=True).encode()).hexdigest()
    require(meta['signature'] == signature,
            'Analysis settings/signature mismatch: ' + str(marker_path))
    sources = settings['sources']
    require(set(sources) == expected_sources(point),
            'Unexpected/incomplete analysis source inventory: ' + str(marker_path))
    for relative, digest in sources.items():
        require(hashes.get(root / relative) == digest,
                'Stale analysis input: ' + str(root / relative))
    for name in CACHE_FILES:
        require((marker_path.parent / name).is_file(),
                'Incomplete analysis artifacts: ' + str(marker_path.parent / name))
    return meta


def selected_model_key(root, point, feature, method, gate):
    selection = rows(root / point / feature / f'{method}_selected.csv')
    require(len(selection) == 1, 'Expected exactly one selected-model row: ' + str(point))
    profile = selection[0]['model_profile']
    require(profile and '/' not in profile and profile not in ('.', '..'),
            'Invalid profile identifier: ' + repr(profile))
    prefix = point / feature / method / profile / 'dataset' / 'weights'
    xml = str(prefix / f'TMVAClassification_{METHOD_TAGS[method]}.weights.xml')
    candidates = [key for key in (xml, xml + '.gz') if key in gate['model_sha256']]
    require(len(candidates) == 1,
            'Selected model does not have one unambiguous locked hash: ' + xml)
    return candidates[0]


def xml_content_hash(path):
    path = Path(path)
    if not path.is_file():
        alternate = path.with_suffix('') if path.suffix == '.gz' else Path(str(path) + '.gz')
        require(alternate.is_file(), 'Missing original trained XML: ' + str(path))
        path = alternate
    opener = gzip.open if path.suffix == '.gz' else open
    digest = hashlib.sha256()
    with opener(path, 'rb') as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b''):
            digest.update(chunk)
    return digest.hexdigest()


def numeric_or_equal(left, right):
    try:
        return float(left) == float(right)
    except (TypeError, ValueError):
        return left == right


def atomic_json(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(mode='w', dir=path.parent, delete=False) as stream:
        temporary = Path(stream.name)
        json.dump(value, stream, indent=2, allow_nan=False)
        stream.write('\n')
    temporary.replace(path)


def check_reuse(original, repair, gate_path=None, report_path=None):
    """Return and save the full audit; raise on any failed invariant.

    Call only after the twelve corrected analyses are complete, before aggregate
    summaries are calculated. Defaults write <repair>/reuse_audit.json. Gate
    dictionaries use the original selection_sha256/model_sha256 schema.
    """
    started = time.time()
    original = Path(original).resolve(strict=True)
    repair = Path(repair).resolve(strict=True)
    require(original != repair, 'Repair and original roots must be different')
    gate_path = Path(gate_path) if gate_path else repair / 'fit_protocol_gate.json'
    report_path = Path(report_path) if report_path else repair / 'reuse_audit.json'
    # A checker must never overwrite its original evidence through an output link.
    resolved_report = report_path.resolve()
    require(repair in resolved_report.parents,
            'Audit report must remain inside the versioned repair root')
    hashes = Hashes()
    old_gate_path = original / 'fit_protocol_gate.json'
    old_gate, new_gate = read_json(old_gate_path), read_json(gate_path)
    require(old_gate.get('passed') is True and new_gate.get('passed') is True,
            'Both historical and repair fit gates must have passed')
    old_gate_hash, new_gate_hash = hashes.get(old_gate_path), hashes.get(gate_path)
    require(new_gate_hash != old_gate_hash,
            'Repair requires its own gate/provenance, not a copy of the old gate')
    require(new_gate.get('expected_groups', 22) == 22 and
            new_gate.get('expected_points', 220) == 220,
            'Repair gate has changed the declared nominal scan scope')
    for gate in (old_gate, new_gate):
        require(len(gate['selection_sha256']) == 1320 and len(gate['model_sha256']) == 880,
                'Fit gate must lock all 1320 selected rows and 880 selected model files')
    expected = {point_path(rep, typ, mass)
                for rep in range(1, 11) for typ in TYPES for mass in MASSES}
    corrected = {point_path(rep, typ, mass): split
                 for (rep, mass), split in CORRECTED_SPLITS.items() for typ in TYPES}
    require(len(expected) == 220 and len(corrected) == 12,
            'Internal repair scope is inconsistent')
    for root in (original, repair):
        inventory = {path.parent.relative_to(root)
                     for path in (root / 'fits').glob('rep_*/*/sample_config.json')}
        require(inventory == expected, 'Incomplete/unexpected point inventory: ' + str(root))
    checks = []
    for point in sorted(expected):
        old_point, new_point = original / point, repair / point
        old_cfg = read_json(old_point / 'sample_config.json')
        new_cfg = read_json(new_point / 'sample_config.json')
        for name in RATE_KEYS:
            require(name in old_cfg and name in new_cfg and
                    numeric_or_equal(old_cfg[name], new_cfg[name]),
                    'Input/rate policy changed at ' + str(point) + ': ' + name)
        old_marker = old_point / 'analysis' / 'analysis_complete.json'
        # Check all historical cached sources too: the repair may not mutate them.
        old_meta = check_marker(old_marker, point, original, old_gate_hash, hashes)
        new_marker = new_point / 'analysis' / 'analysis_complete.json'
        mode = corrected.get(point)
        lineage = new_gate_hash if mode else old_gate_hash
        new_meta = check_marker(new_marker, point, repair, lineage, hashes)
        for meta in (old_meta, new_meta):
            require(int(meta['rep']) == int(new_cfg['rep']) and
                    meta['signal_type'] == new_cfg['signal_type'] and
                    float(meta['mass_GeV']) == float(new_cfg['mass_GeV']),
                    'Cached group identity disagrees with point configuration: ' + str(point))
        require({k: v for k, v in old_meta['settings'].items() if k not in ('sources', 'gate_sha256')} ==
                {k: v for k, v in new_meta['settings'].items() if k not in ('sources', 'gate_sha256')},
                'Bootstrap/script/seed/batch settings changed: ' + str(point))
        require(new_meta['axes'] == old_meta['axes'] and
                new_meta['scenario_axes'] == old_meta['scenario_axes'],
                'Paired method/feature/scenario axes changed: ' + str(point))
        if mode:
            require(new_point.resolve() != old_point.resolve() and
                    (new_point / 'analysis').resolve() != (old_point / 'analysis').resolve(),
                    'Corrected outputs alias original writable evidence: ' + str(point))
        else:
            require(old_cfg == new_cfg, 'Reused sample configuration changed: ' + str(point))
            require(new_meta == old_meta, 'Reused analysis metadata changed: ' + str(point))
            for name in CACHE_FILES:
                require(hashes.get(new_point / 'analysis' / name) ==
                        hashes.get(old_point / 'analysis' / name),
                        'Reused cached result changed: ' + str(point / 'analysis' / name))
        used_selection_hashes = {}
        used_model_hashes = {}
        validation_candidate_content_hashes = {}
        for feature in FEATURES:
            for method in ('bdt', 'likelihood', 'cuts'):
                key = str(point / feature / f'{method}_selected.csv')
                old_actual = hashes.get(original / key)
                new_actual = hashes.get(repair / key)
                require(old_gate['selection_sha256'].get(key) == old_actual,
                        'Historical selected row changed: ' + key)
                require(new_gate['selection_sha256'].get(key) == new_actual,
                        'Repair selected row not locked correctly: ' + key)
                if mode is None or mode == 'test':
                    require(old_actual == new_actual,
                            'Fixed/reused selection changed: ' + key)
                used_selection_hashes[key] = new_actual
            for method in METHOD_TAGS:
                old_key = selected_model_key(original, point, feature, method, old_gate)
                new_key = selected_model_key(repair, point, feature, method, new_gate)
                require(hashes.get(original / old_key) == old_gate['model_sha256'][old_key],
                        'Historical selected model changed: ' + old_key)
                new_actual = hashes.get(repair / new_key)
                require(new_actual == new_gate['model_sha256'][new_key],
                        'Repair selected model not locked correctly: ' + new_key)
                if mode is None or mode == 'test':
                    require(old_key == new_key and new_actual == old_gate['model_sha256'][old_key],
                            'Fixed/reused model changed: ' + new_key)
                if mode == 'validation':
                    require(xml_content_hash(repair / new_key) == xml_content_hash(original / new_key),
                            'Validation-only repair retrained a selected model: ' + new_key)
                used_model_hashes[new_key] = new_actual
            if mode == 'validation':
                for method, profiles in METHOD_PROFILES.items():
                    for profile in profiles:
                        candidate = point / feature / method / profile / 'dataset' / 'weights' / (
                            f'TMVAClassification_{METHOD_TAGS[method]}.weights.xml.gz')
                        new_content = xml_content_hash(repair / candidate)
                        require(new_content == xml_content_hash(original / candidate),
                                'Validation-only candidate model was retrained: ' + str(candidate))
                        validation_candidate_content_hashes[str(candidate)] = new_content
        checks.append(dict(point=str(point), correction_split=mode,
                           analysis_gate_sha256=lineage,
                           analysis_signature=new_meta['signature'],
                           source_hashes=new_meta['settings']['sources'],
                           selection_hashes=used_selection_hashes,
                           model_hashes=used_model_hashes,
                           validation_candidate_xml_content_hashes=validation_candidate_content_hashes))
    checker_hash = hashes.get(Path(__file__))
    report = dict(passed=True, original_root=str(original), repair_root=str(repair),
        inventory_points=220, reused_points=208, corrected_points=12,
        corrected_point_scopes={str(p): split for p, split in sorted(corrected.items())},
        selection_files_checked=1320, selected_models_checked=880,
        original_gate_sha256=old_gate_hash, repair_gate_sha256=new_gate_hash,
        mixed_analysis_gate_lineage=True,
        lineage_explanation='208 byte-identical inherited caches retain the original gate; '
                            '12 corrected local caches record the new repair gate. '
                            'All current source hashes and locked selections/models are checked.',
        statistical_scope='Correction after previous final tests were inspected; not a new blinded '
                          'independent confirmation. Ten runs per group and the original '
                          '198-contrast family/settings are retained. This audit addresses the '
                          'six identified support failures, not every possible model or software issue.',
        policy='Original sample-rate/calibration policy unchanged; no new result-dependent stopping rule.',
        files_hashed=hashes.files, bytes_hashed=hashes.bytes,
        seconds=time.time()-started, script_sha256=checker_hash,
        point_checks=checks)
    atomic_json(report_path, report)
    return report


def main():
    default_root = Path(__file__).resolve().parents[2]
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--original', type=Path, default=default_root / 'stratified_refit')
    parser.add_argument('--repair', type=Path, default=default_root / 'stratified_repair')
    parser.add_argument('--gate-file', type=Path)
    parser.add_argument('--report', type=Path)
    args = parser.parse_args()
    result = check_reuse(args.original, args.repair, args.gate_file, args.report)
    print(json.dumps({key: value for key, value in result.items() if key != 'point_checks'}, indent=2))


if __name__ == '__main__':
    main()
