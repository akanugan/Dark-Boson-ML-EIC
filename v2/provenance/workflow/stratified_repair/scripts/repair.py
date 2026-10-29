#!/usr/bin/env python3
"""Complete the bounded six-file correction without modifying prior results."""
import os
for key in ('OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','VECLIB_MAXIMUM_THREADS'):
    os.environ[key]='1'
import argparse
from concurrent.futures import ThreadPoolExecutor,as_completed
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import time

ROOT=Path(__file__).resolve().parents[1]
REV=ROOT.parent
OLD=REV/'stratified_refit'
sys.path.insert(0,str(REV/'scripts'))
import run_stratified_refit as fit
import continue_stratified_study as evaluation
import analyze_stratified_refit as analysis

fit.OUT=ROOT
evaluation.OUT=ROOT
START=time.time()

def status(phase,**extra):
    fit.atomic_json(ROOT/'study_status.json',dict(phase=phase,started=START,
        updated=time.time(),pid=os.getpid(),**extra))
    print('PHASE',phase,json.dumps(extra),flush=True)

def signals(point,rep,typ,mass,split):
    target=point/'data'/f'signal_{split}.root'
    source=OLD/'fits'/f'rep_{rep:03d}'/f'{typ}_{fit.label(mass)}'/'data'/target.name
    if not target.is_file() or not source.is_file() or fit.sha(target)!=fit.sha(source):
        raise RuntimeError('Repair must reuse the exact original signal file: '+str(target))
    return target

fit.signal_sample=signals
evaluation.signal_sample=signals

def inventory():
    saved=json.loads((ROOT/'inventory.json').read_text())
    # Original absolute paths remain in the immutable provenance JSON. Resolve
    # their final run/point components against this checkout for execution.
    for row in saved['points']:
        tail=Path(row['new_point']).parts[-2:]
        row['new_point']=str(ROOT/'fits'/tail[0]/tail[1])
        row['old_point']=str(OLD/'fits'/tail[0]/tail[1])
    saved['affected']=[row for row in saved['points'] if row['split']]
    return saved
def point(row):return Path(row['new_point'])

def verify_original_executables():
    records=[]
    for row in inventory()['affected']:
        if row['split']!='train':continue
        old=Path(row['old_point'])
        paths=list(old.glob('*/*/*/trained.json'))+list(old.glob('*/boxes/*.done.json'))
        if len(paths)!=22:raise RuntimeError('Missing original training/box command records '+str(old))
        for path in paths:
            meta=json.loads(path.read_text());args=meta['arguments']
            calculated=hashlib.sha256((json.dumps(args)+fit.sha(Path(args[0]))).encode()).hexdigest()
            if calculated!=meta['signature']:
                raise RuntimeError('Original fitting executable changed: '+str(path))
            records.append(dict(marker=str(path),signature=calculated,executable_sha256=fit.sha(Path(args[0]))))
    fit.atomic_json(ROOT/'original_executable_check.json',dict(passed=True,records=records))

def merge():
    generation=json.loads((ROOT/'photon_generation_status.json').read_text())
    if generation.get('state')!='complete' or generation['completed']!=6:
        raise RuntimeError('Six validated replacements are required')
    for rep,mass,split in ((4,1.585,'train'),(7,1.585,'train'),(5,1.585,'test'),
                            (5,2.512,'test'),(1,5.,'validation'),(4,6.31,'validation')):
        fit.merge(rep,mass,split)
    verify_original_executables()

def run_validation(row):
    p=point(row);rep=int(row['rep']);mass=float(row['mass_GeV'])
    args=[sys.executable,str(ROOT/'scripts/validation_reselect.py'),
          '--point',str(p),'--original-point',row['old_point'],
          '--photon-train',str(fit.data_dir(rep,mass)/'train.root'),
          '--photon-validation',str(fit.data_dir(rep,mass)/'validation.root'),'--execute']
    with (p/'validation_reselect.log').open('w') as stream:
        subprocess.run(args,stdout=stream,stderr=subprocess.STDOUT,check=True)
    repaired=json.loads((p/'validation_reselect_complete.json').read_text())
    marker=json.loads((Path(row['old_point'])/'fit_complete.json').read_text())
    marker.update(state='validation_reselected_after_sampling_repair',
        support=repaired['support'],original_training_preserved=True,
        validation_reselection_seconds=repaired['seconds'],
        repair_provenance=str(p/'validation_reselect_complete.json'))
    fit.atomic_json(p/'fit_complete.json',marker)
    return repaired

def fit_one(row):
    if row['split']=='train':
        return fit.fit_point(int(row['rep']),row['signal_type'],float(row['mass_GeV']))
    return run_validation(row)

def fitting():
    jobs=[r for r in inventory()['affected'] if r['split'] in ('train','validation')]
    jobs.sort(key=lambda r:(r['split']!='train',r['rep'],r['signal_type']))
    done=[];errors=[]
    with ThreadPoolExecutor(max_workers=4) as pool:
        futures={pool.submit(fit_one,r):r for r in jobs}
        for future in as_completed(futures):
            row=futures[future]
            try:
                result=future.result();done.append(row)
                print('FITTED/RESELECTED',len(done),'/',len(jobs),row['rep'],row['signal_type'],row['mass_GeV'],row['split'],flush=True)
            except Exception as exc:
                errors.append(dict(point=row['new_point'],error=str(exc)))
                print('ERROR',errors[-1],flush=True)
            fit.atomic_json(ROOT/'fit_status.json',dict(state='running',completed=len(done),total=len(jobs),errors=errors))
    fit.atomic_json(ROOT/'fit_status.json',dict(state='failed' if errors else 'complete',completed=len(done),total=len(jobs),errors=errors))
    if errors:raise RuntimeError('Affected fitting/reselection failed; see fit_status.json')

def gate():
    selected={};models={};support=[]
    for cfgpath in sorted((ROOT/'fits').glob('rep_*/*/sample_config.json')):
        p=cfgpath.parent
        if not (p/'fit_complete.json').is_file():raise RuntimeError('Missing fit '+str(p))
        support+=fit.rows(p/'validation_support.csv')
        for feature in fit.FEATURES:
            for method in ('bdt','likelihood','cuts'):
                path=p/feature/f'{method}_selected.csv'
                selected[str(path.relative_to(ROOT))]=fit.sha(path)
                if method!='cuts':
                    row=fit.rows(path)[0];tag='BDTG' if method=='bdt' else 'PDERS'
                    model=p/feature/method/row['model_profile']/'dataset/weights'/f'TMVAClassification_{tag}.weights.xml.gz'
                    models[str(model.relative_to(ROOT))]=fit.sha(model)
    if len(selected)!=1320 or len(models)!=880:raise RuntimeError('Incomplete full-view selection/model inventory')
    issues=[r for r in support if r['method']=='likelihood' and float(r['score_half_weight_fraction'])>.01]
    fit.write(ROOT/'full_validation_support.csv',support)
    fit.atomic_json(ROOT/'full_support_gate.json',dict(passed=not issues,issues=issues,
        interpretation='Same validation support-warning proxy as the original study; not exhaustive numerical coverage proof'))
    if issues:raise RuntimeError('Corrected validation support proxy requires review')
    parent=json.loads((OLD/'fit_protocol_gate.json').read_text())
    parent.pop('locked',None)
    parent.update(passed=True,selection_sha256=selected,model_sha256=models,
        expected_points=220,expected_groups=22,
        repair_kind='post-evaluation numerical correction of six independently diagnosed photon support failures',
        new_blinded_confirmation=False,parent_gate_sha256=fit.sha(OLD/'fit_protocol_gate.json'),
        changed_point_count=12,reused_point_count=208,
        correction_protocol_sha256=fit.sha(ROOT/'protocol.md'),
        corrected_components=json.loads((ROOT/'photon_replacement_integrations.json').read_text()))
    path=ROOT/'fit_protocol_gate.json'
    if path.exists():
        if json.loads(path.read_text())!=parent:raise RuntimeError('Changed completed repair gate')
    else:fit.atomic_json(path,parent)

def evaluate():
    jobs=inventory()['affected'];done=[];errors=[]
    with ThreadPoolExecutor(max_workers=4) as pool:
        futures={pool.submit(evaluation.final_point,int(r['rep']),r['signal_type'],float(r['mass_GeV'])):r for r in jobs}
        for future in as_completed(futures):
            row=futures[future]
            try:
                future.result();done.append(row)
                print('EVALUATED',len(done),'/',len(jobs),row['rep'],row['signal_type'],row['mass_GeV'],flush=True)
            except Exception as exc:
                errors.append(dict(point=row['new_point'],error=str(exc)));print('ERROR',errors[-1],flush=True)
            fit.atomic_json(ROOT/'evaluation_status.json',dict(state='running',completed=len(done),total=len(jobs),errors=errors))
    fit.atomic_json(ROOT/'evaluation_status.json',dict(state='failed' if errors else 'complete',completed=len(done),total=len(jobs),errors=errors))
    if errors:raise RuntimeError('Affected evaluation failed')

def analyze():
    jobs=inventory()['affected'];done=[]
    gatehash=analysis.gate_check(ROOT/'fit_protocol_gate.json')
    with ThreadPoolExecutor(max_workers=4) as pool:
        futures={pool.submit(analysis.process_point,point(r),ROOT,2000,48230000,32,gatehash):r for r in jobs}
        for future in as_completed(futures):
            result=future.result();done.append(result)
            print('ANALYZED',len(done),'/',len(jobs),result,flush=True)
            fit.atomic_json(ROOT/'point_analysis_status.json',dict(state='running',completed=len(done),total=len(jobs)))
    fit.atomic_json(ROOT/'point_analysis_status.json',dict(state='complete',completed=len(done),total=len(jobs)))
    sys.path.insert(0,str(ROOT/'scripts'))
    from check_reuse import check_reuse
    check_reuse(OLD,ROOT,gate_path=ROOT/'fit_protocol_gate.json',report_path=ROOT/'reuse_audit.json')
    result=analysis.summarize(ROOT,1000000,48230000+900000,22,220)
    if result['state']!='complete':raise RuntimeError('Incomplete repaired full-view aggregation')

def plots():
    for script in ('compare_selections.py','plot_stratified_refit.py'):
        args=[sys.executable,str(REV/'scripts'/script),'--results',str(ROOT)]
        if script.startswith('compare'):args+=['--workers','4']
        with (ROOT/(script+'.log')).open('w') as stream:
            subprocess.run(args,stdout=stream,stderr=subprocess.STDOUT,check=True)

def main():
    p=argparse.ArgumentParser();p.add_argument('--stage',choices=['all','merge','fit','gate','evaluate','analyze','plots'],default='all')
    args=p.parse_args()
    stages=[('merge',merge),('fit',fitting),('gate',gate),('evaluate',evaluate),('analyze',analyze),('plots',plots)]
    for name,fn in stages:
        if args.stage not in ('all',name):continue
        status(name);fn()
    status('complete',next='Compare before/after corrected numerical results; original study and manuscript preserved.')

if __name__=='__main__':
    try:main()
    except Exception as exc:
        status('needs_attention',error=str(exc));raise
