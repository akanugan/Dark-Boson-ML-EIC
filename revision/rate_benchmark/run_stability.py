#!/usr/bin/env python3
"""Increase numerical budgets and check regulator independence; four workers."""
import concurrent.futures
import time
from run import BASE, atomic_json, digest, job

ROUTES = {
    'central_cm_large': ('cm_focused', 'central', 1933001),
    'outside_lab_large': ('lab_transformed', 'outside', 2033001),
    'central_cm_regulator': ('cm_focused', 'central', 2133001),
    'outside_lab_regulator': ('lab_transformed', 'outside', 2233001),
}

def main():
    atomic_json(BASE/'stability_environment.json', dict(
        binaries={key:digest(BASE/'bin'/key) for key in ('cm_focused','lab_transformed')},
        protocol_sha256=digest(BASE/'stability_protocol.md')))
    pending=[(m,r,k) for r in ROUTES for m in (.032,10.) for k in (1,2,3)]
    complete,errors=[],[]
    def status(state):
        atomic_json(BASE/'stability_status.json', dict(state=state,completed=len(complete),
            total=len(pending),failures=errors,updated_unix=time.time()))
    def one(mass,route,rep):
        flags=['--fold-phi']
        if route.startswith('central'):
            flags+=['--log-pair-mass','--t-importance-center','0.0001','--t-importance-width','3']
        else:
            flags+=['--log-electron-energy']
        if route.endswith('regulator'):
            flags+=['--mass','0.0000001']
        return job(mass,route,rep,routes=ROUTES,output_root=BASE/'runs_stability',
            extra_flags=flags,attempts=1000000,cells=5000,samples=2000)
    status('running')
    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
        futures={pool.submit(one,*item):item for item in pending}
        for future in concurrent.futures.as_completed(futures):
            try:
                result=future.result();complete.append(result)
                factor=1e-6 if result['route'].startswith('central') else 1.
                print(f"Completed {len(complete)}/{len(pending)}: {result['mass_GeV']:g} "
                      f"{result['route']} rep{result['replicate']} effective_pb={factor*result['sigma_pb']:.10g}",flush=True)
            except Exception as error:
                item=dict(job=futures[future],error=str(error));errors.append(item)
                print('FAILED '+str(item),flush=True)
            status('running')
    atomic_json(BASE/'stability_integrations.json',complete)
    status('complete' if not errors else 'failed')
    if errors:raise SystemExit(1)

if __name__=='__main__':main()
