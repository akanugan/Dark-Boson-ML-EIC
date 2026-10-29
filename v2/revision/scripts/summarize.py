#!/usr/bin/env python3
"""Summarize only complete ten-run groups; incomplete groups are explicitly listed."""
import argparse
import json
from pathlib import Path
import numpy as np
from run_comparison import rows, write_csv, FEATURES

PAIRS = ('bdt_over_cuts','likelihood_over_cuts','bdt_over_likelihood')

def aggregate(draws, nominal, seed, n=200000):
    rng=np.random.default_rng(seed)
    result=np.empty((n,3))
    for start in range(0,n,2000):
        count=min(2000,n-start)
        runs=rng.integers(0,10,(count,10))
        events=rng.integers(0,draws.shape[1],(count,10))
        result[start:start+count]=np.mean(np.log(draws[runs,events]),axis=1)
    return np.exp(np.mean(np.log(nominal),axis=0)), np.exp(result)

def main():
    parser=argparse.ArgumentParser();parser.add_argument('results',type=Path)
    args=parser.parse_args()
    groups={};individual=[]
    for complete in sorted(args.results.glob('rep_*/*/complete.json')):
        meta=json.loads(complete.read_text());rate=meta['rate'];point=complete.parent
        for feature in FEATURES:
            dest=point/feature
            a,b=[rows(dest/f'{m}_test.csv')[0] for m in ('bdt','likelihood')]
            for key in ('box_signal_efficiency','box_photon_efficiency','box_RZ'):
                if key in a and not np.isclose(float(a[key]),float(b[key]),rtol=1e-10,atol=1e-12):
                    raise ValueError(f'Inconsistent shared cut result: {dest}, {key}')
            nominal=np.array([float(a['RZ_ratio']),float(b['RZ_ratio']),float(a['RZ_ratio'])/float(b['RZ_ratio'])])
            draw=np.array([[float(r[k]) for k in PAIRS] for r in rows(dest/'paired_ratios.csv')])
            key=(rate['signal_type'],float(rate['mass_GeV']),feature)
            groups.setdefault(key,[]).append((meta['replicate'],nominal,draw))
            individual.append(dict(signal_type=key[0],mass_GeV=key[1],feature_set=feature,
                                   run=meta['replicate'],**dict(zip(PAIRS,nominal))))
    if individual:write_csv(args.results/'run_results.csv',individual)
    summaries=[];pending=[]
    for index,(key,runs) in enumerate(sorted(groups.items())):
        if sorted(r[0] for r in runs)!=list(range(1,11)):
            pending.append(dict(group=key,completed_runs=len(runs)));continue
        nominal,boot=aggregate(np.stack([r[2] for r in runs]),np.stack([r[1] for r in runs]),27000000+index)
        for j,pair in enumerate(PAIRS):
            lo,hi=np.quantile(boot[:,j],[.025,.975])
            flo,fhi=np.quantile(boot[:,j],[.025/132,1-.025/132])
            summaries.append(dict(signal_type=key[0],mass_GeV=key[1],feature_set=key[2],comparison=pair,
                                  geometric_mean_ratio=nominal[j],ci95_low=lo,ci95_high=hi,
                                  simultaneous_low=flo,simultaneous_high=fhi,
                                  family_size=132,independent_runs=10,resamples=200000))
    if summaries:write_csv(args.results/'summary.csv',summaries)
    status=dict(completed_points=len(individual)//2,expected_points=220,
                complete_groups=len(summaries)//3,expected_groups=44,incomplete_groups=pending)
    (args.results/'status.json').write_text(json.dumps(status,indent=2))
    print(json.dumps(status,indent=2))

if __name__=='__main__':main()
