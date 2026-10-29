#!/usr/bin/env python3
"""Run the preserved-physics four-route integration comparison, four at once."""

import concurrent.futures
import os
import hashlib
import json
import re
import shutil
import subprocess
import time
from pathlib import Path

BASE = Path(__file__).resolve().parent
REVISION = BASE.parent
ROUTES = {
    'effective_cm': ('historical', 'effective', 833001),
    'central_cm': ('central', 'central', 933001),
    'outside_cm': ('historical', 'forward', 1033001),
    'outside_lab': ('lab', 'outside', 1133001),
}


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def atomic_json(path, value):
    temporary = path.with_suffix(path.suffix + '.tmp')
    temporary.write_text(json.dumps(value, indent=2) + '\n')
    temporary.replace(path)


def preserve(source, destination):
    destination.parent.mkdir(parents=True, exist_ok=True)
    if destination.exists():
        if digest(destination) != digest(source):
            raise ValueError(f'Preserved source changed: {destination}')
    else:
        shutil.copy2(source, destination)


def job(mass, route, replicate, *, routes=ROUTES, output_root=None, extra_flags=(),
        attempts=250000, cells=2500, samples=1200, seed_override=None):
    binary_key, region, seed_base = routes[route]
    binary = BASE / 'bin' / binary_key
    seed = seed_override if seed_override is not None else seed_base + (replicate - 1) * 100
    output_root = output_root or BASE / 'runs'
    directory = output_root / ('m' + f'{mass:.3f}'.replace('.', 'p')) / route / f'rep_{replicate:03d}'
    directory.mkdir(parents=True, exist_ok=True)
    args = [str(binary), '--mass', '0.000001', '--cut-mass', str(mass),
            '--coupling', '0.3028221209', '--events', str(attempts),
            '--cells', str(cells), '--samples', str(samples), '--seed', str(seed),
            '--integrate-paper-cut', '--photon-region', region, '--quiet',
            '--output', str(directory / 'events.root'), *extra_flags]
    signature = hashlib.sha256((json.dumps(args) + digest(binary)).encode()).hexdigest()
    marker = directory / 'result.json'
    if marker.exists():
        previous = json.loads(marker.read_text())
        if previous['signature'] != signature:
            raise ValueError(f'Changed command for existing result: {marker}')
        if not (directory / 'events.root').exists():
            raise ValueError(f'Missing saved events: {directory}')
        return previous
    if shutil.disk_usage(BASE).free < 15 * 1024**3:
        raise RuntimeError('15 GiB free-space safeguard')
    started = time.time()
    atomic_json(directory / 'command.json', dict(args=args, signature=signature, started_unix=started))
    with (directory / 'run.log').open('w') as handle:
        handle.write(json.dumps(args) + '\n')
        handle.flush()
        subprocess.run(args, stdout=handle, stderr=subprocess.STDOUT, check=True)
    log = (directory / 'run.log').read_text()
    integral = re.search(r'^sigma_total_pb=([0-9eE.+-]+) \+/- ([0-9eE.+-]+)', log, re.MULTILINE)
    count = re.search(r'^accepted_events=(\d+)', log, re.MULTILINE)
    if not integral or not count:
        raise ValueError(f'Incomplete integration output: {directory}')
    result = dict(mass_GeV=mass, route=route, replicate=replicate, seed=seed,
                  attempts=attempts, cells=cells, samples=samples,
                  sigma_pb=float(integral[1]), sigma_error_pb=float(integral[2]),
                  entries=int(count[1]), seconds=time.time()-started,
                  signature=signature, root_path=str(directory / 'events.root'),
                  root_sha256=digest(directory / 'events.root'))
    atomic_json(marker, result)
    return result


def main():
    # The public archive already contains the exact source variants. Build them
    # locally; do not fetch an author-specific legacy executable or rewrite it.
    required = [BASE / 'bin' / ROUTES[route][0] for route in ROUTES]
    missing = [str(path) for path in required if not path.is_file()]
    if missing:
        raise FileNotFoundError('Run revision/build.sh --benchmarks first: ' + ', '.join(missing))
    root_version = subprocess.check_output(
        [os.environ.get('ROOT_CONFIG', 'root-config'), '--version'], text=True).strip()
    atomic_json(BASE / 'environment.json', dict(root_version=root_version,
                sources={str(p.relative_to(BASE)): digest(p) for p in sorted((BASE / 'sources').glob('*'))},
                binaries={p.name: digest(p) for p in sorted((BASE / 'bin').glob('*'))}))
    pending = [(mass, route, rep) for route in ROUTES for mass in (0.032, 10.0) for rep in (1, 2, 3)]
    complete, errors = [], []

    def status(state):
        atomic_json(BASE / 'status.json', dict(state=state, completed=len(complete), total=len(pending),
                    failures=errors, updated_unix=time.time()))

    status('running')
    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
        futures = {pool.submit(job, *item): item for item in pending}
        for future in concurrent.futures.as_completed(futures):
            try:
                result = future.result()
                complete.append(result)
                print(f"Completed {len(complete)}/{len(pending)}: "
                      f"{result['mass_GeV']:g} {result['route']} rep{result['replicate']} "
                      f"sigma={result['sigma_pb']:.10g} +/- {result['sigma_error_pb']:.4g}", flush=True)
            except Exception as error:
                item = dict(job=futures[future], error=str(error))
                errors.append(item)
                print('FAILED ' + json.dumps(item), flush=True)
            status('running')
    atomic_json(BASE / 'integrations.json', complete)
    status('complete' if not errors else 'failed')
    if errors:
        raise SystemExit(1)


if __name__ == '__main__':
    main()
