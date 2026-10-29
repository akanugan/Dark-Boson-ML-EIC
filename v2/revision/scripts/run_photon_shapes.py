#!/usr/bin/env python3
"""Fixed-selector background-shape stress tests based on old ancillary marginals."""
import os
os.environ['OPENBLAS_NUM_THREADS']='1';os.environ['VECLIB_MAXIMUM_THREADS']='1'
import csv,gzip,json,math,subprocess,time
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor,as_completed
import numpy as np
BASE=Path(__file__).resolve().parents[1];OUT=BASE/'photon_shape_test'
SCENARIOS=['baseline','pt_half','pt_full','eta_half','eta_full','joint_half','joint_full']
def rows(p):
 with p.open() as f:return list(csv.DictReader(f))
def write(p,r):
 with p.open('w') as f:
  w=csv.DictWriter(f,fieldnames=list(r[0]));w.writeheader();w.writerows(r)
def prepare():
 a=np.genfromtxt(OUT/'reference/inclusive.csv',delimiter=',',names=True)
 tables={}; diagnostics=[]
 for name,key,width in [('pt','logpt',.5),('eta','eta',1.)]:
  ref=np.loadtxt(OUT/f'reference/Fig4_{name}_photon.dat');edges=np.r_[ref[:,0],ref[-1,0]+width]
  x=np.log10(a['pt']) if name=='pt' else a['eta'];w=a['weight']
  h=np.histogram(x,edges,weights=w)[0];h2=np.histogram(x,edges,weights=w*w)[0];q=h/h.sum();p=ref[:,1]/ref[:,1].sum()
  # Sparse/unrepresented tails make exact ratio matching unstable: explicitly bounded deformation.
  factor=np.divide(p,q,out=np.ones_like(p),where=q>0);factor=np.clip(factor,.2,5.)
  tables[name]=(edges,factor)
  outside=1-h.sum()/w.sum();tv=.5*np.abs(p-q).sum()
  for i in range(len(p)):
   diagnostics.append(dict(observable=name,low=edges[i],high=edges[i+1],reference_probability=p[i],proxy_probability=q[i],factor=factor[i],neff=h[i]**2/h2[i] if h2[i]>0 else 0,range_TV=tv,proxy_outside_fraction=outside))
 write(OUT/'shape_comparison.csv',diagnostics)
 return tables

def factors(a,tables):
 fs=[]
 for name,col in [('pt','logpt'),('eta','eta')]:
  edges,f=tables[name];idx=np.searchsorted(edges,a[col],side='right')-1;inside=(idx>=0)&(idx<len(f));v=np.ones(len(a));v[inside]=f[idx[inside]];fs.append(v)
 p,e=fs;j=np.clip(p*e,.2,5.)
 return np.column_stack([np.ones(len(a)),(1+p)/2,p,(1+e)/2,e,(1+j)/2,j])

def job(typ,rep,tables):
 st=time.time();src=BASE/'results'/f'rep_{rep:03d}'/f'{typ}_m10p000';sel=src/'electron_qa2';dst=OUT/f'rep_{rep:03d}'/typ;dst.mkdir(parents=True,exist_ok=True)
 sets={}
 for m,tag in [('bdt','BDTG'),('likelihood','PDERS')]:
  cfg=rows(sel/f'{m}_selected.csv')[0];model=sel/m/cfg['model_profile']/'dataset/weights'/f'TMVAClassification_{tag}.weights.xml';local=dst/f'{m}.xml'
  local.write_bytes(model.read_bytes() if model.exists() else gzip.decompress(model.with_suffix('.xml.gz').read_bytes()))
  args=[BASE/'bin/export_shape_scores',src/'data/signal_test.root',src/'data/photon_test.root',local,sel/f'{m}_selected.csv',sel/'cuts_selected.csv',dst/m,'electron_qa2',cfg['photon_xs_pb'],cfg['dis_xs_pb']]
  with (dst/f'{m}.log').open('w') as f:subprocess.run(list(map(str,args)),stdout=f,stderr=subprocess.STDOUT,check=True)
  local.unlink();sets[m]=[np.genfromtxt(dst/f'{m}_{k}.csv',delimiter=',',names=True) for k in ['signal','photon']]
 for k in [0,1]:
  for col in ['weight','logpt','eta','logt','cuts_pass']:
   if not np.array_equal(sets['bdt'][k][col],sets['likelihood'][k][col]):raise RuntimeError('event pairing mismatch')
 s,b=sets['bdt'];px=float(cfg['photon_xs_pb']);dx=float(cfg['dis_xs_pb'])
 sp=np.column_stack([s['model_pass'],sets['likelihood'][0]['model_pass'],s['cuts_pass']]);bp=np.column_stack([b['model_pass'],sets['likelihood'][1]['model_pass'],b['cuts_pass']])
 fac=factors(b,tables);bw=b['weight'][:,None]*fac;sw=s['weight'];se=(sw[:,None]*sp).sum(0)/sw.sum();be=(bw[:,:,None]*bp[:,None,:]).sum(0)/bw.sum(0)[:,None]
 rz=se[None,:]*np.sqrt((px+dx)/(px*be+dx))
 for i,m in enumerate(['bdt','likelihood']):
  orig=rows(sel/f'{m}_test.csv')[0]
  for val,key in [(rz[0,i],'bdt_RZ'),(rz[0,2],'box_RZ')]:
   if not math.isclose(val,float(orig[key]),rel_tol=1e-9):raise RuntimeError('baseline mismatch')
 # Pair all methods/scenarios under the same ordinary event bootstrap resamples.
 rng=np.random.default_rng(991000+rep+(10000 if typ=='scalar' else 0));bootstrap=[]
 sm=np.column_stack([sw,sw[:,None]*sp]);bm=np.column_stack([bw,(bw[:,:,None]*bp[:,None,:]).reshape(len(b),-1)])
 for start in range(0,2000,100):
  sc=rng.multinomial(len(s),np.full(len(s),1/len(s)),size=100)@sm
  bc=rng.multinomial(len(b),np.full(len(b),1/len(b)),size=100)@bm
  seb=sc[:,1:]/sc[:,:1];beb=bc[:,7:].reshape(100,7,3)/bc[:,:7,None]
  r=seb[:,None,:]*np.sqrt((px+dx)/(px*beb+dx));bootstrap.append(np.stack([r[:,:,0]/r[:,:,2],r[:,:,1]/r[:,:,2],r[:,:,0]/r[:,:,1]],axis=2))
 boot=np.concatenate(bootstrap);np.save(dst/'bootstrap_ratios.npy',boot)
 nominal=np.column_stack([rz[:,0]/rz[:,2],rz[:,1]/rz[:,2],rz[:,0]/rz[:,1]]);np.save(dst/'nominal_ratios.npy',nominal)
 rec=[]
 for i,name in enumerate(SCENARIOS):
  rec.append(dict(boson=typ,rep=rep,scenario=name,bdt_RZ=rz[i,0],likelihood_RZ=rz[i,1],cuts_RZ=rz[i,2],photon_neff=bw[:,i].sum()**2/(bw[:,i]**2).sum(),max_weight_fraction=bw[:,i].max()/bw[:,i].sum(),mean_shape_factor=bw[:,i].sum()/bw[:,0].sum()))
 write(dst/'metrics.csv',rec);(dst/'complete.json').write_text(json.dumps({'seconds':time.time()-st}))
 return rec

def main():
 tables=prepare()
 plan={'purpose':'shape-only stress test at 10 GeV, fixed trained selectors','reference':'old arXiv v2 ancillary marginals used for manuscript Figure 3; v4 source inspected, no numeric ancillary histograms present','construction':'inclusive reference/proxy normalized-bin probability ratio; clip each marginal ratio to [0.2,5]; leave uncovered or zero-proxy bins at 1; joint is clipped product, not a fitted reference joint density; half variations interpolate factors halfway to 1','normalization':'photon effective rate fixed by renormalizing varied weights after preselection; signal and DIS unchanged','fit_sample':'independent historical inclusive calibration sample, no test labels/selection outcomes used to choose variations','limits':'bounded sensitivity envelope, not exact reference matching or proof of background validity; unconstrained correlations remain; reference/calibration uncertainties not included','workers':4,'runs_per_boson':10,'bootstrap':'2000 paired event resamples per run, 20000 run-and-event aggregate draws, pointwise 95% intervals'}
 (OUT/'plan.json').write_text(json.dumps(plan,indent=2));done=[];errors=[]
 def status(state):(OUT/'status.json').write_text(json.dumps({'state':state,'completed':len(done)//7,'total':20,'errors':errors},indent=2))
 status('running')
 with ThreadPoolExecutor(max_workers=4) as pool:
  fs={pool.submit(job,t,r,tables):(t,r) for t in ['vector','scalar'] for r in range(1,11)}
  for f in as_completed(fs):
   try:done.extend(f.result());print('Completed',len(done)//7,'/20',fs[f],flush=True)
   except Exception as e:errors.append(str(e));print('FAILED',fs[f],str(e),flush=True)
   status('running')
 if errors:status('failed');return
 write(OUT/'run_results.csv',done);summary=[];rng=np.random.default_rng(108826)
 for typ in ['vector','scalar']:
  dirs=[OUT/f'rep_{r:03d}'/typ for r in range(1,11)];boot=np.log(np.array([np.load(p/'bootstrap_ratios.npy') for p in dirs]));nom=np.log(np.array([np.load(p/'nominal_ratios.npy') for p in dirs]))
  ix=rng.integers(0,10,(20000,10));jx=rng.integers(0,2000,(20000,10));dist=100*np.expm1(boot[ix,jx].mean(1));point=100*np.expm1(nom.mean(0))
  for i,name in enumerate(SCENARIOS):
   for j,pair in enumerate(['BDT/cuts','likelihood/cuts','BDT/likelihood']):
    lo,hi=np.quantile(dist[:,i,j],[.025,.975]);summary.append(dict(boson=typ,scenario=name,comparison=pair,advantage_pct=point[i,j],ci95_low=lo,ci95_high=hi))
 write(OUT/'summary.csv',summary);status('complete')
if __name__=='__main__':main()
