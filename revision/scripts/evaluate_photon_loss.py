#!/usr/bin/env python3
"""Paired, fixed-selector photon-loss sensitivity study at 10 GeV.

No training, threshold optimization, or choice of loss scenario uses these samples.
"""
import os
os.environ['OPENBLAS_NUM_THREADS'] = '1'
os.environ['VECLIB_MAXIMUM_THREADS'] = '1'
import csv
import json
import math
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
import numpy as np

BASE = Path(__file__).resolve().parents[1]
OUT = BASE / 'photon_loss_10gev'
EPS = np.array([1e-8, 1e-7, 1e-6, 1e-5])
TYPES = ['vector', 'scalar']
METHODS = ['BDT', 'likelihood', 'cuts']
MODES = ['shape_only', 'rate_and_shape', 'rate_only']
PAIRS = [(0, 2, 'BDT/cuts'), (1, 2, 'likelihood/cuts'), (0, 1, 'BDT/likelihood')]
FIXED_PHOTON_PB = .33266971
DIS_PB = .0155
NBOOT = 2000

def load(path):
    return np.genfromtxt(path, delimiter=',', names=True)

def write(path, rows):
    with path.open('w') as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)

def equal(a, b, columns):
    for col in columns:
        if not np.array_equal(a[col], b[col]):
            raise RuntimeError(f'Unpaired input column: {col}')

def resample_sums(rng, matrix, attempts, size):
    # The unstored attempts have zero integrand. A final category retains them
    # when bootstrapping absolute stratum cross sections, not just efficiencies.
    n = len(matrix)
    assert n <= attempts
    p = np.r_[np.full(n, 1.0/attempts), (attempts-n)/attempts]
    return rng.multinomial(attempts, p, size=size)[:, :-1] @ matrix

def performance(signal_efficiency, central, outside):
    # central/outside have columns total and three pass integrals per boson.
    # Shape: [replicate, scenario, boson, method].
    varied = central[:, None, :] * EPS[None, :, None] + outside[:, None, :]
    total = varied[:, :, :1]
    passed = varied[:, :, 1:].reshape(-1, len(EPS), 2, 3)
    eff = passed / total[:, :, None, :]
    nominal_eff = eff[:, 2:3]
    def rz(rate, photon_eff):
        return signal_efficiency[:, None] * np.sqrt((rate + DIS_PB)/(rate*photon_eff + DIS_PB))
    shape = rz(FIXED_PHOTON_PB, eff)
    full = rz(total[:, :, None, :], eff)
    rate_only = rz(total[:, :, None, :], nominal_eff)
    return np.stack([shape, full, rate_only], axis=1), total[:, :, 0]

def job(rep):
    start = time.time()
    dst = OUT / f'rep_{rep:03d}'
    signal_matrices = []
    strata = {}
    diagnostics = []
    for region in ['central', 'outside']:
        arrays = {}
        for typ in TYPES:
            arrays[typ] = {}
            for method in ['bdt', 'likelihood']:
                prefix = dst / typ / f'{method}_{region}'
                a = load(prefix.with_name(prefix.name + '_photon.csv'))
                arrays[typ][method] = a
                if region == 'central':
                    s = load(prefix.with_name(prefix.name + '_signal.csv'))
                    old = load(BASE/'photon_shape_test'/f'rep_{rep:03d}'/typ/f'{method}_signal.csv')
                    equal(s, old, ['weight','logpt','eta','logt','model_pass','cuts_pass'])
                    arrays[typ][method+'_signal'] = s
                else:
                    s = load(prefix.with_name(prefix.name + '_signal.csv'))
                    equal(s, load(dst/typ/f'{method}_central_signal.csv'),
                          ['weight','logpt','eta','logt','model_pass','cuts_pass'])
            equal(arrays[typ]['bdt'], arrays[typ]['likelihood'], ['weight','logpt','eta','logt','cuts_pass'])
            if region == 'central':
                s = arrays[typ]['bdt_signal']
                equal(s, arrays[typ]['likelihood_signal'], ['weight','logpt','eta','logt','cuts_pass'])
                flags = np.column_stack([s['model_pass'], arrays[typ]['likelihood_signal']['model_pass'], s['cuts_pass']])
                signal_matrices.append(np.column_stack([s['weight'], s['weight'][:, None]*flags]))
        v = arrays['vector']['bdt']
        equal(v, arrays['scalar']['bdt'], ['weight','logpt','eta','logt'])
        raw = v['weight'] / (1e-6 if region == 'central' else 1.0)
        flags = np.column_stack([arrays[t][m]['model_pass'] if m != 'cuts' else arrays[t]['bdt']['cuts_pass']
                                 for t in TYPES for m in ['bdt','likelihood','cuts']])
        mat = np.column_stack([raw, raw[:,None]*flags])
        meta = json.loads((dst/f'{region}.json').read_text())
        if not math.isclose(raw.sum(), meta['sigma_pb'], rel_tol=2e-7):
            raise RuntimeError(f'Stratum normalization/region failure {rep} {region}')
        strata[region] = (mat, meta['attempts'])
        relerr = np.sqrt(max(0, (raw*raw).sum() - raw.sum()**2/meta['attempts']))/raw.sum()
        diagnostics.append(dict(rep=rep,region=region,entries=len(raw),attempts=meta['attempts'],
             sigma_pb=raw.sum(),foam_error_pb=meta['sigma_error_pb'],event_error_pb=raw.sum()*relerr,
             neff=raw.sum()**2/np.dot(raw,raw),max_weight_fraction=raw.max()/raw.sum()))
    se = np.array([m.sum(0)[1:]/m.sum(0)[0] for m in signal_matrices])[None]
    c = strata['central'][0].sum(0)[None]
    o = strata['outside'][0].sum(0)[None]
    nominal, rates = performance(se, c, o)
    rows = []
    for mode_i, mode in enumerate(MODES):
        for ei, epsilon in enumerate(EPS):
            for ti, typ in enumerate(TYPES):
                record = dict(rep=rep,boson=typ,mode=mode,epsilon=epsilon,
                              calculated_photon_rate_pb=rates[0,ei],
                              outside_fraction=o[0,0]/rates[0,ei])
                for mi, method in enumerate(METHODS):
                    record[method+'_RZ'] = nominal[0,mode_i,ei,ti,mi]
                    record[method+'_signal_efficiency'] = se[0,ti,mi]
                    record[method+'_photon_efficiency'] = (EPS[ei]*c[0,1+ti*3+mi]+o[0,1+ti*3+mi])/rates[0,ei]
                rows.append(record)
    write(dst/'metrics.csv',rows)
    write(dst/'component_diagnostics.csv',diagnostics)
    np.save(dst/'nominal_RZ.npy', nominal[0])
    rng = np.random.default_rng(1572000 + rep)
    samples = []
    for start_i in range(0, NBOOT, 50):
        n = min(50, NBOOT-start_i)
        cb = resample_sums(rng, *strata['central'], n)
        ob = resample_sums(rng, *strata['outside'], n)
        sb = []
        for sm in signal_matrices:
            # Conditional bootstrap of accepted signal events: efficiency only.
            sums = rng.multinomial(len(sm),np.full(len(sm),1/len(sm)),size=n) @ sm
            sb.append(sums[:,1:]/sums[:,:1])
        rz, _ = performance(np.stack(sb,axis=1),cb,ob)
        if not np.all(np.isfinite(rz)) or np.any(rz <= 0):
            raise RuntimeError('Undefined bootstrap performance')
        samples.append(rz)
    np.save(dst/'bootstrap_RZ.npy',np.concatenate(samples))
    (dst/'evaluation_complete.json').write_text(json.dumps({'rep':rep,'bootstrap':NBOOT,'seconds':time.time()-start},indent=2))
    return rows, diagnostics

def summarize():
    rng = np.random.default_rng(1572999)
    nominal = np.array([np.load(OUT/f'rep_{r:03d}/nominal_RZ.npy') for r in range(1,11)])
    boot = np.array([np.load(OUT/f'rep_{r:03d}/bootstrap_RZ.npy') for r in range(1,11)])
    ix = rng.integers(0,10,(20000,10))
    jx = rng.integers(0,NBOOT,(20000,10))
    draws = np.exp(np.log(boot[ix,jx]).mean(axis=1))
    point = np.exp(np.log(nominal).mean(axis=0))
    output = []
    for mi, mode in enumerate(MODES):
        for ei, epsilon in enumerate(EPS):
            for ti, typ in enumerate(TYPES):
                for a,b,label in PAIRS:
                    dist = 100*(draws[:,mi,ei,ti,a]/draws[:,mi,ei,ti,b]-1)
                    low,high = np.quantile(dist,[.025,.975])
                    output.append(dict(mode=mode,epsilon=epsilon,boson=typ,comparison=label,
                            advantage_pct=100*(point[mi,ei,ti,a]/point[mi,ei,ti,b]-1),
                            ci95_low=low,ci95_high=high,runs=10,bootstrap_per_run=NBOOT,
                            aggregate_draws=20000,interval_scope='pointwise, not multiplicity-adjusted'))
    write(OUT/'summary.csv',output)

def main():
    plan = json.loads((OUT/'plan.json').read_text())
    plan.update({
      'generator_changes':'Central: original phase-space coordinates restricted to |eta_gamma|<=3.5. Outside: alternative lab coordinates covering both forward/backward |eta_gamma|>3.5. Same matrix element, couplings, form factor, flux, preselection; explicit analytic phase-space Jacobian.',
      'coordinate_check':'50 outside phase-space points: lab density versus original density times numerical coordinate Jacobian; maximum relative difference 5.23e-6. mapping_check.cpp/log retained.',
      'source_context':'Davoudiasl and Liu v4 Section III assumes central photon inefficiency between 1e-8 and 1e-5 and 100% loss for |eta_gamma|>3.5. These are documented response scenarios, not an experimentally measured uncertainty band.',
      'fixed_photon_rate_pb_for_shape_only':FIXED_PHOTON_PB,
      'dis_rate_pb_fixed_and_unrejected':DIS_PB,
      'scope':'Photon response varied alone. All existing validation-selected BDT/PDERS models, thresholds, rectangular cuts and signal test events held fixed. No refitting or reoptimization in variations. New independent stratified photon test samples shared by all three methods and both boson types.',
      'bootstrap':'2000 paired event resamples per run. Photon strata resampled separately over all attempted events, including zero-weight unstored attempts, retaining absolute-rate uncertainty. Conditional accepted-event bootstrap for signal efficiencies. 20000 draws resampling 10 runs and their paired event draws; geometric mean performance ratios. Pointwise 95% intervals, no new familywise significance claim.',
      'rate_only_control':'Varied total photon rate with the epsilon=1e-6 normalized shape held fixed; complements fixed-rate shape-only and full rate+shape tests.',
      'scenario_formula':'sigma_eff(epsilon)=epsilon*sigma_central+sigma_outside; same formula for selected cross sections.'})
    (OUT/'plan.json').write_text(json.dumps(plan,indent=2))
    done=[]; components=[]
    with ThreadPoolExecutor(max_workers=4) as pool:
        futures = {pool.submit(job, rep):rep for rep in range(1,11)}
        for future in as_completed(futures):
            rows, diagnostics = future.result()
            done.extend(rows);components.extend(diagnostics)
            print('Evaluated',len(done)//24,'/10',futures[future],flush=True)
            (OUT/'evaluation_status.json').write_text(json.dumps({'state':'running','completed':len(done)//24,'total':10}))
    write(OUT/'run_results.csv',done)
    write(OUT/'component_diagnostics.csv',components)
    summarize()
    (OUT/'evaluation_status.json').write_text(json.dumps({'state':'complete','completed':10,'total':10}))

if __name__ == '__main__':
    main()
