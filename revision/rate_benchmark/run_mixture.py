#!/usr/bin/env python3
"""Fresh adaptive CM joint-proposal check, four simultaneous jobs maximum."""
import concurrent.futures
import hashlib
import json
import shutil
import subprocess
import time
from run import BASE, atomic_json, digest, job

ROUTES={'outside_cm_mixture':('cm_mixture','forward',2333001)}

def iid_job(mass,route,rep):
    binary=BASE/'bin/cm_mixture_iid'
    seed=2433001+100*(rep-1)
    directory=BASE/'runs_mixture'/('m'+f'{mass:.3f}'.replace('.','p'))/route/f'rep_{rep:03d}'
    directory.mkdir(parents=True,exist_ok=True)
    box='.74,.81,.02,.12,.08,.45,0,.25' if mass<1 else '.74,.81,.06,.70,0,.09,0,.25'
    args=[str(binary),'--mass','0.000001','--cut-mass',str(mass),'--coupling','0.3028221209',
          '--events','2000000','--seed',str(seed),'--integrate-paper-cut',
          '--photon-region','forward','--fold-phi','--cm-box',box,
          '--cm-box-probability','0.75','--quiet','--rate-json',str(directory/'rate.json')]
    signature=hashlib.sha256((json.dumps(args)+digest(binary)).encode()).hexdigest()
    marker=directory/'result.json'
    if marker.exists():
        result=json.loads(marker.read_text())
        if result['signature']!=signature:raise ValueError('Changed saved IID command')
        return result
    if shutil.disk_usage(BASE).free<15*1024**3:raise RuntimeError('15 GiB safeguard')
    started=time.time()
    atomic_json(directory/'command.json',dict(args=args,signature=signature,started_unix=started))
    with (directory/'run.log').open('w') as handle:
        handle.write(json.dumps(args)+'\n');handle.flush()
        subprocess.run(args,stdout=handle,stderr=subprocess.STDOUT,check=True)
    rate=json.loads((directory/'rate.json').read_text())
    result=dict(mass_GeV=mass,route=route,replicate=rep,seed=seed,attempts=rate['attempts'],
        cells=0,samples=0,sigma_pb=rate['sigma_total_pb'],sigma_error_pb=rate['sigma_total_error_pb'],
        entries=rate['positive_points'],seconds=time.time()-started,signature=signature,
        root_path='',root_sha256='')
    atomic_json(marker,result)
    return result

def main():
    atomic_json(BASE/'mixture_environment.json',dict(
        binary_sha256=digest(BASE/'bin/cm_mixture'),
        iid_binary_sha256=digest(BASE/'bin/cm_mixture_iid'),
        iid_source_sha256=digest(BASE/'sources/cm_mixture_iid.cpp'),
        source_sha256=digest(BASE/'sources/cm_mixture.cpp'),
        protocol_sha256=digest(BASE/'mixture_protocol.md')))
    pending=[(m,route,r) for route in ('outside_cm_mixture','outside_cm_iid')
             for m in(.032,10.) for r in(1,2,3)]
    complete,errors=[],[]
    def status(state):
        atomic_json(BASE/'mixture_status.json',dict(state=state,completed=len(complete),
            total=len(pending),failures=errors,updated_unix=time.time()))
    def one(mass,route,rep):
        if route=='outside_cm_iid':return iid_job(mass,route,rep)
        box='.74,.81,.02,.12,.08,.45,0,.25' if mass<1 else '.74,.81,.06,.70,0,.09,0,.25'
        return job(mass,route,rep,routes=ROUTES,output_root=BASE/'runs_mixture',
            extra_flags=('--fold-phi','--cm-box',box,'--cm-box-probability','0.75'))
    status('running')
    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
        futures={pool.submit(one,*item):item for item in pending}
        for future in concurrent.futures.as_completed(futures):
            try:
                result=future.result();complete.append(result)
                print(f"Completed {len(complete)}/{len(pending)}: {result['mass_GeV']:g} "
                      f"{result['route']} rep{result['replicate']} outside_pb={result['sigma_pb']:.10g} "
                      f"+/- {result['sigma_error_pb']:.4g}",flush=True)
            except Exception as error:
                item=dict(job=futures[future],error=str(error));errors.append(item)
                print('FAILED '+str(item),flush=True)
            status('running')
    atomic_json(BASE/'mixture_integrations.json',complete)
    status('complete' if not errors else 'failed')
    if errors:raise SystemExit(1)

if __name__=='__main__':main()
