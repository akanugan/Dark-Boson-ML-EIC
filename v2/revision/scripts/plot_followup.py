"""Combine targeted follow-up with original results without discarding runs."""
import os
os.environ.setdefault('MPLCONFIGDIR','/tmp/dark-mpl-cache')
from pathlib import Path
import json
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from run_comparison import BASE, rows, write_csv
PAIRS=('bdt_over_cuts','likelihood_over_cuts','bdt_over_likelihood')
LABELS=('BDT / cuts','Likelihood / cuts','BDT / likelihood')
out=BASE/'updated_results';out.mkdir(exist_ok=True)
old=BASE/'results';new=BASE/'wide_interval_reruns'
assert json.loads((new/'status.json').read_text())['completed_points']==10
summaries=rows(old/'summary.csv'); diagnostics=[]

def read_run(root,rep,feature):
 p=root/f'rep_{rep:03d}'/'vector_m0p032'/feature
 a,b=[rows(p/f'{m}_test.csv')[0] for m in ('bdt','likelihood')]
 nominal=[float(a['RZ_ratio']),float(b['RZ_ratio']),float(a['RZ_ratio'])/float(b['RZ_ratio'])]
 draws=[[float(r[k]) for k in PAIRS] for r in rows(p/'paired_ratios.csv')]
 return nominal,draws

def summarize(records,feature,label,seed):
 nominal=np.array([r[0] for r in records]); draws=np.array([r[1] for r in records]); n=len(records)
 rng=np.random.default_rng(seed); boot=np.empty((200000,3))
 for start in range(0,len(boot),2000):
  ri=rng.integers(0,n,(2000,n));ei=rng.integers(0,draws.shape[1],(2000,n))
  boot[start:start+2000]=np.exp(np.mean(np.log(draws[ri,ei]),axis=1))
 center=np.exp(np.mean(np.log(nominal),axis=0)); result=[]
 for j,pair in enumerate(PAIRS):
  lo,hi=np.quantile(boot[:,j],[.025,.975]);flo,fhi=np.quantile(boot[:,j],[.025/132,1-.025/132])
  result.append(dict(signal_type='vector',mass_GeV=.032,feature_set=feature,comparison=pair,
   geometric_mean_ratio=center[j],ci95_low=lo,ci95_high=hi,simultaneous_low=flo,simultaneous_high=fhi,
   family_size=132,independent_runs=n,resamples=200000))
  diagnostics.append(dict(batch=label,**result[-1]))
 return result

for i,feature in enumerate(('electron','electron_qa2')):
 original=[read_run(old,r,feature) for r in range(1,11)]
 added=[read_run(new,r,feature) for r in range(11,21)]
 summarize(original,feature,'Original 10',32000000+i)
 summarize(added,feature,'New 10',33000000+i)
 combined=summarize(original+added,feature,'All 20',34000000+i)
 summaries=[r for r in summaries if not(r['signal_type']=='vector' and float(r['mass_GeV'])==.032 and r['feature_set']==feature)]
 summaries.extend(combined)
write_csv(out/'summary.csv',summaries);write_csv(out/'followup_summary.csv',diagnostics)
(out/'README.md').write_text('Updated comparison: original ten runs retained at every point; ten additional runs included at vector 0.032 GeV for both input sets. This is a targeted follow-up selected after inspecting original uncertainty, not a new prespecified scan. Pointwise intervals are descriptive; fixed-family bounds do not correct for adaptive follow-up selection. Original data remain in ../results.\n')
fig,axes=plt.subplots(1,2,figsize=(12,5),constrained_layout=True)
for ax,feature in zip(axes,('electron','electron_qa2')):
 for j,(pair,label) in enumerate(zip(PAIRS,LABELS)):
  data=[next(r for r in diagnostics if r['feature_set']==feature and r['comparison']==pair and r['batch']==batch) for batch in ('Original 10','New 10','All 20')]
  x=np.arange(3)+(j-1)*.15;y=np.array([100*(r['geometric_mean_ratio']-1) for r in data])
  lo=np.array([100*(r['ci95_low']-1) for r in data]);hi=np.array([100*(r['ci95_high']-1) for r in data])
  line,=ax.plot(x,y,'o',label=label);ax.vlines(x,lo,hi,color=line.get_color())
 ax.set_xticks(range(3),('Original 10','New 10','All 20'));ax.axhline(0,color='black',lw=.7)
 ax.set_title('Electron inputs'+(' + t' if feature=='electron_qa2' else ''));ax.set_ylabel('Significance ratio advantage (%)');ax.grid(alpha=.2);ax.legend(fontsize=8)
fig.suptitle('Vector, 0.032 GeV: independent follow-up\nBars: pointwise 95% intervals')
for ext in ('png','pdf'):fig.savefig(out/f'followup.{ext}',dpi=180)
print(json.dumps([r for r in diagnostics if r['feature_set']=='electron_qa2' and r['comparison']=='likelihood_over_cuts'],indent=2))
