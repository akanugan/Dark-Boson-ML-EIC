from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
import subprocess,json,time
base=Path(__file__).resolve().parents[1];out=base/'photon_loss_10gev/pilot';out.mkdir(exist_ok=True)
config=[('central',921001),('outside',921002)]
def job(cfg):
 region,seed=cfg;args=[base/'bin/generate_photon_regions','--mass','0.000001','--cut-mass','10','--coupling','0.3028221209','--events','5000','--cells','500','--samples','500','--seed',str(seed),'--photon-region',region,'--integrate-paper-cut','--quiet','--output',out/f'{region}.root'];st=time.time()
 with (out/f'{region}.log').open('w') as f:
  f.write(json.dumps(list(map(str,args)))+'\n');f.flush();p=subprocess.run(list(map(str,args)),stdout=f,stderr=subprocess.STDOUT)
 print(region,p.returncode,round(time.time()-st,2),flush=True)
with ThreadPoolExecutor(max_workers=4) as pool:list(pool.map(job,config))
