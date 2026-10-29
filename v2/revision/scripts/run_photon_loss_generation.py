#!/usr/bin/env python3
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor,as_completed
import hashlib,json,re,subprocess,time
BASE=Path(__file__).resolve().parents[1];OUT=BASE/'photon_loss_10gev';OUT.mkdir(exist_ok=True)
def job(rep,region):
 dst=OUT/f'rep_{rep:03d}';dst.mkdir(exist_ok=True);binary=BASE/'bin'/('generate_photon_regions' if region=='central' else 'generate_photon_lab')
 n,c,s=(100000,2500,1500) if region=='central' else (40000,1000,1000)
 seed=923000+rep*10+(0 if region=='central' else 1)
 args=list(map(str,[binary,'--mass',1e-6,'--cut-mass',10,'--coupling',.3028221209,'--events',n,'--cells',c,'--samples',s,'--seed',seed,'--photon-region',region,'--integrate-paper-cut','--quiet','--output',dst/f'{region}.root']))
 signature=hashlib.sha256((json.dumps(args)+hashlib.sha256(binary.read_bytes()).hexdigest()).encode()).hexdigest();marker=dst/f'{region}.json'
 if marker.exists():
  old=json.loads(marker.read_text());assert old['signature']==signature;return old
 st=time.time()
 with (dst/f'{region}.log').open('w') as f:
  f.write(json.dumps(args)+'\n');f.flush();subprocess.run(args,stdout=f,stderr=subprocess.STDOUT,check=True)
 log=(dst/f'{region}.log').read_text();xs=re.search(r'sigma_total_pb=([0-9eE.+-]+) \+/- ([0-9eE.+-]+)',log);entries=re.search(r'accepted_events=(\d+)',log)
 if not xs or not entries or int(entries[1])<1000:raise RuntimeError(f'Invalid integration {rep} {region}')
 row={'rep':rep,'region':region,'signature':signature,'seed':seed,'attempts':n,'entries':int(entries[1]),'sigma_pb':float(xs[1]),'sigma_error_pb':float(xs[2]),'seconds':time.time()-st};marker.write_text(json.dumps(row,indent=2));return row
complete=[];errors=[]
def status(state):(OUT/'generation_status.json').write_text(json.dumps({'state':state,'completed':len(complete),'total':20,'errors':errors},indent=2))
status('running')
with ThreadPoolExecutor(max_workers=4) as pool:
 futures={pool.submit(job,r,g):(r,g) for r in range(1,11) for g in ['central','outside']}
 for f in as_completed(futures):
  try:
   row=f.result();complete.append(row);print('Completed',len(complete),'/20',row,flush=True)
  except Exception as e:errors.append({'job':futures[f],'error':str(e)});print(errors[-1],flush=True)
  status('running')
(OUT/'component_integrations.json').write_text(json.dumps(complete,indent=2));status('complete' if not errors else 'failed')
