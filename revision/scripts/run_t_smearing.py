#!/usr/bin/env python3
"""Fixed-selector 10% t resolution sensitivity at 10 GeV, four workers."""
import concurrent.futures as cf
import csv, gzip, json, math, subprocess, time
from pathlib import Path
import numpy as np
BASE=Path(__file__).resolve().parents[1]
OUT=BASE/'t_smearing_10gev_10pct'
OUT.mkdir(exist_ok=True)
def rows(p):
    with p.open() as f: return list(csv.DictReader(f))
def write(p,r):
    with p.open('w') as f:
        w=csv.DictWriter(f,fieldnames=list(r[0]));w.writeheader();w.writerows(r)
def job(typ,rep):
    start=time.time(); src=BASE/'results'/f'rep_{rep:03d}'/f'{typ}_m10p000'; sel=src/'electron_qa2'
    dst=OUT/f'rep_{rep:03d}'/typ;dst.mkdir(parents=True,exist_ok=True)
    record={'boson':typ,'rep':rep}
    for method,tag in [('bdt','BDTG'),('likelihood','PDERS')]:
        config=rows(sel/f'{method}_selected.csv')[0]; original=rows(sel/f'{method}_test.csv')[0]
        model=sel/method/config['model_profile']/'dataset/weights'/f'TMVAClassification_{tag}.weights.xml'
        local=dst/f'{method}.xml'
        local.write_bytes(model.read_bytes() if model.exists() else gzip.decompress(model.with_suffix('.xml.gz').read_bytes()))
        for fraction,label in [(0.,'zero'),(.1,'smeared')]:
            output=dst/f'{method}_{label}.csv'
            args=[BASE/'bin/evaluate_t_smearing',src/'data/signal_test.root',src/'data/photon_test.root',local,sel/f'{method}_selected.csv',sel/'cuts_selected.csv',output,'electron_qa2',config['photon_xs_pb'],config['dis_xs_pb'],2000,original['bootstrap_seed'],fraction,700000+rep+(10000 if typ=='scalar' else 0)]
            with (dst/f'{method}_{label}.log').open('w') as f:
                f.write(json.dumps(list(map(str,args)))+'\n');f.flush()
                subprocess.run(list(map(str,args)),stdout=f,stderr=subprocess.STDOUT,check=True)
            result=rows(output)[0]
            if label=='zero':
                for key,value in original.items():
                    if key=='feature_set': continue
                    if not math.isclose(float(value),float(result[key]),rel_tol=1e-9,abs_tol=1e-12):
                        raise RuntimeError(f'Zero-smearing mismatch {typ} {rep} {method} {key}')
            record[f'{method}_{label}_RZ']=float(result['bdt_RZ'])
            record[f'cuts_{label}_RZ']=float(result['box_RZ'])
            if label=='smeared' and method=='likelihood':
                b=rows(dst/'bdt_smeared.csv')[0]
                for key in ['box_RZ','box_signal_efficiency','box_photon_efficiency']:
                    if result[key]!=b[key]: raise RuntimeError('Shared smearing/cuts mismatch')
        local.unlink()
    record['seconds']=time.time()-start
    (dst/'complete.json').write_text(json.dumps(record,indent=2))
    return record

def main():
    plan={'mass_GeV':10,'fractional_sigma_t':0.1,'workers':4,'runs_per_boson':10,'methods':['BDT','PDERS likelihood','rectangular cuts'],'formula':'t_s=t*(1+0.1*z), z standard Gaussian; redraw nonpositive factors','scope':'test-event t only; existing models, thresholds, cuts, weights and background rates unchanged','interpretation':'assumed resolution sensitivity benchmark, not channel-specific detector simulation','bootstrap':'2000 paired event resamples per run; 20000 run-and-event resamples for descriptive 95% intervals; one smearing realization per independent run','zero_check':'all original evaluation columns reproduced for both trained methods in every run'}
    (OUT/'plan.json').write_text(json.dumps(plan,indent=2))
    completed=[]; failures=[]
    def status(state): (OUT/'status.json').write_text(json.dumps({'state':state,'completed':len(completed),'total':20,'failures':failures},indent=2))
    status('running')
    with cf.ThreadPoolExecutor(max_workers=4) as pool:
        futures={pool.submit(job,t,r):(t,r) for t in ['vector','scalar'] for r in range(1,11)}
        for f in cf.as_completed(futures):
            try:
                result=f.result();completed.append(result);print(f"Completed {len(completed)}/20: {result['boson']} run {result['rep']}",flush=True)
            except Exception as e:
                failures.append({'job':futures[f],'error':str(e)});print(str(e),flush=True)
            status('running')
    if failures: status('failed');return
    write(OUT/'run_results.csv',sorted(completed,key=lambda r:(r['boson'],r['rep'])))
    summary=[];rng=np.random.default_rng(81623)
    for typ in ['vector','scalar']:
        for label in ['zero','smeared']:
            nominal=[]; draws=[]
            for rep in range(1,11):
                p=OUT/f'rep_{rep:03d}'/typ
                b,l=[rows(p/f'{m}_{label}.csv')[0] for m in ['bdt','likelihood']]
                nominal.append([float(b['RZ_ratio']),float(l['RZ_ratio']),float(b['RZ_ratio'])/float(l['RZ_ratio'])])
                bb,ll=[rows(p/f'{m}_{label}_bootstrap.csv') for m in ['bdt','likelihood']]
                if len(bb)!=2000 or len(ll)!=2000: raise RuntimeError('Incomplete bootstrap pairing')
                draws.append([[float(x['RZ_ratio']),float(y['RZ_ratio']),float(x['RZ_ratio'])/float(y['RZ_ratio'])] for x,y in zip(bb,ll)])
            a=np.log(np.array(draws)); runs=rng.integers(0,10,(20000,10)); events=rng.integers(0,2000,(20000,10))
            dist=100*np.expm1(a[runs,events].mean(axis=1)); point=100*np.expm1(np.log(nominal).mean(axis=0))
            for i,pair in enumerate(['BDT/cuts','likelihood/cuts','BDT/likelihood']):
                lo,hi=np.quantile(dist[:,i],[.025,.975]);summary.append(dict(boson=typ,condition=label,comparison=pair,significance_advantage_pct=point[i],ci95_low_pct=lo,ci95_high_pct=hi))
    write(OUT/'summary.csv',summary);status('complete')
    print(json.dumps(summary,indent=2),flush=True)
if __name__=='__main__': main()
