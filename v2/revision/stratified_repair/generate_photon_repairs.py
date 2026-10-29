#!/usr/bin/env python3
"""Repair exactly six diagnosed outside-photon samples; preserve all originals."""
from concurrent.futures import ThreadPoolExecutor, as_completed
import csv
import hashlib
import json
import math
from pathlib import Path
import re
import shutil
import subprocess
import time

BASE=Path(__file__).resolve().parent
REV=BASE.parent
ORIGINAL=REV/'stratified_refit'
TASKS=[(4,1.585,'train'),(7,1.585,'train'),(5,1.585,'test'),
       (5,2.512,'test'),(1,5.0,'validation'),(4,6.31,'validation')]

def sha(path):
    h=hashlib.sha256()
    with Path(path).open('rb') as f:
        for block in iter(lambda:f.read(1024*1024),b''):h.update(block)
    return h.hexdigest()

def atomic(path,value):
    tmp=path.with_suffix(path.suffix+'.tmp')
    tmp.write_text(json.dumps(value,indent=2)+'\n');tmp.replace(path)

def label(m):return f'm{m:.3f}'.replace('.','p')

def job(rep,mass,split):
    if shutil.disk_usage(BASE).free<15*1024**3:
        raise RuntimeError('Below 15 GiB reserve; no new repair generation')
    olddir=ORIGINAL/'data'/f'rep_{rep:03d}'/label(mass)
    oldroot=olddir/f'{split}_outside.root';oldmarker=olddir/f'{split}_outside.json'
    previous=json.loads(oldmarker.read_text())
    if sha(oldroot)!=previous['file_sha256']:raise RuntimeError('Original checksum mismatch '+str(oldroot))
    dst=BASE/'data'/f'rep_{rep:03d}'/label(mass);dst.mkdir(parents=True,exist_ok=True)
    root=dst/f'{split}_outside.root';marker=dst/f'{split}_outside.json'
    binary=BASE/'bin/generate_photon_lab'
    source=BASE/'src/generate_photon_lab.cpp'
    args=list(map(str,[binary,'--mass',1e-6,'--cut-mass',mass,'--coupling',.3028221209,
        '--events',previous['attempts'],'--cells',previous['cells'],'--samples',previous['samples'],
        '--seed',previous['seed'],'--photon-region','outside','--integrate-paper-cut',
        '--fold-phi','--log-electron-energy','--quiet','--output',root]))
    signature=hashlib.sha256((json.dumps(args)+sha(binary)+previous['file_sha256']).encode()).hexdigest()
    if marker.exists():
        saved=json.loads(marker.read_text())
        if saved['signature']!=signature or not root.exists() or sha(root)!=saved['file_sha256']:
            raise RuntimeError('Incompatible retained repair '+str(root))
        return saved
    if root.exists():raise RuntimeError('Unmarked repair already exists; preserve for inspection '+str(root))
    started=time.time()
    atomic(dst/f'{split}_outside.command.json',dict(arguments=args,signature=signature,
        original_root=str(oldroot),original_root_sha256=previous['file_sha256'],
        source_sha256=sha(source),binary_sha256=sha(binary),max_concurrent_generation=4))
    logpath=dst/f'{split}_outside.log'
    with logpath.open('w') as f:
        f.write(json.dumps(args)+'\n');f.flush()
        subprocess.run(args,stdout=f,stderr=subprocess.STDOUT,check=True)
    log=logpath.read_text()
    rate=re.search(r'sigma_total_pb=([0-9eE.+-]+) \+/- ([0-9eE.+-]+)',log)
    entries=re.search(r'accepted_events=(\d+)',log)
    features=re.search(r'mirror_max_feature_relative_difference=([0-9eE.+-]+)',log)
    if not rate or not entries or int(entries[1])<1000:raise RuntimeError('Insufficient support '+str(root))
    if not features or float(features[1])!=0:raise RuntimeError('Mirror feature invariance failed '+str(root))
    if not(float(rate[1])>0 and float(rate[2])>0):raise RuntimeError('Invalid rate '+str(root))
    pilots=json.loads((REV/'rate_benchmark/support_integrations.json').read_text())
    same=next(r for r in pilots if r['route']=='transformed_lab' and r['seed']==previous['seed'] and r['mass_GeV']==mass)
    validation_args=list(map(str,[BASE/'bin/validate_signed_photon',root,same['root_path'],olddir/f'{split}_central.root']))
    checked=subprocess.run(validation_args,text=True,capture_output=True)
    (dst/f'{split}_outside.validation.stdout').write_text(checked.stdout)
    (dst/f'{split}_outside.validation.stderr').write_text(checked.stderr)
    if checked.returncode:raise RuntimeError('Signed/schema validation failed '+str(root)+': '+checked.stderr)
    validation=json.loads(checked.stdout)
    with (REV/'rate_benchmark/support_group_summary.csv').open() as handle:
        independent=next(r for r in csv.DictReader(handle) if r['route']=='independent_lab' and float(r['mass_GeV'])==mass)
    pilot_mean=float(independent['mean_rate_pb'])
    pilot_error=max(float(independent['seed_sem_pb']),float(independent['quadrature_mean_error_pb']))
    pilot_z=(float(rate[1])-pilot_mean)/math.hypot(float(rate[2]),pilot_error)
    validation.update(independent_pilot_mean_pb=pilot_mean,independent_pilot_sem_pb=pilot_error,
        independent_pilot_offset_percent=100*(float(rate[1])/pilot_mean-1),
        independent_pilot_comparison_z=pilot_z)
    if abs(pilot_z)>6:raise RuntimeError('Large numerical discrepancy from independent pilot '+str(root))
    atomic(dst/f'{split}_outside.validation.json',dict(**validation,arguments=validation_args,
        folded_pilot_sha256=sha(same['root_path']),central_schema_sha256=sha(olddir/f'{split}_central.root')))
    row=dict(rep=rep,mass_GeV=mass,split=split,region='outside',seed=previous['seed'],
        attempts=previous['attempts'],cells=previous['cells'],samples=previous['samples'],
        sigma_pb=float(rate[1]),sigma_error_pb=float(rate[2]),entries=int(entries[1]),
        signature=signature,file_sha256=sha(root),seconds=time.time()-started,
        original_file=str(oldroot),original_file_sha256=previous['file_sha256'],
        original_sigma_pb=previous['sigma_pb'],source_sha256=sha(source),binary_sha256=sha(binary),
        command=args,root_path=str(root),folded_pilot_file=same['root_path'],
        independent_pilot_rate_comparison=True,same_seed_folded_equivalence=True,
        mirror_restored=True,validation=validation)
    if sha(oldroot)!=previous['file_sha256']:raise RuntimeError('Original changed during repair')
    atomic(marker,row)
    return row

def main():
    completed=[];errors=[]
    def status(state):atomic(BASE/'photon_generation_status.json',dict(state=state,
        completed=len(completed),total=len(TASKS),errors=errors,updated_unix=time.time()))
    status('running')
    with ThreadPoolExecutor(max_workers=4) as pool:
        pending={pool.submit(job,*task):task for task in TASKS}
        for future in as_completed(pending):
            try:
                row=future.result();completed.append(row)
                print(f"Validated {len(completed)}/6: {row['mass_GeV']} rep{row['rep']} {row['split']} sigma={row['sigma_pb']}",flush=True)
            except Exception as e:
                errors.append(dict(task=pending[future],error=str(e)));print('FAILED '+json.dumps(errors[-1]),flush=True)
            status('running')
    atomic(BASE/'photon_replacement_integrations.json',completed)
    status('complete' if not errors else 'failed')
    if errors:raise SystemExit(1)

if __name__=='__main__':main()
