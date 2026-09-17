import csv
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
OUT=Path(__file__).resolve().parent
def rows(p):
 with open(p) as f:return list(csv.DictReader(f))
plt.rcParams.update({'font.size':9,'axes.titlesize':10,'axes.labelsize':9,'legend.fontsize':8,'pdf.fonttype':42})
fig,axs=plt.subplots(1,2,figsize=(7.4,3.0),layout='constrained',gridspec_kw={'width_ratios':[1.15,1]})
for ax,fp,order,title,color in [
 (axs[0],'seed_robustness/run_20260814T063518Z', [('vector',1.),('vector',10.),('scalar',1.),('scalar',6.31)],'(a) Electron inputs','#222222'),
 (axs[1],'t_seed_robustness/run_t_20260820_final',[('vector',10.),('scalar',10.)],r'(b) Electron inputs + $t$','#2563eb')]:
 lookup={(r['signal_type'],float(r['mass_GeV'])):r for r in rows(OUT/'data'/('electron.csv' if fp.startswith('seed_robustness/') else 'with_t.csv'))}
 ys=list(range(len(order)))
 for y,key in zip(ys,order):
  r=lookup[key];m=100*float(r['hierarchical_coupling_q50']);lo=100*float(r['hierarchical_coupling_q025']);hi=100*float(r['hierarchical_coupling_q975'])
  ax.errorbar(m,y,xerr=[[m-lo],[hi-m]],fmt='o',ms=5,capsize=3,color=color)
 ax.set_yticks(ys,[f'{s.capitalize()}, {m:g} GeV' for s,m in order]);ax.invert_yaxis()
 ax.set_title(title); ax.set_xlabel('BDT coupling advantage [%]');ax.grid(axis='x',alpha=.22)
 ax.set_ylim(len(order)-.45,-.55)
axs[0].set_xlim(-.22,.22);axs[0].axvline(0,color='gray',lw=.8)
axs[1].set_xlim(.8,1.65);axs[1].axvline(1,color='gray',ls=':',lw=1)
fig.savefig(OUT/'figure.pdf');fig.savefig(OUT/'figure.png',dpi=220)
