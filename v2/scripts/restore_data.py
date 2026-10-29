#!/usr/bin/env python3
"""Verify the published model/analysis package and restore it under results/."""
import argparse
import hashlib
import json
from pathlib import Path, PurePosixPath
import tarfile
import tempfile

BASE = Path(__file__).resolve().parents[1]
RECORDS = BASE / 'provenance/workflow'
ARCHIVE_ROOT = PurePosixPath('revision/stratified_repair')


def digest(path):
    value = hashlib.sha256()
    with path.open('rb') as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b''):
            value.update(chunk)
    return value.hexdigest()


def checksums(path):
    values = {}
    for line in path.read_text().splitlines():
        value, name = line.split(None, 1)
        name = name.lstrip(' *')
        if len(value) != 64 or name in values:
            raise ValueError('Invalid checksum record: ' + line)
        values[name] = value
    return values


def restore(downloads, destination):
    downloads = downloads.resolve()
    destination = destination.resolve()
    recorded_sums = RECORDS / 'RELEASE_SHA256SUMS'
    if (downloads / 'SHA256SUMS').read_bytes() != recorded_sums.read_bytes():
        raise ValueError('Downloaded SHA256SUMS differs from the recorded release')
    for name, expected in checksums(recorded_sums).items():
        path = downloads / name
        if not path.is_file() or digest(path) != expected:
            raise ValueError('Missing or incorrect release asset: ' + name)
    expected_files = checksums(downloads / 'FILES_SHA256SUMS')
    release = json.loads((RECORDS / 'release.json').read_text())
    seen = set()
    destination.mkdir(parents=True, exist_ok=True)
    for archive in release['archives']:
        with tarfile.open(downloads / archive['name'], 'r:gz') as stream:
            for member in stream:
                if member.isdir():
                    continue
                if not member.isfile() or member.name not in expected_files or member.name in seen:
                    raise ValueError('Unexpected archive member: ' + member.name)
                original = PurePosixPath(member.name)
                if '..' in original.parts or original.is_absolute():
                    raise ValueError('Unsafe archive path: ' + member.name)
                relative = original.relative_to(ARCHIVE_ROOT)
                # Keep the public study guide; retain the release's README separately.
                target = (downloads / 'import-records/README.md' if relative == PurePosixPath('README.md')
                          else destination / str(relative))
                allowed = downloads if relative == PurePosixPath('README.md') else destination
                if not target.resolve().is_relative_to(allowed):
                    raise ValueError('Destination escapes the import directory: ' + str(target))
                target.parent.mkdir(parents=True, exist_ok=True)
                value = hashlib.sha256()
                temporary = None
                try:
                    with tempfile.NamedTemporaryFile(dir=target.parent, delete=False) as output:
                        temporary = Path(output.name)
                        with stream.extractfile(member) as source:
                            for chunk in iter(lambda: source.read(1024 * 1024), b''):
                                value.update(chunk)
                                output.write(chunk)
                    if value.hexdigest() != expected_files[member.name]:
                        raise ValueError('Incorrect member checksum: ' + member.name)
                    temporary.replace(target)
                finally:
                    if temporary is not None:
                        temporary.unlink(missing_ok=True)
                seen.add(member.name)
        print('Imported', archive['name'], flush=True)
    if seen != set(expected_files):
        raise ValueError('Release import incomplete')
    report = {'verified_files': len(seen), 'destination': str(destination),
              'archive_root': str(ARCHIVE_ROOT), 'release': release['release']}
    (downloads / 'import-records').mkdir(exist_ok=True)
    (downloads / 'import-records/import.json').write_text(json.dumps(report, indent=2) + '\n')
    print('Verified and restored', len(seen), 'files to', destination)
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--downloads', type=Path, default=BASE / 'downloads')
    parser.add_argument('--destination', type=Path, default=BASE / 'results')
    args = parser.parse_args()
    restore(args.downloads, args.destination)


if __name__ == '__main__':
    main()
