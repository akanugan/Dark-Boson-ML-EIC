#!/usr/bin/env python3
"""Replay flagged samples and test exact alternative lab mappings."""

import concurrent.futures
import csv
import json
import time
from run import BASE, atomic_json, digest, job

ROUTES = {'original_lab': ('lab', 'outside', 0),
          'transformed_lab': ('lab_transformed', 'outside', 0),
          'independent_lab': ('lab_transformed', 'outside', 0)}


def main():
    with (BASE.parent/'background_audit/convergence_flags.csv').open() as handle:
        flags = list(csv.DictReader(handle))
    pending=[]
    for index,row in enumerate(flags,1):
        for route in ('original_lab','transformed_lab'):
            pending.append((float(row['mass_GeV']),route,index,int(row['seed'])))
    for index,mass in enumerate((1.585,2.512,5.0,6.31)):
        for rep in (1,2,3):
            pending.append((mass,'independent_lab',rep,1633001+index*10000+(rep-1)*100))
    atomic_json(BASE/'support_environment.json',dict(
        binaries={name:digest(BASE/'bin'/name) for name in ('lab','lab_transformed')},
        protocol_sha256=digest(BASE/'support_protocol.md'),
        flagged_inputs_sha256=digest(BASE.parent/'background_audit/convergence_flags.csv')))
    complete,errors=[],[]

    def status(state):
        atomic_json(BASE/'support_status.json',dict(state=state,completed=len(complete),
            total=len(pending),failures=errors,updated_unix=time.time()))

    def one(mass,route,rep,seed):
        extra=() if route=='original_lab' else ('--fold-phi','--log-electron-energy')
        return job(mass,route,rep,routes=ROUTES,output_root=BASE/'runs_support',
            extra_flags=extra,attempts=40000,cells=1000,samples=1000,seed_override=seed)

    status('running')
    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
        futures={pool.submit(one,*item):item for item in pending}
        for future in concurrent.futures.as_completed(futures):
            try:
                result=future.result();complete.append(result)
                print(f"Completed {len(complete)}/{len(pending)}: {result['mass_GeV']:g} "
                      f"{result['route']} seed{result['seed']} sigma={result['sigma_pb']:.10g}",flush=True)
            except Exception as error:
                item=dict(job=futures[future],error=str(error));errors.append(item)
                print('FAILED '+json.dumps(item),flush=True)
            status('running')
    atomic_json(BASE/'support_integrations.json',complete)
    status('complete' if not errors else 'failed')
    if errors:raise SystemExit(1)


if __name__=='__main__':main()
