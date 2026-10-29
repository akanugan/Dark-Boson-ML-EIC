#!/usr/bin/env bash
set -euo pipefail

project_dir=$(cd "$(dirname "$0")/.." && pwd)
output_root="$project_dir/fair_study"
mkdir -p "$output_root/models" "$output_root/baselines" "$output_root/logs" \
  "$output_root/results"

make -C "$project_dir" bin/train_tmva bin/optimize_rectangular

lookup_rate() {
  local file=$1 mass=$2 column=$3
  awk -F, -v target="$mass" -v col="$column" \
    'NR>1 && sprintf("%.3f",$1)==sprintf("%.3f",target){print $col; exit}' "$file"
}

run_point() {
  local signal_type=$1 mass=$2
  local tag=${mass//./p}
  local signal_train="$project_dir/data/ml/root/${signal_type}_m${tag}_train.root"
  local signal_test="$project_dir/data/ml/root/${signal_type}_m${tag}_test.root"
  local photon_train="$project_dir/data/ml/root/photon_m${tag}_train.root"
  local photon_test="$project_dir/data/ml/root/photon_m${tag}_test.root"
  local signal_xs photon_xs dis_xs
  if [[ "$signal_type" == "vector" ]]; then
    signal_xs=$(lookup_rate "$project_dir/frozen_baseline/results/vector_scan_fresh.csv" "$mass" 4)
  else
    signal_xs=$(lookup_rate "$project_dir/frozen_baseline/results/scalar_scan.csv" "$mass" 4)
  fi
  photon_xs=$(lookup_rate "$project_dir/results/background_rates_from_table_I.csv" "$mass" 2)
  dis_xs=$(lookup_rate "$project_dir/results/background_rates_from_table_I.csv" "$mass" 3)

  for feature_set in electron electron_qa2; do
    local model_dir="$output_root/models/${signal_type}_m${tag}_${feature_set}"
    "$project_dir/bin/train_tmva" "$signal_train" "$signal_test" \
      "$photon_train" "$photon_test" "$model_dir" "$signal_type" "$mass" \
      "$signal_xs" "$photon_xs" "$dis_xs" "$feature_set" \
      >"$output_root/logs/${signal_type}_m${tag}_${feature_set}_tmva.log" 2>&1
    "$project_dir/bin/optimize_rectangular" "$signal_test" "$photon_test" \
      "$output_root/baselines/${signal_type}_m${tag}_${feature_set}.csv" \
      "$signal_type" "$mass" "$signal_xs" "$photon_xs" "$dis_xs" \
      "$feature_set" \
      >"$output_root/logs/${signal_type}_m${tag}_${feature_set}_rectangular.log" 2>&1
  done
}

run_point vector 1.000
run_point vector 10.000
run_point scalar 1.000
run_point scalar 6.310

python3 "$project_dir/scripts/summarize_fair_pilot.py"
python3 "$project_dir/scripts/plot_fair_pilot.py"
echo "Created $output_root/results/fair_pilot_metrics.csv"
