#!/usr/bin/env python3
"""Resume-safe three-selector scan. No test events enter model selection."""
import argparse
import concurrent.futures
import csv
import hashlib
import gzip
import json
import os
from pathlib import Path
import shutil
import subprocess
import time

BASE = Path(__file__).resolve().parents[1]
PROFILES = ('depth2', 'depth3', 'depth4', 'depth3_800')
LIKELIHOODS = ('h02', 'h04', 'h08', 'h16')
FEATURES = ('electron', 'electron_qa2')

def rows(path):
    with Path(path).open() as f:
        return list(csv.DictReader(f))

def write_csv(path, values):
    with Path(path).open('w') as f:
        w = csv.DictWriter(f, fieldnames=list(values[0]), lineterminator='\n')
        w.writeheader()
        w.writerows(values)

def digest(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as f:
        for chunk in iter(lambda: f.read(1024*1024), b''):
            h.update(chunk)
    return h.hexdigest()

def command(args, log, marker):
    """Only reuse commands with identical arguments and a success marker."""
    args = list(map(str, args))
    marker = Path(marker)
    signature = hashlib.sha256(json.dumps(args).encode()).hexdigest()
    if marker.exists():
        if json.loads(marker.read_text())['signature'] != signature:
            raise RuntimeError(f'Changed command for {marker}; use a new output directory')
        return
    Path(log).parent.mkdir(parents=True, exist_ok=True)
    start = time.time()
    with Path(log).open('w') as f:
        f.write(json.dumps(args) + '\n'); f.flush()
        subprocess.run(args, stdout=f, stderr=subprocess.STDOUT, check=True)
    marker.write_text(json.dumps(dict(signature=signature, seconds=time.time()-start)))

def find_existing(project, rep, typ, mass):
    name = f'{typ}_m{mass:.3f}'.replace('.', 'p')
    for group, run in [('t_seed_robustness', 'run_t_20260820_final'),
                       ('seed_robustness', 'run_20260814T063518Z')]:
        point = project/'fair_study'/group/run/f'rep_{rep:03d}'/name
        if all((point/'data'/f'{kind}_{split}.root').exists()
               for kind in ('signal','photon') for split in ('train','validation','test')):
            run_dir=point.parent.parent
            config=rows(run_dir/'run_config.csv')[0]
            for key,value in [('train_attempts_per_class',30000),('validation_attempts_per_class',20000),
                              ('test_attempts_per_class',20000),('cells',1000),('samples',300)]:
                if int(config[key])!=value: raise RuntimeError(f'Incompatible sample budget: {run_dir}')
            manifest={line.split(maxsplit=1)[1]:line.split()[0]
                      for line in (run_dir/'method_manifest.sha256').read_text().splitlines()}
            for name in ('src/generate_vector.cpp','src/generate_scalar.cpp','include/DarkBosonKinematics.h',
                         'bin/generate_vector','bin/generate_scalar'):
                if digest(project/name)!=manifest.get(name):
                    raise RuntimeError(f'Generator changed since existing samples: {name}')
            return point
    return None

def run_point(project, output, rep, point_index, rate):
    typ, mass = rate['signal_type'], float(rate['mass_GeV'])
    point = output/f'rep_{rep:03d}'/f'{typ}_m{mass:.3f}'.replace('.', 'p')
    point.mkdir(parents=True, exist_ok=True)
    if (point/'complete.json').exists():
        return str(point)
    print('START',point,flush=True)
    if shutil.disk_usage(output).free < 4*1024**3:
        raise RuntimeError('Less than 4 GiB free; stopped before generating new samples')
    old = find_existing(project, rep, typ, mass)
    data = point/'data'; data.mkdir(exist_ok=True)
    block = 19500000 + rep*10000 + point_index*100
    cuts = next(r for r in rows(BASE/'config/paper_cuts.csv') if abs(float(next(iter(r.values())))-mass)<1e-8)
    cut_values = list(cuts.values())[1:6]
    provenance = {}

    def prepare(split):
        events = 30000 if split == 'train' else 20000
        offset = dict(train=1,validation=2,test=3)[split]
        for kind in ('signal','photon'):
            target = data/f'{kind}_{split}.root'
            if old:
                source = old/'data'/target.name
                if not target.exists(): target.symlink_to(source)
                provenance[target.name] = dict(source=str(source), sha256=digest(source), reused=True)
                continue
            photon = kind == 'photon'
            seed = block + offset + (10 if photon else 0)
            process = 'vector' if photon else typ
            gen_mass = 1e-6 if photon else mass
            coupling = .3028221209 if photon else .0001
            args = [project/'bin'/f'generate_{process}', '--mass', gen_mass,
                    '--events',events,'--cells',1000,'--samples',300,'--seed',seed,'--output',target]
            if photon: args += ['--cut-mass',mass,'--coupling',coupling]
            args += ['--integrate-paper-cut','--quiet'] if process == 'vector' else ['--selected']
            command(args,point/'logs'/f'{kind}_{split}.log',data/f'{kind}_{split}.generated.json')
            validate = [project/'bin/validate_sealed_sample', target, *cut_values,
                        int(photon),100,process,gen_mass,mass,coupling,seed,events,1000,300]
            command(validate,point/'logs'/f'{kind}_{split}_check.log',data/f'{kind}_{split}.validated.json')
            provenance[target.name] = dict(source=str(target),sha256=digest(target),seed=seed,reused=False)

    prepare('train'); prepare('validation')
    sx, px, dx = (rate[k] for k in ('signal_xs_pb','photon_xs_pb','dis_xs_pb'))
    for feature in FEATURES:
        dest = point/feature; dest.mkdir(exist_ok=True)
        for method, profiles in [('bdt',PROFILES), ('likelihood',LIKELIHOODS)]:
            candidates = []
            for profile in profiles:
                model = dest/method/profile; model.mkdir(parents=True,exist_ok=True)
                executable = project/'bin/train_tmva' if method=='bdt' else BASE/'bin/train_likelihood'
                args = [executable,data/'signal_train.root',data/'signal_validation.root',
                        data/'photon_train.root',data/'photon_validation.root',model,typ,mass,sx,px,dx,
                        feature,profile,block+31,'validation_all']
                command(args,model/'run.log',model/'trained.json')
                candidates.append(rows(model/'metrics.csv')[0])
                # TMVA's diagnostic trees duplicate the input data. XML/sidecars retain the model.
                training = model/'training.root'
                if training.exists(): training.unlink()
            selected = max(candidates, key=lambda r: float(r['validation_significance_improvement']))
            write_csv(dest/f'{method}_candidates.csv',candidates)
            write_csv(dest/f'{method}_selected.csv',[selected])
        boxes = dest/'boxes'; boxes.mkdir(exist_ok=True)
        candidates = []
        for grid in (40,80,160):
            file = boxes/f'q{grid}.csv'
            args = [project/'bin/optimize_rectangular_fair',data/'signal_train.root',data/'photon_train.root',
                    data/'signal_validation.root',data/'photon_validation.root',
                    data/'signal_validation.root',data/'photon_validation.root',file,typ,mass,sx,px,dx,
                    feature,grid,20,block+21]
            command(args,boxes/f'q{grid}.log',boxes/f'q{grid}.done.json')
            candidates.append(rows(file)[0])
        selected = max(candidates, key=lambda r:(float(r['validation_significance_improvement']),
                                                   float(r['training_significance_improvement'])))
        write_csv(dest/'cuts_selected.csv',[selected])
    # All six selections are now fixed; only now generate/read the independent test samples.
    prepare('test')
    (point/'samples.json').write_text(json.dumps(provenance,indent=2))
    for feature in FEATURES:
        dest = point/feature
        for method in ('bdt','likelihood'):
            selected = rows(dest/f'{method}_selected.csv')[0]['model_profile']
            tag = 'BDTG' if method=='bdt' else 'PDERS'
            weights = dest/method/selected/'dataset/weights'/f'TMVAClassification_{tag}.weights.xml'
            if not weights.exists() and weights.with_suffix('.xml.gz').exists():
                with gzip.open(weights.with_suffix('.xml.gz'),'rb') as src, weights.open('wb') as dst:
                    shutil.copyfileobj(src,dst)
            args = [BASE/'bin/evaluate_three_way',data/'signal_test.root',data/'photon_test.root',
                    weights,dest/f'{method}_selected.csv',dest/'cuts_selected.csv',dest/f'{method}_test.csv',
                    feature,px,dx,2000,block+22]
            command(args,dest/f'{method}_test.log',dest/f'{method}_evaluated.json')
        # Both evaluators use exactly the same event order and bootstrap seed.
        a,b = [rows(dest/f'{m}_test_bootstrap.csv') for m in ('bdt','likelihood')]
        if len(a)!=2000 or len(b)!=2000: raise RuntimeError('Missing bootstrap draws; cannot pair safely')
        paired=[]
        for x,y in zip(a,b):
            if x['replicate']!=y['replicate']: raise RuntimeError('Bootstrap alignment failure')
            paired.append(dict(replicate=x['replicate'],bdt_over_cuts=x['RZ_ratio'],
                               likelihood_over_cuts=y['RZ_ratio'],
                               bdt_over_likelihood=float(x['RZ_ratio'])/float(y['RZ_ratio'])))
        write_csv(dest/'paired_ratios.csv',paired)
        for weights in dest.glob('*/**/*.weights.xml'):
            compressed=weights.with_suffix('.xml.gz')
            with weights.open('rb') as src, gzip.open(compressed,'wb') as dst:
                shutil.copyfileobj(src,dst)
            if digest(weights) != hashlib.sha256(gzip.decompress(compressed.read_bytes())).hexdigest():
                raise RuntimeError('Compressed model verification failed')
            weights.unlink()
    (point/'complete.json').write_text(json.dumps(dict(rate=rate,replicate=rep,seed_block=block)))
    print('COMPLETE',point,flush=True)
    return str(point)

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--project',type=Path,default=Path(os.environ.get('DARK_PROJECT_ROOT', str(Path(__file__).resolve().parents[2]))))
    parser.add_argument('--output',type=Path,default=BASE/'results')
    parser.add_argument('--workers',type=int,default=2)
    parser.add_argument('--pilot',action='store_true',help='First vector 10 GeV run, both input sets')
    args=parser.parse_args(); args.output=args.output.resolve(); args.output.mkdir(parents=True,exist_ok=True)
    rates=rows(BASE/'config/rates.csv')
    files=[Path(__file__),BASE/'docs/protocol.md',BASE/'scripts/summarize.py',BASE/'src/train_likelihood.cpp',BASE/'bin/train_likelihood',
           BASE/'src/evaluate_three_way.cpp',BASE/'bin/evaluate_three_way',
           BASE/'config/rates.csv',BASE/'config/paper_cuts.csv']
    files += [args.project/'bin'/name for name in ('train_tmva','evaluate_fair_model',
               'generate_vector','generate_scalar','optimize_rectangular_fair','validate_sealed_sample')]
    manifest={str(f):digest(f) for f in files}
    target=args.output/'method_manifest.json'
    if target.exists() and json.loads(target.read_text())!=manifest:
        raise RuntimeError('Code or configuration changed; start a new results directory')
    target.write_text(json.dumps(manifest,indent=2))
    tasks=[(rep,i,r) for rep in range(1,11) for i,r in enumerate(rates)]
    if args.pilot: tasks=[t for t in tasks if t[0]==1 and t[2]['signal_type']=='vector' and float(t[2]['mass_GeV'])==10]
    with concurrent.futures.ThreadPoolExecutor(max_workers=args.workers) as pool:
        futures=[pool.submit(run_point,args.project,args.output,*t) for t in tasks]
        try:
            for future in concurrent.futures.as_completed(futures): future.result()
        except BaseException:
            for future in futures: future.cancel()
            raise

if __name__=='__main__': main()
