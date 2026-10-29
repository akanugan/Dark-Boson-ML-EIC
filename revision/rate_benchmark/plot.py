#!/usr/bin/env python3
"""Show the historical seed-by-seed components and independent component sums."""

import csv
import json
import os
import math
from pathlib import Path

BASE=Path(__file__).resolve().parent
os.environ.setdefault('MPLCONFIGDIR',str(BASE/'.mplconfig'))
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt


def main():
    historical=[json.loads(line) for line in (BASE/'historical_diagnostics.jsonl').read_text().splitlines()]
    with (BASE/'route_summary.csv').open() as handle:
        summary=list(csv.DictReader(handle))
    fig,axes=plt.subplots(1,2,figsize=(13,6))
    fig.subplots_adjust(top=.78,bottom=.17,left=.07,right=.98,wspace=.25)
    for ax,mass,reference in zip(axes,(.032,10.),(2.06,.33)):
        selected=[r for r in historical if f'cut_mass_GeV={mass:g};' in r['configuration']]
        selected.sort(key=lambda r:r['file'])
        central=[r['groups']['central']['effective_cross_section_pb'] for r in selected]
        outside=[r['groups']['outside']['effective_cross_section_pb'] for r in selected]
        labels=['Old\nseed 1','Old\nseed 2','Old\nseed 3']
        total_errors=[0,0,0]
        for stage,suffix,label in [('stability','_large','Separate\nregions'),
                                  ('stability','_regulator','Regulator\ncheck')]:
            def value(route):
                r=next(r for r in summary if r['stage']==stage and float(r['mass_GeV'])==mass and r['route']==route+suffix)
                return r
            c=value('central_cm');o=value('outside_lab')
            central.append(float(c['mean_effective_pb']));outside.append(float(o['mean_effective_pb']));labels.append(label)
            total_errors.append(math.hypot(float(c['sem_from_seeds_pb']),float(o['sem_from_seeds_pb'])))
        x=range(len(labels))
        ax.bar(x,central,color='#377eb8',label='Central photons after loss factor')
        ax.bar(x,outside,bottom=central,color='#ff9f40',label='Outside acceptance')
        ax.errorbar(list(x)[3:],[central[i]+outside[i] for i in range(3,5)],
                    yerr=total_errors[3:],fmt='none',ecolor='#222222',capsize=4,lw=1)
        ax.axhline(reference,color='#333333',ls='--',lw=1.5,label='Updated reference total')
        ax.set_xticks(list(x),labels,fontsize=10)
        ax.set_ylabel('Effective photon cross section (pb)',fontsize=11)
        ax.set_title(f'{mass:g} GeV mass-dependent preselection',fontsize=13)
        ax.set_ylim(0,max(c+o for c,o in zip(central,outside))*1.15)
        ax.grid(axis='y',alpha=.2);ax.set_axisbelow(True)
        for index,(c,o) in enumerate(zip(central,outside)):
            ax.text(index,c+o+.015*ax.get_ylim()[1],f'{c+o:.4f}',ha='center',fontsize=9)
    handles,labels=axes[0].get_legend_handles_labels()
    fig.legend(handles,labels,loc='upper center',bbox_to_anchor=(.5,.92),ncol=3,fontsize=10,frameon=False)
    fig.suptitle('Unchanged physics: historical replay versus separate photon regions',fontsize=14,y=.99)
    fig.savefig(BASE/'comparison.png',dpi=180)
    fig.savefig(BASE/'comparison.svg')
    plt.close(fig)
    print(BASE/'comparison.png')

    fig,axes=plt.subplots(1,2,figsize=(10,4.8))
    fig.subplots_adjust(top=.76,bottom=.20,left=.09,right=.98,wspace=.35)
    for ax,mass in zip(axes,(.032,10.)):
        rows=[r for r in summary if float(r['mass_GeV'])==mass]
        iid=next(r for r in rows if r['route']=='outside_cm_iid')
        lab=next(r for r in rows if r['stage']=='stability' and r['route']=='outside_lab_large')
        mean=[float(lab['mean_effective_pb']),float(iid['mean_effective_pb'])]
        iiderr=max(float(iid['sem_from_seeds_pb']),float(iid['rms_reported_error_pb'])/math.sqrt(3))
        error=[float(lab['sem_from_seeds_pb']),iiderr]
        ax.errorbar([0,1],mean,yerr=error,fmt='o',color='#255f85',capsize=6,ms=7)
        ax.set_xticks([0,1],['Lab coordinates\nadaptive','CM coordinates\ndirect random draws'])
        ax.set_xlim(-.5,1.5)
        ax.set_ylabel('Outside-photon cross section (pb)')
        ax.set_title(f'{mass:g} GeV preselection')
        ax.grid(axis='y',alpha=.2)
    fig.suptitle('Independent outside-photon rate check',y=.98,fontsize=14)
    fig.text(.5,.88,'Three seeds per method; bars show one standard error of the mean',ha='center',fontsize=10)
    fig.savefig(BASE/'outside_check.png',dpi=180)
    fig.savefig(BASE/'outside_check.svg')
    plt.close(fig)


if __name__=='__main__':main()
