#!/usr/bin/env bash
set -euo pipefail

project_dir=$(cd "$(dirname "$0")/.." && pwd)
train_events=${ML_TRAIN_EVENTS:-30000}
test_events=${ML_TEST_EVENTS:-20000}
cells=${ML_CELLS:-1000}
samples=${ML_SAMPLES:-300}
photon_mass=${PHOTON_REGULATOR_MASS:-0.000001}
electric_charge=${ELECTRIC_CHARGE:-0.3028221209}
sdk_include=/Library/Developer/CommandLineTools/SDKs/MacOSX26.2.sdk/usr/include/c++/v1

vector_masses=(0.010 0.032 0.100 0.316 1.000 1.585 2.512 3.981 5.000 6.310 10.000)
scalar_masses=(0.010 0.032 0.100 0.316 1.000 1.585 2.512 3.981 5.000 6.310)

mkdir -p "$project_dir/data/ml/root" "$project_dir/models" \
  "$project_dir/results/ml" "$project_dir/logs/ml"
make -C "$project_dir" all

calibration_root="$project_dir/data/ml/validation/photon_inclusive.root"
pt_reference="$project_dir/references/published_ancillary_v2/Fig4_pt_photon.dat"
eta_reference="$project_dir/references/published_ancillary_v2/Fig4_eta_photon.dat"
mkdir -p "$project_dir/data/ml/validation"
if [[ ! -f "$calibration_root" ]]; then
  "$project_dir/bin/generate_vector" --mass "$photon_mass" \
    --coupling "$electric_charge" --events 100000 --cells 1500 --samples 500 \
    --seed 710001 --quiet --output "$calibration_root" \
    >"$project_dir/logs/ml/photon_inclusive_validation.log" 2>&1
fi

CPLUS_INCLUDE_PATH="$sdk_include${CPLUS_INCLUDE_PATH:+:$CPLUS_INCLUDE_PATH}" \
  "$project_dir/bin/validate_photon_shapes" "$calibration_root" \
  "$pt_reference" "$eta_reference" \
  "$project_dir/results/ml/photon_shape_validation.csv" \
  2>"$project_dir/results/ml/photon_shape_validation_summary.txt"

lookup_rate() {
  local file=$1 mass=$2 column=$3
  awk -F, -v target="$mass" -v col="$column" \
    'NR>1 && sprintf("%.3f",$1)==sprintf("%.3f",target){print $col; exit}' "$file"
}

generate_pair() {
  local signal_type=$1 mass=$2 index=$3
  local tag=${mass//./p}
  local signal_generator="$project_dir/bin/generate_${signal_type}"
  local signal_train="$project_dir/data/ml/root/${signal_type}_m${tag}_train.root"
  local signal_test="$project_dir/data/ml/root/${signal_type}_m${tag}_test.root"
  local photon_train="$project_dir/data/ml/root/photon_m${tag}_train.root"
  local photon_test="$project_dir/data/ml/root/photon_m${tag}_test.root"
  local model_dir="$project_dir/models/${signal_type}_m${tag}"
  local signal_xs photon_xs dis_xs

  if [[ "$signal_type" == "vector" ]]; then
    signal_xs=$(lookup_rate "$project_dir/frozen_baseline/results/vector_scan_fresh.csv" "$mass" 4)
  else
    signal_xs=$(lookup_rate "$project_dir/frozen_baseline/results/scalar_scan.csv" "$mass" 4)
  fi

  photon_xs=$(lookup_rate "$project_dir/results/background_rates_from_table_I.csv" "$mass" 2)
  dis_xs=$(lookup_rate "$project_dir/results/background_rates_from_table_I.csv" "$mass" 3)

  local selected_flag
  if [[ "$signal_type" == "vector" ]]; then selected_flag="--integrate-paper-cut"; else selected_flag="--selected"; fi

  "$signal_generator" --mass "$mass" --events "$train_events" --cells "$cells" \
    --samples "$samples" --seed $((310000 + index)) $selected_flag \
    --output "$signal_train" >"$project_dir/logs/ml/${signal_type}_m${tag}_train.log" 2>&1
  "$signal_generator" --mass "$mass" --events "$test_events" --cells "$cells" \
    --samples "$samples" --seed $((410000 + index)) $selected_flag \
    --output "$signal_test" >"$project_dir/logs/ml/${signal_type}_m${tag}_test.log" 2>&1

  if [[ ! -f "$photon_train" ]]; then
    "$project_dir/bin/generate_vector" --mass "$photon_mass" --cut-mass "$mass" \
      --coupling "$electric_charge" --events "$train_events" --cells "$cells" \
      --samples "$samples" --seed $((510000 + index)) --integrate-paper-cut --quiet \
      --output "$photon_train" >"$project_dir/logs/ml/photon_m${tag}_train.log" 2>&1
    "$project_dir/bin/generate_vector" --mass "$photon_mass" --cut-mass "$mass" \
      --coupling "$electric_charge" --events "$test_events" --cells "$cells" \
      --samples "$samples" --seed $((610000 + index)) --integrate-paper-cut --quiet \
      --output "$photon_test" >"$project_dir/logs/ml/photon_m${tag}_test.log" 2>&1
  fi

  "$project_dir/bin/train_tmva" "$signal_train" "$signal_test" \
    "$photon_train" "$photon_test" "$model_dir" "$signal_type" "$mass" \
    "$signal_xs" "$photon_xs" "$dis_xs" "electron_qa2" \
    >"$project_dir/logs/ml/${signal_type}_m${tag}_tmva.log" 2>&1
  echo "completed ${signal_type} m=${mass} GeV"
}

for index in "${!vector_masses[@]}"; do
  generate_pair vector "${vector_masses[$index]}" "$index"
done
for index in "${!scalar_masses[@]}"; do
  generate_pair scalar "${scalar_masses[$index]}" "$index"
done

metrics="$project_dir/results/ml/ml_metrics.csv"
first=$(find "$project_dir/models" -name metrics.csv | sort | head -1)
sed -n '1p' "$first" > "$metrics"
while IFS= read -r file; do sed -n '2p' "$file"; done \
  < <(find "$project_dir/models" -name metrics.csv | sort) >> "$metrics"

echo "Created $metrics"
python3 "$project_dir/scripts/validate_ml_outputs.py"
