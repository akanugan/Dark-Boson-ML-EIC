#!/usr/bin/env python3
"""Continue the authorized numerical plan through pilot gates and final analyses."""
import os
for k in ['OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','VECLIB_MAXIMUM_THREADS']:os.environ[k]='1'
import fcntl
import json
from pathlib import Path
import shutil
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor,as_completed
from run_stratified_refit import (BASE,OUT,MASSES,FEATURES,PROJECT,point_dir,data_dir,rows,
                                  atomic_json,command,compress,merge,signal_sample,sha)

START=time.time()
def state(phase,**extra):
    atomic_json(OUT/'study_status.json',dict(phase=phase,pid=os.getpid(),started=START,updated=time.time(),**extra))
    print('PHASE',phase,json.dumps(extra),flush=True)

def wait_pilot():
    last=None
    while True:
        file=OUT/'pilot_fit_status.json'
        s=json.loads(file.read_text()) if file.exists() else {}
        if s!=last:
            print('PILOT',json.dumps(s),flush=True);last=s
        if s.get('state')=='failed':raise RuntimeError('Pilot fitting failed; inspect pilot_fit_status.json')
        if s.get('state')=='complete':break
        time.sleep(5)
    # pilot-fit writes its gate after publishing fit_status=complete. Waiting for
    # that file avoids two coordinators writing the same gate/summary concurrently.
    gate_path=OUT/'pilot_gate.json'
    while not gate_path.exists():time.sleep(1)
    gate=json.loads(gate_path.read_text())
    if not gate['passed']:raise RuntimeError('Pilot likelihood support review needed; full scan not started')
    state('pilot_passed',max_outside_score_half_fraction=gate['max_likelihood_score_half_outside_fraction'])

def require_exports(point):
    expected=[]
    for feature in FEATURES:
        for method in ['bdt','likelihood']:
            prefix=point/feature/f'test_{method}'
            expected += [prefix.with_name(prefix.name+'_'+sample+'.csv.gz') for sample in ['signal','photon']]
            expected += [prefix.with_name(prefix.name+'_'+suffix+'.csv') for suffix in ['support','metrics']]
    missing=[str(path) for path in expected if not path.is_file() or path.stat().st_size==0]
    if missing:raise RuntimeError('Missing final evaluation outputs: '+', '.join(missing))

def verify_locked_point(point):
    gate=json.loads((OUT/'fit_protocol_gate.json').read_text())
    if gate.get('passed') is not True:raise RuntimeError('Fitting protocol is not locked')
    observed={}
    for feature in FEATURES:
        dest=point/feature
        for method in ['bdt','likelihood','cuts']:
            path=dest/f'{method}_selected.csv';key=str(path.relative_to(OUT));actual=sha(path)
            if gate['selection_sha256'].get(key)!=actual:raise RuntimeError('Locked selection changed: '+key)
            observed[key]=actual
            if method!='cuts':
                selected=rows(path)[0];tag='BDTG' if method=='bdt' else 'PDERS'
                model=dest/method/selected['model_profile']/'dataset/weights'/f'TMVAClassification_{tag}.weights.xml.gz'
                key=str(model.relative_to(OUT));actual=sha(model)
                if gate['model_sha256'].get(key)!=actual:raise RuntimeError('Locked fitted model changed: '+key)
                observed[key]=actual
    observed['sample_config.json']=sha(point/'sample_config.json')
    return observed

def require_analysis_complete(root):
    from analyze_stratified_refit import SCENARIO_MODES,EPSILONS,CONTRASTS
    gate=json.loads((root/'fit_protocol_gate.json').read_text())
    status=json.loads((root/'analysis_status.json').read_text())
    groups=int(gate.get('expected_groups',22));points=int(gate.get('expected_points',220))
    if status.get('state')!='complete' or status.get('complete_groups')!=groups or status.get('completed_independent_points')!=points:
        raise RuntimeError('Analysis is incomplete: '+str(root))
    summary=rows(root/'summary.csv')
    if len(summary)!=groups*len(CONTRASTS):raise RuntimeError('Missing nominal summary contrasts: '+str(root))
    if len(rows(root/'scenario_summary.csv'))!=groups*len(SCENARIO_MODES)*len(EPSILONS)*len(CONTRASTS):
        raise RuntimeError('Missing descriptive photon scenarios: '+str(root))

def final_point(rep,typ,mass,smearing=0.,smearing_root=None):
    point=point_dir(rep,typ,mass)
    destpoint=point if smearing_root is None else smearing_root/'fits'/f'rep_{rep:03d}'/f'{typ}_m{mass:.3f}'.replace('.','p')
    destpoint.mkdir(parents=True,exist_ok=True)
    marker=destpoint/('final_complete.json' if smearing==0 else 'smearing_complete.json')
    locked=verify_locked_point(point)
    if marker.exists():
        old=json.loads(marker.read_text());require_exports(destpoint)
        if old.get('locked_inputs')!=locked or old.get('exporter_sha256')!=sha(BASE/'bin/export_refit_scores'):
            raise RuntimeError('Cached final evaluation inputs changed: '+str(destpoint))
        if old.get('t_fraction')!=smearing:raise RuntimeError('Cached smearing fraction changed')
        sig=point/'data/signal_test.root';photons=data_dir(rep,mass)/'test.root'
        if not sig.is_file() or not photons.is_file() or old.get('signal_test_sha256')!=sha(sig) or old.get('photon_test_sha256')!=sha(photons):
            raise RuntimeError('Cached final source samples changed or disappeared: '+str(destpoint))
        return old
    started=time.time();cfg=json.loads((point/'sample_config.json').read_text())
    if destpoint!=point:atomic_json(destpoint/'sample_config.json',cfg)
    sig=signal_sample(point,rep,typ,mass,'test');photons=data_dir(rep,mass)/'test.root'
    if not photons.exists():raise RuntimeError('Fresh final photons unavailable')
    px,dx=cfg['photon_xs_pb'],cfg['dis_xs_pb']
    for feature in FEATURES:
        src=point/feature;dst=destpoint/feature;dst.mkdir(exist_ok=True)
        for method,tag in [('bdt','BDTG'),('likelihood','PDERS')]:
            selected=rows(src/f'{method}_selected.csv')[0]
            compressed=src/method/selected['model_profile']/'dataset/weights'/f'TMVAClassification_{tag}.weights.xml.gz'
            local=dst/f'{method}_evaluation.xml';local.write_bytes(__import__('gzip').decompress(compressed.read_bytes()))
            prefix=dst/f'test_{method}'
            args=[BASE/'bin/export_refit_scores',sig,photons,local,src/f'{method}_selected.csv',src/'cuts_selected.csv',prefix,feature,px,dx]
            if smearing:args += [smearing,731000000+rep*10]
            command(args,prefix.with_suffix('.log'),prefix.with_suffix('.done.json'))
            local.unlink()
            for sample in ['signal','photon']:compress(dst/f'test_{method}_{sample}.csv')
    result={'rep':rep,'signal_type':typ,'mass_GeV':mass,'t_fraction':smearing,'seconds':time.time()-started,
            'signal_test_sha256':sha(sig),'photon_test_sha256':sha(photons),'locked_inputs':locked,
            'exporter_sha256':sha(BASE/'bin/export_refit_scores')}
    require_exports(destpoint)
    if verify_locked_point(point)!=locked:raise RuntimeError('Locked inputs changed during final export')
    atomic_json(marker,result);return result

def evaluate(masses,label,smearing=0.,smearing_root=None):
    jobs=[(r,t,m) for r in range(1,11) for m in masses for t in ['vector','scalar']]
    done=[];errors=[]
    state(label,completed=0,total=len(jobs))
    with ThreadPoolExecutor(max_workers=4) as pool:
        fs={pool.submit(final_point,*j,smearing,smearing_root):j for j in jobs}
        for f in as_completed(fs):
            try:done.append(f.result());print('EVALUATED',label,len(done),'/',len(jobs),fs[f],flush=True)
            except Exception as exc:errors.append({'job':fs[f],'error':str(exc)});print('ERROR',errors[-1],flush=True)
            atomic_json(OUT/f'{label}_status.json',{'completed':len(done),'total':len(jobs),'errors':errors})
    if errors:raise RuntimeError('Evaluation failures in '+label)

def run_script(script,args,log):
    with (OUT/log).open('a') as f:
        subprocess.run([sys.executable,str(BASE/'scripts'/script),*map(str,args)],stdout=f,stderr=subprocess.STDOUT,check=True)

def preserve_locked_gate(path,proposed):
    """Keep an unchanged lock byte-for-byte; never relock changed final inputs."""
    if proposed.get('passed') is not True:raise RuntimeError('Cannot publish an unpassed fitting gate')
    if not path.exists():
        atomic_json(path,proposed)
        return proposed
    existing=json.loads(path.read_bytes())
    if existing.get('passed') is not True:
        raise RuntimeError('Existing fitting gate has not passed: '+str(path))
    # A restart proposes a new wall-clock timestamp. It is not a protocol
    # change and must not invalidate already cached evaluation/analysis work.
    immutable=lambda gate:{key:value for key,value in gate.items() if key!='locked'}
    before,after=immutable(existing),immutable(proposed)
    if before!=after:
        changed=sorted(key for key in set(before)|set(after) if before.get(key)!=after.get(key))
        raise RuntimeError('Existing locked fitting inputs/settings differ; final work was not relocked: '
                           +str(path)+'; changed fields: '+', '.join(changed))
    return existing

def main():
    OUT.mkdir(exist_ok=True)
    lock=(OUT/'master.lock').open('a')
    try:fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
    except BlockingIOError:
        print('An existing study coordinator holds the lock; leaving its status unchanged.',flush=True)
        return
    state('waiting_for_pilot_fit');wait_pilot()
    state('full_generation_and_fitting')
    run_script('run_stratified_refit.py',['--stage','full-fit'],'full_fit.log')
    # Lock before creating/reading fresh final evaluation samples. Validation
    # determines selections; the allocation below was set in protocol.md.
    support=json.loads((OUT/'full_support_gate.json').read_text())
    if support.get('passed') is not True:raise RuntimeError('Full-scan validation support gate has not passed')
    selected={};models={}
    for rep in range(1,11):
        for mass in MASSES:
            for typ in ['vector','scalar']:
                p=point_dir(rep,typ,mass)
                if not (p/'fit_complete.json').exists():raise RuntimeError('Missing fit '+str(p))
                for feature in FEATURES:
                    for method in ['bdt','likelihood','cuts']:
                        f=p/feature/f'{method}_selected.csv';selected[str(f.relative_to(OUT))]=sha(f)
                        if method!='cuts':
                            row=rows(f)[0];tag='BDTG' if method=='bdt' else 'PDERS'
                            model=p/feature/method/row['model_profile']/'dataset/weights'/f'TMVAClassification_{tag}.weights.xml.gz'
                            models[str(model.relative_to(OUT))]=sha(model)
    gate={'passed':True,'locked':time.time(),'runs_per_point':10,'signal_test_attempts':50000,
          'central_test_attempts':100000,'outside_test_attempts':40000,
          'selection_sha256':selected,'model_sha256':models,
          'precision_target':'10% relative on nonzero gains; target attainment reported, not assumed',
          'note':'Initial allocation fixed before final tests; no model/threshold choice uses these tests.'}
    gate=preserve_locked_gate(OUT/'fit_protocol_gate.json',gate)
    state('fresh_final_photon_generation')
    run_script('prepare_stratified_data.py',['--stage','test'],'final_generation.log')
    state('final_photon_merging')
    for rep in range(1,11):
        for mass in MASSES:merge(rep,mass,'test')
    evaluate(MASSES,'final_evaluation')
    state('paired_nominal_and_photon_scenario_analysis')
    run_script('analyze_stratified_refit.py',['--results',OUT,'--workers',4],'analysis.log')
    require_analysis_complete(OUT)
    run_script('plot_stratified_refit.py',['--results',OUT],'plots.log')
    for fraction,label in [(.1,'10pct'),(.2,'20pct')]:
        root=OUT/'smearing'/label;root.mkdir(parents=True,exist_ok=True)
        if not (root/'data').exists():(root/'data').symlink_to(OUT/'data',target_is_directory=True)
        preserve_locked_gate(root/'fit_protocol_gate.json',dict(gate,t_smearing_fraction=fraction,expected_groups=2,expected_points=20,
              interpretation='fixed-selector assumed-resolution benchmark; one paired noise realization per independent run'))
        evaluate([10.],f'smearing_{label}',fraction,root)
        run_script('analyze_stratified_refit.py',['--results',root,'--workers',4],f'smearing_{label}_analysis.log')
        require_analysis_complete(root)
        run_script('plot_stratified_refit.py',['--results',root],f'smearing_{label}_plots.log')
    run_script('plot_stratified_refit.py',['--results',OUT],'plots.log')
    state('numerical_results_complete',summary=str(OUT/'summary.csv'),
          next='Inspect results and precision flags, then update figures/manuscript consistently; no external upload performed.')

if __name__=='__main__':
    try:main()
    except Exception as exc:
        state('needs_attention',error=str(exc));raise
