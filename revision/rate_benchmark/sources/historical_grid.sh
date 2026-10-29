#!/bin/zsh
set -euo pipefail
unsetopt BG_NICE

generator="$(pwd)/analysis/background_crosscheck/bin/generate_photon"
outdir="/tmp/photon_effective_grid"
mkdir -p "$outdir"

masses=(0.010 0.032 0.100 0.316 1.000 1.585 2.512 3.981 5.000 6.310 10.000)
seeds=(833001 833101 833201)
max_jobs=4
running=0
pids=()

for mass in "${masses[@]}"; do
  tag=${mass//./p}
  for seed in "${seeds[@]}"; do
    "$generator" \
      --mass 0.000001 \
      --cut-mass "$mass" \
      --coupling 0.3028221209 \
      --events 250000 \
      --cells 2500 \
      --samples 1200 \
      --seed "$seed" \
      --integrate-paper-cut \
      --photon-region effective \
      --quiet \
      --output "$outdir/photon_m${tag}_s${seed}.root" \
      > "$outdir/photon_m${tag}_s${seed}.log" 2>&1 &
    ((running += 1))
    pids+=("$!")
    if (( running >= max_jobs )); then
      for pid in "${pids[@]}"; do
        wait "$pid"
      done
      running=0
      pids=()
    fi
  done
done

for pid in "${pids[@]}"; do
  wait "$pid"
done
