#!/usr/bin/env python3
"""Resume-safe corrected fitting study; final test generation follows pilot gates."""
import os
for k in ['OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','VECLIB_MAXIMUM_THREADS']:
    os.environ[k]='1'
import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
import csv
import gzip
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import time
from prepare_stratified_data import BASE, OUT, MASSES, label, sha

PROJECT=Path(os.environ.get('DARK_PROJECT_ROOT', str(Path(__file__).resolve().parents[2])))
FEATURES=['electron_qa2','electron']
BDT_PROFILES=['depth2','depth3','depth4','depth3_800']
LIKELIHOOD_PROFILES=['h02','h04','h08','h16']

def rows(path):
    with path.open() as f:return list(csv.DictReader(f))
def write(path,records):
    path.parent.mkdir(parents=True,exist_ok=True)
    with path.open('w') as f:
        w=csv.DictWriter(f,fieldnames=list(records[0]));w.writeheader();w.writerows(records)
def atomic_json(path,value):
    path.parent.mkdir(parents=True,exist_ok=True)
    with tempfile.NamedTemporaryFile(mode='w',dir=path.parent,delete=False) as stream:
        temp=Path(stream.name);json.dump(value,stream,indent=2);stream.write('\n')
    temp.replace(path)

def all_pass_candidate(template,feature):
    """Retain the original unrefined selection alongside optimized boxes."""
    candidate=dict(template)
    candidate['selection_kind']='all_pass'
    for key in ['training_signal_efficiency','training_photon_efficiency','training_significance_improvement',
                'validation_signal_efficiency','validation_photon_efficiency','validation_significance_improvement',
                'signal_efficiency','photon_background_efficiency','significance_improvement']:
        if key not in candidate:raise RuntimeError('Missing rectangular metric '+key)
        candidate[key]='1'
    candidate['coupling_reach_improvement']='0'
    candidate['candidate_count']='1'
    candidate['quantiles']='0';candidate['restarts']='0'
    for name in ['logQe2','pt','eta','energy','logQA2']:
        for side in ['min','max']:
            key=name+'_'+side
            if key not in candidate:raise RuntimeError('Missing rectangular bound '+key)
            candidate[key]='NA' if name=='logQA2' and feature=='electron' else ('-inf' if side=='min' else 'inf')
    return candidate

def select_cuts(candidates,feature):
    optimized=[dict(row,selection_kind='optimized') for row in candidates if row.get('selection_kind')!='all_pass']
    if not optimized:raise RuntimeError('No optimized rectangular candidates')
    candidates=optimized+[all_pass_candidate(optimized[0],feature)]
    selected=max(candidates,key=lambda r:(float(r['validation_significance_improvement']),float(r['training_significance_improvement'])))
    return selected,candidates

def same_cut_bounds(left,right,feature):
    names=['logQe2','pt','eta','energy']+(['logQA2'] if feature=='electron_qa2' else [])
    return all(float(left[name+'_'+side])==float(right[name+'_'+side]) for name in names for side in ['min','max'])

def export_validation(point,feature):
    """Refresh validation diagnostics from selections; never reads final tests."""
    cfg=json.loads((point/'sample_config.json').read_text())
    sigval=point/'data/signal_validation.root'
    photons=data_dir(int(cfg['rep']),float(cfg['mass_GeV']))/'validation.root'
    dest=point/feature
    for method,tag in [('bdt','BDTG'),('likelihood','PDERS')]:
        selection=rows(dest/f'{method}_selected.csv')[0]
        model=dest/method/selection['model_profile']/'dataset/weights'/f'TMVAClassification_{tag}.weights.xml'
        if not model.exists():model.write_bytes(gzip.decompress(model.with_suffix('.xml.gz').read_bytes()))
        prefix=dest/f'validation_{method}'
        command([BASE/'bin/export_refit_scores',sigval,photons,model,dest/f'{method}_selected.csv',
                 dest/'cuts_selected.csv',prefix,feature,cfg['photon_xs_pb'],cfg['dis_xs_pb']],
                prefix.with_suffix('.log'),prefix.with_suffix('.done.json'))
        for sample in ['signal','photon']:compress(dest/f'validation_{method}_{sample}.csv')
        compress(model)

def validation_support(point):
    records=[]
    cfg=json.loads((point/'sample_config.json').read_text())
    for feature in FEATURES:
        dest=point/feature
        for method in ['bdt','likelihood']:
            selection=rows(dest/f'{method}_selected.csv')[0]
            for row in rows(dest/f'validation_{method}_support.csv'):
                if row['sample']=='photon' and row['stratum']=='outside':
                    records.append(dict(rep=int(cfg['rep']),signal_type=cfg['signal_type'],mass_GeV=float(cfg['mass_GeV']),
                                        feature_set=feature,method=method,profile=selection['model_profile'],**row))
    write(point/'validation_support.csv',records)
    return records

def repair_all_pass(point):
    """Repair pilot outputs after active heavy fitting has finished."""
    changed=[]
    for feature in FEATURES:
        dest=point/feature
        optimized=[row for q in [40,80,160] for row in rows(dest/'boxes'/f'q{q}.csv')]
        selected,candidates=select_cuts(optimized,feature)
        old=rows(dest/'cuts_selected.csv')[0]
        if not same_cut_bounds(old,selected,feature):
            archive=dest/'validation_before_all_pass'/str(time.time_ns());archive.mkdir(parents=True)
            shutil.copy2(dest/'cuts_selected.csv',archive/'cuts_selected.csv')
            for method in ['bdt','likelihood']:
                for path in list(dest.glob(f'validation_{method}_*'))+[dest/f'validation_{method}.done.json',dest/f'validation_{method}.log']:
                    if path.is_file():path.replace(archive/path.name)
            changed.append(feature)
        write(dest/'cuts_selected.csv',[selected]);write(dest/'cuts_candidates.csv',candidates)
        if feature in changed:export_validation(point,feature)
    support=validation_support(point)
    marker=point/'fit_complete.json'
    result=json.loads(marker.read_text())
    result.update(all_pass_validation_candidate=True,all_pass_repaired_features=changed,support=support)
    atomic_json(marker,result)
    return changed

def full_support_gate():
    records=[]
    for rep in range(1,11):
        for mass in MASSES:
            for typ in ['vector','scalar']:
                records+=validation_support(point_dir(rep,typ,mass))
    issues=[r for r in records if r['method']=='likelihood' and float(r['score_half_weight_fraction'])>.01]
    result={'passed':not issues,'scope':'all 220 fitted points; validation only',
            'warning_proxy':'More than1% outside weight at exact score0.5 requires support review, not automatic interpretation as empty density.',
            'max_likelihood_score_half_outside_fraction':max(float(r['score_half_weight_fraction']) for r in records if r['method']=='likelihood'),
            'issues':issues}
    atomic_json(OUT/'full_support_gate.json',result);write(OUT/'full_validation_support.csv',records)
    if issues:raise RuntimeError('Full-scan likelihood support review needed before final samples; see full_support_gate.json')
    return result
def command(args,log,marker):
    args=list(map(str,args));marker=Path(marker)
    signature=hashlib.sha256((json.dumps(args)+sha(Path(args[0]))).encode()).hexdigest()
    if marker.exists():
        old=json.loads(marker.read_text())
        if old['signature']!=signature:raise RuntimeError('Changed successful command: '+str(marker))
        return old
    reserve_gib=float(os.environ.get('DARK_STUDY_MIN_FREE_GIB','15'))
    if not 10<=reserve_gib<=15:raise RuntimeError('Study free-space reserve must be between 10 and 15 GiB')
    if shutil.disk_usage(OUT).free<reserve_gib*1024**3:
        raise RuntimeError(f'Less than{reserve_gib:g}GiB free; new commands stopped')
    Path(log).parent.mkdir(parents=True,exist_ok=True)
    started=time.time()
    with Path(log).open('w') as f:
        f.write(json.dumps(args)+'\n');f.flush()
        subprocess.run(args,stdout=f,stderr=subprocess.STDOUT,check=True)
    result={'signature':signature,'seconds':time.time()-started,'arguments':args}
    atomic_json(marker,result);return result

def compress(path):
    if not path.exists():return
    target=path.with_suffix(path.suffix+'.gz');tmp=target.with_suffix(target.suffix+'.tmp')
    digest=hashlib.sha256()
    with path.open('rb') as src,gzip.open(tmp,'wb',compresslevel=6) as dst:
        for b in iter(lambda:src.read(1024*1024),b''):digest.update(b);dst.write(b)
    check=hashlib.sha256()
    with gzip.open(tmp,'rb') as src:
        for b in iter(lambda:src.read(1024*1024),b''):check.update(b)
    if check.digest()!=digest.digest():raise RuntimeError('Compression verification failed')
    tmp.replace(target);path.unlink()

def data_dir(rep,mass):return OUT/'data'/f'rep_{rep:03d}'/label(mass)
def point_dir(rep,typ,mass):return OUT/'fits'/f'rep_{rep:03d}'/f'{typ}_{label(mass)}'

def merge(rep,mass,split):
    d=data_dir(rep,mass);target=d/f'{split}.root'
    if not (d/f'{split}_merged.json').exists():
        command([BASE/'bin/merge_photon_strata',d/f'{split}_central.root',d/f'{split}_outside.root',target],
                d/f'{split}_merge.log',d/f'{split}_merged.json')
    c=json.loads((d/f'{split}_central.json').read_text());o=json.loads((d/f'{split}_outside.json').read_text())
    meta={'attempts_central':c['attempts'],'attempts_outside':o['attempts'],'central_sigma_pb':c['sigma_pb'],
          'outside_sigma_pb':o['sigma_pb'],'epsilon_central':1e-6,'effective_sigma_pb':1e-6*c['sigma_pb']+o['sigma_pb'],
          'file_sha256':sha(target)}
    atomic_json(d/f'{split}_merge.json',meta)
    return target

def calibration(mass):
    d=data_dir(0,mass)
    c=json.loads((d/'calibration_central.json').read_text());o=json.loads((d/'calibration_outside.json').read_text())
    for a in [c,o]:
        if a['sigma_error_pb']/a['sigma_pb']>.03:raise RuntimeError('Calibration integration insufficiently precise '+str(mass))
    return {'photon_xs_pb':1e-6*c['sigma_pb']+o['sigma_pb'],
            'photon_xs_mc_error_pb':((1e-6*c['sigma_error_pb'])**2+o['sigma_error_pb']**2)**.5,
            'source':'separate calibration rep000, independent of fitting/validation/final tests'}

def signal_sample(point,rep,typ,mass,split):
    d=point/'data';d.mkdir(exist_ok=True);target=d/f'signal_{split}.root'
    if split in ['train','validation']:
        existing=BASE/'results'/f'rep_{rep:03d}'/f'{typ}_{label(mass)}'/'data'/target.name
        if not existing.exists():raise RuntimeError('Existing independent fitting signal unavailable '+str(existing))
        source=existing.resolve(strict=True)
        if target.is_symlink() and target.resolve()!=source:raise RuntimeError('Signal source changed')
        if not target.exists():target.symlink_to(source)
    else:
        seed=681000000+MASSES.index(mass)*100000+rep*1000+(100 if typ=='scalar' else 0)
        args=[PROJECT/'bin'/f'generate_{typ}','--mass',mass,'--events',50000,'--cells',1000,'--samples',300,
              '--seed',seed,'--output',target]
        args+=['--integrate-paper-cut','--quiet'] if typ=='vector' else ['--selected']
        command(args,d/'signal_test.log',d/'signal_test.generated.json')
    if not target.is_file() or target.stat().st_size==0:raise RuntimeError('Signal sample missing or empty: '+str(target))
    return target

def fit_point(rep,typ,mass):
    started=time.time();point=point_dir(rep,typ,mass);point.mkdir(parents=True,exist_ok=True)
    if (point/'fit_complete.json').exists():return json.loads((point/'fit_complete.json').read_text())
    cfg=next(r for r in rows(BASE/'config/rates.csv') if r['signal_type']==typ and abs(float(r['mass_GeV'])-mass)<1e-8)
    cal=calibration(mass);cfg.update(cal);cfg['mass_GeV']=mass;cfg['rep']=rep
    atomic_json(point/'sample_config.json',cfg)
    sigtrain=signal_sample(point,rep,typ,mass,'train');sigval=signal_sample(point,rep,typ,mass,'validation')
    photons={s:data_dir(rep,mass)/f'{s}.root' for s in ['train','validation']}
    if not all(p.exists() for p in photons.values()):raise RuntimeError('Merged fitting photons unavailable')
    sx,px,dx=cfg['signal_xs_pb'],cfg['photon_xs_pb'],cfg['dis_xs_pb']
    block=691000000+MASSES.index(mass)*100000+rep*1000+(100 if typ=='scalar' else 0)
    support=[]
    for feature in FEATURES:
        dest=point/feature;dest.mkdir(exist_ok=True)
        for method,profiles in [('likelihood',LIKELIHOOD_PROFILES),('bdt',BDT_PROFILES)]:
            candidates=[]
            for profile in profiles:
                model=dest/method/profile;model.mkdir(parents=True,exist_ok=True)
                binary=BASE/'bin/train_likelihood' if method=='likelihood' else PROJECT/'bin/train_tmva'
                args=[binary,sigtrain,sigval,photons['train'],photons['validation'],model,typ,mass,sx,px,dx,feature,profile,block+31,'validation_all']
                command(args,model/'fit.log',model/'trained.json');candidates.append(rows(model/'metrics.csv')[0])
                # Generated diagnostics duplicate the retained source events/models.
                diagnostic=model/'training.root'
                if diagnostic.exists():diagnostic.unlink()
                compress(model/'test_scores.csv') # These are validation scores in validation_all mode.
            selected=max(candidates,key=lambda r:float(r['validation_significance_improvement']))
            write(dest/f'{method}_candidates.csv',candidates);write(dest/f'{method}_selected.csv',[selected])
        candidates=[]
        for q in [40,80,160]:
            path=dest/'boxes'/f'q{q}.csv';path.parent.mkdir(exist_ok=True)
            args=[PROJECT/'bin/optimize_rectangular_fair',sigtrain,photons['train'],sigval,photons['validation'],
                  sigval,photons['validation'],path,typ,mass,sx,px,dx,feature,q,20,block+21]
            command(args,path.with_suffix('.log'),path.with_suffix('.done.json'));candidates.extend(rows(path))
        selected,candidates=select_cuts(candidates,feature)
        write(dest/'cuts_selected.csv',[selected]);write(dest/'cuts_candidates.csv',candidates)
        for method,tag in [('bdt','BDTG'),('likelihood','PDERS')]:
            selection=rows(dest/f'{method}_selected.csv')[0]
            model=dest/method/selection['model_profile']/'dataset/weights'/f'TMVAClassification_{tag}.weights.xml'
            if not model.exists():
                model.write_bytes(gzip.decompress(model.with_suffix('.xml.gz').read_bytes()))
            prefix=dest/f'validation_{method}'
            command([BASE/'bin/export_refit_scores',sigval,photons['validation'],model,dest/f'{method}_selected.csv',
                     dest/'cuts_selected.csv',prefix,feature,px,dx],prefix.with_suffix('.log'),prefix.with_suffix('.done.json'))
            for row in rows(dest/f'validation_{method}_support.csv'):
                if row['sample']=='photon' and row['stratum']=='outside':
                    support.append(dict(rep=rep,signal_type=typ,mass_GeV=mass,feature_set=feature,method=method,
                                        profile=selection['model_profile'],**row))
            for sample in ['signal','photon']:compress(dest/f'validation_{method}_{sample}.csv')
        for model in dest.glob('*/**/*.weights.xml'):compress(model)
    write(point/'validation_support.csv',support)
    result={'rep':rep,'signal_type':typ,'mass_GeV':mass,'state':'fitted_validation_only','seconds':time.time()-started,
            'support':support,'signal_train_sha256':sha(sigtrain),'signal_validation_sha256':sha(sigval)}
    atomic_json(point/'fit_complete.json',result)
    return result

def prepare_merges(masses,reps):
    for rep in reps:
        for mass in masses:
            for split in ['train','validation']:merge(rep,mass,split)

def fit_groups(masses,reps,stage):
    jobs=[(r,t,m) for r in reps for m in masses for t in ['vector','scalar']]
    done=[];errors=[]
    def status(state):atomic_json(OUT/f'{stage}_fit_status.json',{'state':state,'completed':len(done),'total':len(jobs),'errors':errors})
    status('running')
    with ThreadPoolExecutor(max_workers=4) as pool:
        fs={pool.submit(fit_point,*job):job for job in jobs}
        for f in as_completed(fs):
            try:
                row=f.result();done.append(row);print('Fitted',len(done),'/',len(jobs),fs[f],round(row['seconds'],1),'seconds',flush=True)
            except Exception as exc:errors.append({'job':fs[f],'error':str(exc)});print('ERROR',errors[-1],flush=True)
            status('running')
    status('failed' if errors else 'complete')
    if errors:raise RuntimeError('Fitting jobs failed; see status')
    return done

def pilot_gate():
    records=[]
    for rep in range(1,4):
        for mass in [.032,10.]:
            for typ in ['vector','scalar']:
                records+=rows(point_dir(rep,typ,mass)/'validation_support.csv')
    issues=[r for r in records if r['method']=='likelihood' and float(r['score_half_weight_fraction'])>.01]
    result={'passed':not issues,'scope':'validation only; no final tests generated/read',
            'warning_proxy':'Exact score0.5 is not uniquely an empty-density marker; >1% weighted outside rate triggers numerical-support review before full scan.',
            'max_likelihood_score_half_outside_fraction':max(float(r['score_half_weight_fraction']) for r in records if r['method']=='likelihood'),
            'issues':issues}
    atomic_json(OUT/'pilot_gate.json',result);write(OUT/'pilot_validation_support.csv',records)
    return result

def generate(stage):
    command([Path(sys.executable),BASE/'scripts/prepare_stratified_data.py','--stage',stage],
            OUT/f'{stage}_generation_driver.log',OUT/f'{stage}_generation_driver.done.json')

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--stage',choices=['pilot-fit','full-fit'],required=True)
    args=parser.parse_args();OUT.mkdir(exist_ok=True)
    if args.stage=='pilot-fit':
        generation=json.loads((OUT/'pilot_generation_status.json').read_text())
        if generation['state']!='complete':raise RuntimeError('Pilot photon generation not complete')
        prepare_merges([.032,10.],range(1,4));fit_groups([.032,10.],range(1,4),'pilot')
        gate=pilot_gate();print('PILOT_GATE',json.dumps(gate),flush=True)
        if not gate['passed']:raise SystemExit(2)
    else:
        gate=json.loads((OUT/'pilot_gate.json').read_text())
        if not gate['passed']:raise RuntimeError('Pilot support gate has not passed')
        generate('full');prepare_merges(MASSES,range(1,11));fit_groups(MASSES,range(1,11),'full')
        for rep in range(1,11):
            for mass in MASSES:
                for typ in ['vector','scalar']:
                    repaired=repair_all_pass(point_dir(rep,typ,mass))
                    if repaired:print('REPAIRED_ALL_PASS',rep,typ,mass,repaired,flush=True)
        full_support_gate()
        print('ALL_FITTING_COMPLETE; final test stage can now be locked and generated',flush=True)

if __name__=='__main__':main()
