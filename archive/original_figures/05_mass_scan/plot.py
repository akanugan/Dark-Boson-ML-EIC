import csv
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
ROOT=Path(__file__).resolve().parent
OUT=ROOT
def rows(p):
 with open(p) as f:return list(csv.DictReader(f))
plt.rcParams.update({'font.size':9,'axes.titlesize':10,'axes.labelsize':9,'legend.fontsize':8,'pdf.fonttype':42})
data=rows(ROOT/'data/metrics.csv')
fig,axs=plt.subplots(1,2,figsize=(7.4,3.15),sharey=True,layout='constrained')
for ax,signal,panel in zip(axs,['vector','scalar'],['(a)','(b)']):
 for fs,color,label in [('electron','#222222','Electron inputs'),('electron_qa2','#2563eb',r'Electron inputs + $t$')]:
  sub=sorted([r for r in data if r['signal_type']==signal and r['feature_set']==fs],key=lambda r:float(r['mass_GeV']))
  x=[float(r['mass_GeV']) for r in sub]; y=[100*float(r['coupling_advantage']) for r in sub]
  lo=[v-100*float(r['coupling_q025']) for v,r in zip(y,sub)]; hi=[100*float(r['coupling_q975'])-v for v,r in zip(y,sub)]
  ax.errorbar(x,y,yerr=[lo,hi],fmt='o-',ms=3,lw=1,capsize=2,color=color,label=label)
 ax.set(xscale='log',xlim=(.008,12),ylim=(-.5,1.75),xlabel=r'Boson mass $m_\phi$ [GeV]',title=f'{panel} {signal.capitalize()}')
 ax.axhline(0,color='gray',lw=.7); ax.axhline(1,color='gray',ls=':',lw=1)
 ax.grid(alpha=.18);ax.legend(loc='upper left',frameon=False)
axs[0].set_ylabel('BDT coupling advantage over cuts [%]')
fig.savefig(OUT/'figure.pdf');fig.savefig(OUT/'figure.png',dpi=220);plt.close(fig)
