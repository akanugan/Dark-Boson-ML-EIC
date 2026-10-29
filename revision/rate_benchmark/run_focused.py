#!/usr/bin/env python3
"""Test a full-domain t importance map against independent lab integration."""

import concurrent.futures
import time
from run import BASE, atomic_json, digest, job

ROUTES={'central_cm_focused':('cm_focused','central',1733001),
        'outside_cm_focused':('cm_focused','forward',1833001)}


def main():
    atomic_json(BASE/'focused_environment.json',dict(
        binary_sha256=digest(BASE/'bin/cm_focused'),
        source_sha256=digest(BASE/'sources/cm_focused.cpp'),
        protocol_sha256=digest(BASE/'focused_protocol.md')))
    pending=[(mass,route,rep) for route in ROUTES for mass in(.032,10.) for rep in(1,2,3)]
    complete,errors=[],[]

    def status(state):
        atomic_json(BASE/'focused_status.json',dict(state=state,completed=len(complete),
            total=len(pending),failures=errors,updated_unix=time.time()))

    def one(mass,route,rep):
        center,width=('0.0001','3') if route.startswith('central') else ('0.1','1.5')
        return job(mass,route,rep,routes=ROUTES,output_root=BASE/'runs_focused',
            extra_flags=('--log-pair-mass','--fold-phi','--t-importance-center',center,
                         '--t-importance-width',width))

    status('running')
    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
        futures={pool.submit(one,*item):item for item in pending}
        for future in concurrent.futures.as_completed(futures):
            try:
                result=future.result();complete.append(result)
                print(f"Completed {len(complete)}/{len(pending)}: {result['mass_GeV']:g} "
                      f"{result['route']} rep{result['replicate']} sigma={result['sigma_pb']:.10g}",flush=True)
            except Exception as error:
                item=dict(job=futures[future],error=str(error));errors.append(item)
                print('FAILED '+str(item),flush=True)
            status('running')
    atomic_json(BASE/'focused_integrations.json',complete)
    status('complete' if not errors else 'failed')
    if errors:raise SystemExit(1)


if __name__=='__main__':main()
