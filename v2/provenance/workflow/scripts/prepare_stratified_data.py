#!/usr/bin/env python3
"""Independent, physically separated photon samples for the corrected refit."""
import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
import csv
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import time

BASE=Path(__file__).resolve().parents[1]
OUT=BASE/'stratified_refit'
MASSES=[.010,.032,.100,.316,1.,1.585,2.512,3.981,5.,6.310,10.]

def label(mass):return f'm{mass:.3f}'.replace('.','p')
def sha(path):
    h=hashlib.sha256()
    with path.open('rb') as f:
        for b in iter(lambda:f.read(1024*1024),b''):h.update(b)
    return h.hexdigest()

def job(rep,mass,split,region):
    reserve_gib=float(os.environ.get('DARK_STUDY_MIN_FREE_GIB','15'))
    if not 10<=reserve_gib<=15:raise RuntimeError('Study free-space reserve must be between 10 and 15 GiB')
    if shutil.disk_usage(OUT).free<reserve_gib*1024**3:
        raise RuntimeError(f'Less than {reserve_gib:g} GiB free; stopped new generation')
    dst=OUT/'data'/f'rep_{rep:03d}'/label(mass)
    dst.mkdir(parents=True,exist_ok=True)
    binary=BASE/'bin'/('generate_photon_regions' if region=='central' else 'generate_photon_lab')
    n,c,s=(100000,2500,1500) if region=='central' else (40000,1000,1000)
    splitid={'calibration':0,'train':1,'validation':2,'test':3}[split]
    seed=521000000+MASSES.index(mass)*100000+rep*1000+splitid*10+(region=='outside')
    root=dst/f'{split}_{region}.root';marker=dst/f'{split}_{region}.json'
    args=list(map(str,[binary,'--mass',1e-6,'--cut-mass',mass,'--coupling',.3028221209,
          '--events',n,'--cells',c,'--samples',s,'--seed',int(seed),'--photon-region',region,
          '--integrate-paper-cut','--quiet','--output',root]))
    signature=hashlib.sha256((json.dumps(args)+sha(binary)).encode()).hexdigest()
    if marker.exists():
        old=json.loads(marker.read_text())
        if old['signature']!=signature or not root.exists():raise RuntimeError('Incompatible existing sample '+str(root))
        return old
    started=time.time()
    with (dst/f'{split}_{region}.log').open('w') as f:
        f.write(json.dumps(args)+'\n');f.flush()
        subprocess.run(args,stdout=f,stderr=subprocess.STDOUT,check=True)
    log=(dst/f'{split}_{region}.log').read_text()
    xs=re.search(r'sigma_total_pb=([0-9eE.+-]+) \+/- ([0-9eE.+-]+)',log)
    entries=re.search(r'accepted_events=(\d+)',log)
    if not xs or not entries or int(entries[1])<1000:raise RuntimeError('Insufficient photon integration support '+str(root))
    if not (float(xs[1])>0 and float(xs[2])>0):raise RuntimeError('Invalid cross section '+str(root))
    row=dict(rep=rep,mass_GeV=mass,split=split,region=region,seed=int(seed),attempts=n,cells=c,samples=s,
             sigma_pb=float(xs[1]),sigma_error_pb=float(xs[2]),entries=int(entries[1]),signature=signature,
             file_sha256=sha(root),seconds=time.time()-started)
    marker.write_text(json.dumps(row,indent=2));return row

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--stage',choices=['pilot','full','test'],required=True)
    args=parser.parse_args();OUT.mkdir(exist_ok=True)
    masses=[.032,10.] if args.stage=='pilot' else MASSES
    reps=range(1,4) if args.stage=='pilot' else range(1,11)
    tasks=[]
    if args.stage!='test':
        tasks.extend((0,m,'calibration',g) for m in masses for g in ['central','outside'])
        tasks.extend((r,m,s,g) for r in reps for m in masses for s in ['train','validation'] for g in ['central','outside'])
    else:tasks.extend((r,m,'test',g) for r in reps for m in masses for g in ['central','outside'])
    completed=[];errors=[]
    def status(state):
        (OUT/f'{args.stage}_generation_status.json').write_text(json.dumps(dict(state=state,completed=len(completed),total=len(tasks),errors=errors),indent=2))
    status('running')
    with ThreadPoolExecutor(max_workers=4) as pool:
        fs={pool.submit(job,*t):t for t in tasks}
        for f in as_completed(fs):
            try:
                row=f.result();completed.append(row)
                print('Generated',len(completed),'/',len(tasks),row['mass_GeV'],row['rep'],row['split'],row['region'],row['sigma_pb'],flush=True)
            except Exception as exc:errors.append(dict(task=fs[f],error=str(exc)));print('ERROR',errors[-1],flush=True)
            status('running')
    (OUT/f'{args.stage}_component_integrations.json').write_text(json.dumps(completed,indent=2))
    status('failed' if errors else 'complete')
    if errors:raise SystemExit(1)

if __name__=='__main__':main()
