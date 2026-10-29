#!/usr/bin/env python3
"""Run the prespecified exact-coordinate diagnostic stage, four jobs at once."""

import concurrent.futures
import json
import time
from pathlib import Path
from run import BASE, atomic_json, digest, job

ROUTES = {
    'effective_cm_logfold': ('cm_transformed', 'effective', 1233001),
    'central_cm_logfold': ('cm_transformed', 'central', 1333001),
    'outside_cm_logfold': ('cm_transformed', 'forward', 1433001),
    'outside_lab_logfold': ('lab_transformed', 'outside', 1533001),
}


def main():
    for binary in ('cm_transformed', 'lab_transformed'):
        if not (BASE / 'bin' / binary).exists():
            raise FileNotFoundError(binary)
    atomic_json(BASE / 'transformed_environment.json', {
        'binaries': {name: digest(BASE / 'bin' / name)
                     for name in ('cm_transformed', 'lab_transformed')},
        'sources': {name: digest(BASE / 'sources' / name)
                    for name in ('cm_transformed.cpp', 'lab_transformed.cpp')},
        'protocol_sha256': digest(BASE / 'transformed_protocol.md'),
    })
    pending = [(mass, route, rep) for route in ROUTES
               for mass in (0.032, 10.0) for rep in (1, 2, 3)]
    complete, errors = [], []

    def status(state):
        atomic_json(BASE / 'transformed_status.json', dict(
            state=state, completed=len(complete), total=len(pending),
            failures=errors, updated_unix=time.time()))

    def one(mass, route, rep):
        flags = ['--fold-phi', '--log-electron-energy'] if 'lab' in route else ['--fold-phi', '--log-pair-mass']
        return job(mass, route, rep, routes=ROUTES,
                   output_root=BASE / 'runs_transformed', extra_flags=flags)

    status('running')
    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
        futures = {pool.submit(one, *item): item for item in pending}
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
    atomic_json(BASE / 'transformed_integrations.json', complete)
    status('complete' if not errors else 'failed')
    if errors:
        raise SystemExit(1)


if __name__ == '__main__':
    main()
