#!/usr/bin/env bash
set -euo pipefail

project_dir=$(cd "$(dirname "$0")/.." && pwd)
events=${SIGNAL_EVENTS:-20000}
vector_cells=${VECTOR_CELLS:-500}
vector_samples=${VECTOR_SAMPLES:-200}
scalar_cells=${SCALAR_CELLS:-1200}
scalar_samples=${SCALAR_SAMPLES:-300}
base_seed=${SIGNAL_SEED:-260812001}
split_seed=${SPLIT_SEED:-260812999}

vector_masses=(0.010 0.032 0.100 0.316 1.000 1.585 2.512 3.981 5.000 6.310 10.000)
scalar_masses=(0.010 0.032 0.100 0.316 1.000 1.585 2.512 3.981 5.000 6.310)

mkdir -p "$project_dir/data/root" "$project_dir/data/csv" "$project_dir/results/cutflows/individual" "$project_dir/logs"

make -C "$project_dir" all

for index in "${!vector_masses[@]}"; do
  mass=${vector_masses[$index]}
  tag=${mass//./p}
  seed=$((base_seed + index))

  "$project_dir/bin/generate_vector" \
    --mass "$mass" --events "$events" --cells "$vector_cells" \
    --samples "$vector_samples" --seed "$seed" --quiet \
    --output "$project_dir/data/root/vector_m${tag}.root" \
    > "$project_dir/logs/vector_m${tag}.log" 2>&1

  "$project_dir/bin/extract_cutflow" \
    "$project_dir/data/root/vector_m${tag}.root" vector \
    "$project_dir/config/paper_cuts.csv" \
    "$project_dir/results/cutflows/individual/vector_m${tag}.csv" \
    "$project_dir/data/csv/vector_m${tag}.csv" "$split_seed" \
    2>> "$project_dir/logs/vector_m${tag}.log"
done

for index in "${!scalar_masses[@]}"; do
  mass=${scalar_masses[$index]}
  tag=${mass//./p}
  seed=$((base_seed + 100 + index))
  "$project_dir/bin/generate_scalar" \
    --mass "$mass" --events "$events" --cells "$scalar_cells" \
    --samples "$scalar_samples" --seed "$seed" \
    --output "$project_dir/data/root/scalar_m${tag}.root" \
    > "$project_dir/logs/scalar_m${tag}.log" 2>&1

  "$project_dir/bin/extract_cutflow" \
    "$project_dir/data/root/scalar_m${tag}.root" scalar \
    "$project_dir/config/paper_cuts.csv" \
    "$project_dir/results/cutflows/individual/scalar_m${tag}.csv" \
    "$project_dir/data/csv/scalar_m${tag}.csv" "$split_seed" \
    2>> "$project_dir/logs/scalar_m${tag}.log"
done

"$project_dir/scripts/combine_signal_outputs.sh"

echo "Pilot signal dataset complete."
