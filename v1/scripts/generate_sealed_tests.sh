#!/usr/bin/env bash
set -euo pipefail

project_dir=$(cd "$(dirname "$0")/.." && pwd)
study="$project_dir/fair_study/rigorous"
output="$project_dir/data/ml/sealed/root"
logs="$study/sealed_logs"
events=50000
cells=1000
samples=300
photon_mass=0.000001
electric_charge=0.3028221209
vector_masses=(0.010 0.032 0.100 0.316 1.000 1.585 2.512 3.981 5.000 6.310 10.000)
scalar_masses=(0.010 0.032 0.100 0.316 1.000 1.585 2.512 3.981 5.000 6.310 10.000)

selected="$study/development_frozen/selected_models.csv"
development_manifest="$study/development_frozen/development_inputs_and_methods.sha256"
[[ -f "$selected" ]] || {
  echo "Run scripts/run_rigorous_development.sh first" >&2
  exit 1
}
[[ -f "$development_manifest" ]] || {
  echo "Missing development provenance manifest" >&2
  exit 1
}
(cd "$project_dir" && shasum -a 256 -c "$development_manifest" >/dev/null) || {
  echo "Development provenance verification failed" >&2
  exit 1
}

manifest="$study/frozen_method_manifest.sha256"
data_manifest="$study/sealed_data_manifest.sha256"
environment="$study/frozen_environment.txt"
generation_config="$study/sealed_generation_config.csv"
for artifact in "$output" "$logs" "$manifest" "$data_manifest" \
    "$environment" "$generation_config" "$study/final"; do
  if [[ -e "$artifact" ]]; then
    echo "Refusing to reuse or overwrite sealed artifact: $artifact" >&2
    exit 1
  fi
done

mkdir -p "$output" "$logs"
make -C "$project_dir" bin/generate_vector bin/generate_scalar \
  bin/evaluate_fair_model bin/optimize_rectangular_fair bin/train_tmva \
  bin/validate_sealed_sample

{
  date -u '+utc=%Y-%m-%dT%H:%M:%SZ'
  uname -a
  root-config --version
  c++ --version
} >"$environment"
printf '%s\n' \
  'events_per_file,cells,samples,photon_regulator_mass_GeV,electric_charge,vector_seed_base,scalar_seed_base,photon_seed_base' \
  >"$generation_config"
printf '%s,%s,%s,%s,%s,%s,%s,%s\n' \
  "$events" "$cells" "$samples" "$photon_mass" "$electric_charge" \
  910000 920000 930000 >>"$generation_config"

(
  cd "$project_dir"
  shasum -a 256 \
    src/generate_vector.cpp src/generate_scalar.cpp \
    include/DarkBosonKinematics.h src/validate_sealed_sample.cpp \
    src/train_tmva.cpp src/optimize_rectangular_fair.cpp \
    src/evaluate_fair_model.cpp scripts/run_rigorous_development.sh \
    scripts/select_rigorous_models.py scripts/generate_sealed_tests.sh \
    scripts/finalize_rigorous_selection.py \
    scripts/evaluate_sealed_tests.sh \
    scripts/run_sealed_evaluation.py \
    scripts/summarize_rigorous_final.py \
    docs/rigorous_test_protocol.md docs/scalar_development_provenance.md \
    config/paper_cuts.csv \
    results/background_rates_from_table_I.csv \
    fair_study/rigorous/development_frozen/selected_models.csv \
    fair_study/rigorous/development_frozen/development_inputs_and_methods.sha256 \
    fair_study/rigorous/frozen_environment.txt \
    fair_study/rigorous/sealed_generation_config.csv \
    Makefile \
    bin/generate_vector bin/generate_scalar bin/train_tmva \
    bin/optimize_rectangular_fair bin/evaluate_fair_model \
    bin/validate_sealed_sample
  find "$study/development_frozen/models" -type f \
    \( -name metrics.csv -o -name '*.weights.xml' \) -print0 \
    | sort -z | xargs -0 shasum -a 256
  find "$study/development_frozen/baselines" -type f -name '*.csv' -print0 \
    | sort -z | xargs -0 shasum -a 256
) >"$manifest"
(cd "$project_dir" && shasum -a 256 -c "$manifest" >/dev/null)

generate_signal() {
  local signal_type=$1 mass=$2 index=$3 seed_base=$4
  local tag=${mass//./p}
  local destination="$output/${signal_type}_m${tag}_sealed.root"
  local temporary="${destination}.partial"
  local seed=$((seed_base + index))
  local selected_flag
  if [[ "$signal_type" == "vector" ]]; then
    selected_flag=--integrate-paper-cut
  else
    selected_flag=--selected
  fi
  "$project_dir/bin/generate_${signal_type}" --mass "$mass" \
    --events "$events" --cells "$cells" --samples "$samples" \
    --seed "$seed" "$selected_flag" --output "$temporary" \
    >"$logs/${signal_type}_m${tag}_sealed.log" 2>&1
  [[ -s "$temporary" ]] || { echo "empty sample: $temporary" >&2; exit 1; }
  IFS=, read -r qe2_min pt_min eta_min eta_max energy_max < <(
    awk -F, -v target="$mass" \
      'NR>1 && sprintf("%.3f",$1)==sprintf("%.3f",target) \
       {print $2","$3","$4","$5","$6; exit}' \
      "$project_dir/config/paper_cuts.csv"
  )
  "$project_dir/bin/validate_sealed_sample" "$temporary" "$qe2_min" \
    "$pt_min" "$eta_min" "$eta_max" "$energy_max" 0 100 \
    "$signal_type" "$mass" "$mass" 0.0001 "$seed" \
    "$events" "$cells" "$samples" \
    >>"$logs/${signal_type}_m${tag}_sealed.log" 2>&1
  mv "$temporary" "$destination"
}

generate_photon() {
  local mass=$1 index=$2
  local tag=${mass//./p}
  local destination="$output/photon_m${tag}_sealed.root"
  local temporary="${destination}.partial"
  local seed=$((930000 + index))
  "$project_dir/bin/generate_vector" --mass "$photon_mass" --cut-mass "$mass" \
    --coupling "$electric_charge" --events "$events" --cells "$cells" \
    --samples "$samples" --seed "$seed" \
    --integrate-paper-cut --quiet --output "$temporary" \
    >"$logs/photon_m${tag}_sealed.log" 2>&1
  [[ -s "$temporary" ]] || { echo "empty sample: $temporary" >&2; exit 1; }
  IFS=, read -r qe2_min pt_min eta_min eta_max energy_max < <(
    awk -F, -v target="$mass" \
      'NR>1 && sprintf("%.3f",$1)==sprintf("%.3f",target) \
       {print $2","$3","$4","$5","$6; exit}' \
      "$project_dir/config/paper_cuts.csv"
  )
  "$project_dir/bin/validate_sealed_sample" "$temporary" "$qe2_min" \
    "$pt_min" "$eta_min" "$eta_max" "$energy_max" 1 100 \
    vector "$photon_mass" "$mass" "$electric_charge" "$seed" \
    "$events" "$cells" "$samples" \
    >>"$logs/photon_m${tag}_sealed.log" 2>&1
  mv "$temporary" "$destination"
}

for index in "${!vector_masses[@]}"; do
  mass=${vector_masses[$index]}
  generate_signal vector "$mass" "$index" 910000
  generate_photon "$mass" "$index"
done
for index in "${!scalar_masses[@]}"; do
  mass=${scalar_masses[$index]}
  generate_signal scalar "$mass" "$index" 920000
done

root_count=$(find "$output" -type f -name '*.root' | wc -l | tr -d ' ')
[[ "$root_count" == "33" ]] || {
  echo "Expected 33 sealed ROOT files, found $root_count" >&2
  exit 1
}
(cd "$project_dir" && shasum -a 256 data/ml/sealed/root/*.root) \
  >"$data_manifest"
(cd "$project_dir" && shasum -a 256 -c "$manifest" >/dev/null)
(cd "$project_dir" && shasum -a 256 -c "$data_manifest" >/dev/null)

echo "Sealed samples generated. Do not change frozen methods before evaluation."
echo "Manifest: $manifest"
echo "Data manifest: $data_manifest"
