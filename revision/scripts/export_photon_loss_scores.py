#!/usr/bin/env python3
"""Apply the existing validation-selected models to independent photon strata."""
import csv
import gzip
import hashlib
import json
import subprocess
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

BASE = Path(__file__).resolve().parents[1]
OUT = BASE / 'photon_loss_10gev'

def first(path):
    with path.open() as f:
        return next(csv.DictReader(f))

def job(rep, typ):
    start = time.time()
    src = BASE / 'results' / f'rep_{rep:03d}' / f'{typ}_m10p000'
    sel = src / 'electron_qa2'
    dst = OUT / f'rep_{rep:03d}' / typ
    dst.mkdir(exist_ok=True)
    records = []
    for method, tag in [('bdt', 'BDTG'), ('likelihood', 'PDERS')]:
        cfg = first(sel / f'{method}_selected.csv')
        model = sel / method / cfg['model_profile'] / 'dataset/weights' / f'TMVAClassification_{tag}.weights.xml'
        payload = model.read_bytes() if model.exists() else gzip.decompress(model.with_suffix('.xml.gz').read_bytes())
        local = dst / f'{method}.xml'
        local.write_bytes(payload)
        for region in ['central', 'outside']:
            prefix = dst / f'{method}_{region}'
            cmd = [BASE/'bin/export_shape_scores', src/'data/signal_test.root',
                   OUT/f'rep_{rep:03d}'/f'{region}.root', local,
                   sel/f'{method}_selected.csv', sel/'cuts_selected.csv', prefix,
                   'electron_qa2', cfg['photon_xs_pb'], cfg['dis_xs_pb']]
            with (dst/f'{method}_{region}.log').open('w') as f:
                subprocess.run(list(map(str, cmd)), stdout=f, stderr=subprocess.STDOUT, check=True)
            records.append({'method': method, 'region': region, 'model_profile': cfg['model_profile'],
                            'model_sha256': hashlib.sha256(payload).hexdigest(),
                            'threshold': float(cfg['validation_threshold'])})
        local.unlink()
    (dst/'export_complete.json').write_text(json.dumps({'rep':rep,'boson':typ,'seconds':time.time()-start,'models':records},indent=2))
    return rep, typ

def main():
    done = []
    with ThreadPoolExecutor(max_workers=4) as pool:
        futures = [pool.submit(job, rep, typ) for rep in range(1,11) for typ in ['vector','scalar']]
        for future in as_completed(futures):
            done.append(future.result())
            print('Exported',len(done),'/20',done[-1],flush=True)
            (OUT/'export_status.json').write_text(json.dumps({'completed':len(done),'total':20},indent=2))

if __name__ == '__main__':
    main()
