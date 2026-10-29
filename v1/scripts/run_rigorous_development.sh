#!/usr/bin/env bash
set -euo pipefail

project_dir=$(cd "$(dirname "$0")/.." && pwd)
study="$project_dir/fair_study/rigorous/development_frozen"
profiles=(depth2 depth3 depth4 depth3_800)
features=(electron electron_qa2)
quantile_grids=(40 80 160)
vector_masses=(0.010 0.032 0.100 0.316 1.000 1.585 2.512 3.981 5.000 6.310 10.000)
scalar_masses=(0.010 0.032 0.100 0.316 1.000 1.585 2.512 3.981 5.000 6.310 10.000)

[[ ! -e "$study" ]] || {
  echo "Refusing to mix or overwrite development artifacts: $study" >&2
  exit 1
}
mkdir -p "$study/models" "$study/baselines" "$study/logs"
make -C "$project_dir" bin/train_tmva bin/optimize_rectangular_fair \
  bin/generate_scalar

lookup_rate() {
  local file=$1 mass=$2 column=$3
  awk -F, -v target="$mass" -v col="$column" \
    'NR>1 && sprintf("%.3f",$1)==sprintf("%.3f",target){print $col; exit}' "$file"
}

ensure_scalar_ten() {
  local train="$project_dir/data/ml/root/scalar_m10p000_train.root"
  local validation="$project_dir/data/ml/root/scalar_m10p000_test.root"
  if [[ ! -f "$train" ]]; then
    "$project_dir/bin/generate_scalar" --mass 10.000 --events 30000 \
      --cells 1000 --samples 300 --seed 310010 --selected --output "$train" \
      >"$project_dir/logs/ml/scalar_m10p000_train.log" 2>&1
  fi
  if [[ ! -f "$validation" ]]; then
    "$project_dir/bin/generate_scalar" --mass 10.000 --events 20000 \
      --cells 1000 --samples 300 --seed 410010 --selected \
      --output "$validation" \
      >"$project_dir/logs/ml/scalar_m10p000_test.log" 2>&1
  fi
}

signal_rate() {
  local signal_type=$1 mass=$2
  local value
  if [[ "$signal_type" == "vector" ]]; then
    value=$(lookup_rate "$project_dir/frozen_baseline/results/vector_scan_fresh.csv" "$mass" 4)
  else
    value=$(lookup_rate "$project_dir/frozen_baseline/results/scalar_scan.csv" "$mass" 4)
  fi
  if [[ -z "$value" && "$signal_type" == "scalar" && "$mass" == "10.000" ]]; then
    value=$(awk -F= '/sigma_paper_cut_weighted_pb=/{print $2; exit}' \
      "$project_dir/logs/ml/scalar_m10p000_train.log")
  fi
  [[ -n "$value" ]] || { echo "missing signal rate for $signal_type $mass" >&2; exit 1; }
  echo "$value"
}

run_point() {
  local signal_type=$1 mass=$2 point_index=$3
  local tag=${mass//./p}
  local signal_train="$project_dir/data/ml/root/${signal_type}_m${tag}_train.root"
  local signal_validation="$project_dir/data/ml/root/${signal_type}_m${tag}_test.root"
  local photon_train="$project_dir/data/ml/root/photon_m${tag}_train.root"
  local photon_validation="$project_dir/data/ml/root/photon_m${tag}_test.root"
  local signal_xs photon_xs dis_xs
  signal_xs=$(signal_rate "$signal_type" "$mass")
  photon_xs=$(lookup_rate "$project_dir/results/background_rates_from_table_I.csv" "$mass" 2)
  dis_xs=$(lookup_rate "$project_dir/results/background_rates_from_table_I.csv" "$mass" 3)

  for feature_index in "${!features[@]}"; do
    local feature=${features[$feature_index]}
    for profile_index in "${!profiles[@]}"; do
      local profile=${profiles[$profile_index]}
      local model_dir="$study/models/${signal_type}_m${tag}_${feature}/${profile}"
      local metrics="$model_dir/metrics.csv"
      # Hold the stochastic training seed fixed while changing architecture.
      # This prevents profile selection from also selecting a lucky RNG seed.
      local model_seed=$((720000 + point_index * 100 + feature_index * 10))
      "$project_dir/bin/train_tmva" "$signal_train" "$signal_validation" \
        "$photon_train" "$photon_validation" "$model_dir" "$signal_type" \
        "$mass" "$signal_xs" "$photon_xs" "$dis_xs" "$feature" \
        "$profile" "$model_seed" validation_all \
        >"$study/logs/${signal_type}_m${tag}_${feature}_${profile}.log" 2>&1
    done

    for quantiles in "${quantile_grids[@]}"; do
      local baseline="$study/baselines/${signal_type}_m${tag}_${feature}_q${quantiles}.csv"
      "$project_dir/bin/optimize_rectangular_fair" \
        "$signal_train" "$photon_train" \
        "$signal_validation" "$photon_validation" \
        "$signal_validation" "$photon_validation" "$baseline" \
        "$signal_type" "$mass" "$signal_xs" "$photon_xs" "$dis_xs" \
        "$feature" "$quantiles" 20 \
        $((820000 + point_index * 10 + feature_index)) \
        >"$study/logs/${signal_type}_m${tag}_${feature}_box_q${quantiles}.log" 2>&1
    done
  done
  echo "development complete: $signal_type $mass"
}

ensure_scalar_ten

development_manifest="$study/development_inputs_and_methods.sha256"
(
  cd "$project_dir"
  shasum -a 256 \
    src/train_tmva.cpp src/optimize_rectangular_fair.cpp \
    scripts/run_rigorous_development.sh scripts/select_rigorous_models.py \
    docs/rigorous_test_protocol.md config/paper_cuts.csv \
    results/background_rates_from_table_I.csv \
    frozen_baseline/results/vector_scan_fresh.csv \
    frozen_baseline/results/scalar_scan.csv \
    bin/train_tmva bin/optimize_rectangular_fair
  find data/ml/root -type f -name '*.root' -print0 \
    | sort -z | xargs -0 shasum -a 256
) >"$development_manifest"
(cd "$project_dir" && shasum -a 256 -c "$development_manifest" >/dev/null)

point=0
for mass in "${vector_masses[@]}"; do
  run_point vector "$mass" "$point"
  point=$((point + 1))
done
for mass in "${scalar_masses[@]}"; do
  run_point scalar "$mass" "$point"
  point=$((point + 1))
done

(cd "$project_dir" && shasum -a 256 -c "$development_manifest" >/dev/null)
python3 "$project_dir/scripts/select_rigorous_models.py"
echo "Development selection complete. No sealed test sample was opened."
