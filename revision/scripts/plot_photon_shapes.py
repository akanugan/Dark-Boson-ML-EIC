from pathlib import Path
import csv
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
BASE=Path(__file__).resolve().parents[1];OUT=BASE/'photon_shape_test'
with (OUT/'shape_comparison.csv').open() as f:r=list(csv.DictReader(f))
fig,axes=plt.subplots(1,2,figsize=(10,3.6),layout='constrained')
for ax,obs,label in zip(axes,['pt','eta'],[r'$\log_{10}(p_{T,e}/\mathrm{GeV})$',r'$\eta_e$']):
 a=[v for v in r if v['observable']==obs];edges=np.array([float(v['low']) for v in a]+[float(a[-1]['high'])]);p=np.array([float(v['reference_probability']) for v in a]);q=np.array([float(v['proxy_probability']) for v in a]);z=q*np.array([float(v['factor']) for v in a]);z/=z.sum()
 for y,c,l in [(p,'black','Older reference ancillary'),(q,'#2878b5','Our inclusive simulation'),(z,'#df7926','Bounded marginal variation')]:ax.stairs(y,edges,color=c,label=l,lw=1.6)
 ax.set(xlabel=label,ylabel='Probability per bin (within shown range)',yscale='log',ylim=(1e-8,1));ax.grid(alpha=.15)
 ax.set_title(f"Original TV distance: {float(a[0]['range_TV']):.3f}; outside: {100*float(a[0]['proxy_outside_fraction']):.1f}%",fontsize=10)
axes[0].legend(fontsize=8);fig.savefig(OUT/'shape_comparison.png',dpi=180);fig.savefig(OUT/'shape_comparison.pdf');plt.close(fig)
with (OUT/'summary.csv').open() as f:r=list(csv.DictReader(f))
sc=['baseline','pt_half','pt_full','eta_half','eta_full','joint_half','joint_full'];labels=['Baseline',r'$p_T$: half',r'$p_T$: full',r'$\eta$: half',r'$\eta$: full','Combined: half','Combined: full']
fig,axes=plt.subplots(1,2,figsize=(11,4.8),sharey=True,layout='constrained')
for ax,typ in zip(axes,['vector','scalar']):
 for pair,offset,color in [('BDT/cuts',-.12,'#2878b5'),('likelihood/cuts',.12,'#df7926')]:
  a=[next(v for v in r if v['boson']==typ and v['scenario']==s and v['comparison']==pair) for s in sc];x=np.array([float(v['advantage_pct']) for v in a]);lo=np.array([float(v['ci95_low']) for v in a]);hi=np.array([float(v['ci95_high']) for v in a]);ax.errorbar(x,np.arange(7)+offset,xerr=[x-lo,hi-x],fmt='o',capsize=3,color=color,label=pair)
 ax.axvline(0,color='gray',lw=1);ax.set(xlabel='Significance advantage over cuts (%)',title=f'{typ.capitalize()}, 10 GeV',yticks=np.arange(7),yticklabels=labels);ax.grid(axis='x',alpha=.2);ax.legend(fontsize=9)
axes[0].invert_yaxis();fig.suptitle('Fixed selectors; fixed photon rate; pointwise 95% intervals',fontsize=11);fig.savefig(OUT/'shape_sensitivity.png',dpi=180);fig.savefig(OUT/'shape_sensitivity.pdf')
