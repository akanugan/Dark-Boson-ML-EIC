#!/usr/bin/env python3
"""Plot completed aggregate comparisons; do not substitute single-run results."""
import argparse
import os
os.environ.setdefault('MPLCONFIGDIR','/tmp/dark-mpl-cache')
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from run_comparison import rows

p=argparse.ArgumentParser();p.add_argument('results',type=Path);args=p.parse_args()
summary=args.results/'summary.csv'
if not summary.exists():raise SystemExit('No complete ten-run groups to plot.')
data=rows(summary)
fig,axes=plt.subplots(2,2,figsize=(12,8),sharex=True,constrained_layout=True)
for i,typ in enumerate(('vector','scalar')):
    for j,feature in enumerate(('electron','electron_qa2')):
        ax=axes[i,j]
        for pair,label,marker in [('bdt_over_cuts','BDT / cuts','o'),
                                   ('likelihood_over_cuts','Likelihood / cuts','s'),
                                   ('bdt_over_likelihood','BDT / likelihood','^')]:
            selected=sorted([r for r in data if r['signal_type']==typ and r['feature_set']==feature and r['comparison']==pair],key=lambda r:float(r['mass_GeV']))
            if not selected:continue
            x=[float(r['mass_GeV']) for r in selected]
            y=[100*(float(r['geometric_mean_ratio'])-1) for r in selected]
            lo=[100*(float(r['ci95_low'])-1) for r in selected]
            hi=[100*(float(r['ci95_high'])-1) for r in selected]
            line,=ax.plot(x,y,marker=marker,label=label)
            ax.vlines(x,lo,hi,alpha=.6,color=line.get_color())
        ax.axhline(0,color='black',linewidth=.7)
        ax.set_xscale('log');ax.grid(alpha=.2)
        ax.set_title(f'{typ.capitalize()}: '+('electron inputs' if j==0 else 'electron inputs + t'))
        ax.set_ylabel('Significance ratio advantage (%)')
        ax.set_xlabel('Boson mass (GeV)');ax.legend(fontsize=8)
counts=sorted({int(r['independent_runs']) for r in data})
run_note=('Ten independent runs per point' if counts==[10] else '20 runs at vector 0.032 GeV; 10 runs elsewhere (targeted follow-up)')
fig.suptitle('Three-method comparison — '+run_note+'\nBars: pointwise 95% intervals',fontsize=11)
fig.savefig(args.results/'comparison.png',dpi=180)

fig.savefig(args.results/'comparison.pdf')
