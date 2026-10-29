#!/usr/bin/env python3
"""Shape diagnostics and performance plots for the documented loss scenarios."""
import os
os.environ['MPLCONFIGDIR']='/tmp/dark-mpl-cache'
from pathlib import Path
import csv
import json
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

BASE=Path(__file__).resolve().parents[1]
OUT=BASE/'photon_loss_10gev'
EPS=[1e-8,1e-7,1e-6,1e-5]
COLORS=['#6a3d9a','#1b9e77','#2878b5','#df7926']
EDGES={'logt':np.r_[-np.inf,np.arange(-8,2.001,.25),np.inf],
       'pt':np.r_[-np.inf,np.linspace(1.3,10,30),np.inf],
       'eta':np.r_[-np.inf,np.linspace(-1.5,3,31),np.inf]}

def write(path,rows):
    with path.open('w') as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)

def main():
    stages=['Table_I']+[f'{t}_{m}' for t in ['vector','scalar'] for m in ['BDT','likelihood','cuts']]
    hist={}; component={}; ranges={}
    for region in ['central','outside']:
        component[region]=0.
        for rep in range(1,11):
            dst=OUT/f'rep_{rep:03d}'
            arrays={t:{m:np.genfromtxt(dst/t/f'{m}_{region}_photon.csv',delimiter=',',names=True)
                       for m in ['bdt','likelihood']} for t in ['vector','scalar']}
            a=arrays['vector']['bdt'];raw=a['weight']/(1e-6 if region=='central' else 1)/10
            component[region]+=raw.sum()
            x={'logt':a['logt'],'pt':10**a['logpt'],'eta':a['eta']}
            for stage in stages:
                if stage=='Table_I':mask=np.ones(len(a),dtype=bool)
                else:
                    typ,method=stage.split('_')
                    mask=arrays[typ]['likelihood' if method=='likelihood' else 'bdt']['model_pass' if method!='cuts' else 'cuts_pass'].astype(bool)
                weights=raw*mask
                for obs,edge in EDGES.items():
                    key=(region,stage,obs)
                    h=np.histogram(x[obs],bins=edge,weights=weights)[0]
                    hist[key]=hist.get(key,0)+h
                key=(region,stage,'joint_pt_logt')
                h=np.histogram2d(x['pt'],x['logt'],bins=[EDGES['pt'],EDGES['logt']],weights=weights)[0]
                hist[key]=hist.get(key,0)+h
    diagnostics=[];hist_rows=[];rates=[]
    for ei,e in enumerate(EPS):
        rate=e*component['central']+component['outside']
        rates.append(dict(epsilon=e,central_raw_pb=component['central'],outside_raw_pb=component['outside'],
                          effective_photon_rate_pb=rate,outside_fraction=component['outside']/rate))
    for stage in stages:
        for obs in list(EDGES)+['joint_pt_logt']:
            c=hist['central',stage,obs];o=hist['outside',stage,obs]
            hn=1e-6*c+o;pn=hn/hn.sum()
            for e in EPS:
                h=e*c+o;p=h/h.sum()
                diagnostics.append(dict(stage=stage,observable=obs,epsilon=e,
                    TV_to_nominal=.5*np.abs(p-pn).sum(),selected_photon_rate_pb=h.sum(),
                    outside_fraction=o.sum()/h.sum(),
                    underflow_fraction=p[0] if p.ndim==1 else '',
                    overflow_fraction=p[-1] if p.ndim==1 else ''))
                if obs in EDGES:
                    for i,value in enumerate(p):
                        hist_rows.append(dict(stage=stage,observable=obs,epsilon=e,
                            bin_low=EDGES[obs][i],bin_high=EDGES[obs][i+1],probability=value))
    write(OUT/'scenario_rates.csv',rates)
    write(OUT/'shape_distances.csv',diagnostics)
    write(OUT/'shape_histograms.csv',hist_rows)
    np.savez_compressed(OUT/'component_histograms.npz',**{'__'.join(k):v for k,v in hist.items()})
    fig,axes=plt.subplots(1,3,figsize=(12,3.6),layout='constrained')
    labels={'logt':r'$\log_{10}(t/\mathrm{GeV}^2)$','pt':r'$p_{T,e}$ (GeV)','eta':r'$\eta_e$'}
    for ax,(obs,edge) in zip(axes,EDGES.items()):
        c=hist['central','Table_I',obs];o=hist['outside','Table_I',obs]
        for e,color in zip(EPS,COLORS):
            h=e*c+o;p=h/h.sum()
            ax.stairs(p[1:-1],edge[1:-1],label=rf'$\epsilon=10^{{{int(np.log10(e))}}}$',color=color,lw=1.6)
        ax.set(xlabel=labels[obs],ylabel='Probability per bin');ax.grid(alpha=.15)
    axes[0].set_xlim(-5,1.5)
    axes[0].legend(fontsize=9)
    fig.suptitle('Photon background after 10 GeV preselection; each scenario normalized to one',fontsize=11)
    for suffix in ['png','pdf']:fig.savefig(OUT/f'shape_changes.{suffix}',dpi=180)
    plt.close(fig)
    with (OUT/'summary.csv').open() as f:summary=list(csv.DictReader(f))
    for mode,title in [('shape_only','Photon rate held fixed'),('rate_and_shape','Photon rate and shape varied'),('rate_only','Photon rate varied; nominal shape held fixed')]:
        fig,axes=plt.subplots(1,2,figsize=(10,4.2),layout='constrained')
        for ax,typ in zip(axes,['vector','scalar']):
            for pair,offset,color in [('BDT/cuts',-.045,'#2878b5'),('likelihood/cuts',.045,'#df7926')]:
                a=[next(r for r in summary if r['mode']==mode and r['boson']==typ and r['comparison']==pair and float(r['epsilon'])==e) for e in EPS]
                y=np.array([float(r['advantage_pct']) for r in a]);lo=np.array([float(r['ci95_low']) for r in a]);hi=np.array([float(r['ci95_high']) for r in a])
                ax.errorbar(np.log10(EPS)+offset,y,yerr=[y-lo,hi-y],fmt='o-',capsize=3,color=color,label=pair)
            ax.axhline(0,color='gray',lw=1);ax.set(xlabel=r'$\log_{10}(\epsilon_{\rm central})$',ylabel='Significance advantage over cuts (%)',title=f'{typ.capitalize()}, 10 GeV',xticks=[-8,-7,-6,-5]);ax.grid(alpha=.15);ax.legend(fontsize=9)
        fig.suptitle(title+'; fixed selectors; pointwise 95% intervals',fontsize=11)
        for suffix in ['png','pdf']:fig.savefig(OUT/f'performance_{mode}.{suffix}',dpi=180)
        plt.close(fig)

if __name__=='__main__':main()
