# Exact-t seed-robust BDT-versus-cuts study

Run: `run_t_20260820_final`; complete replicas per benchmark: 10.
Both methods use recoil-electron variables plus exact generator-level t.

| Signal | Mass [GeV] | RZ ratio | Coupling advantage, median [95%] | Familywise lower | Verdict |
|---|---:|---:|---:|---:|---|
| vector | 10 | 1.02456 | +1.208% [+1.081%, +1.326%] | +1.081% | practical BDT superiority |
| scalar | 10 | 1.02780 | +1.361% [+1.206%, +1.529%] | +1.206% | practical BDT superiority |

The intervals use a hierarchical paired bootstrap over complete generator/training replicas and paired event resamples.
The result remains conditional parton-level evidence with exact t as an oracle input.
