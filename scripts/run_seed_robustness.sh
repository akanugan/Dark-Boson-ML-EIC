#!/usr/bin/env bash
set -euo pipefail

project_dir=$(cd "$(dirname "$0")/.." && pwd)

replicates=${ROBUST_REPLICATES:-10}
train_events=${ROBUST_TRAIN_EVENTS:-30000}
validation_events=${ROBUST_VALIDATION_EVENTS:-20000}
test_events=${ROBUST_TEST_EVENTS:-20000}
cells=${ROBUST_CELLS:-1000}
samples=${ROBUST_SAMPLES:-300}
box_restarts=${ROBUST_BOX_RESTARTS:-20}
paired_bootstraps=${ROBUST_PAIRED_BOOTSTRAPS:-2000}
aggregate_bootstraps=${ROBUST_AGGREGATE_BOOTSTRAPS:-20000}
seed_base=${ROBUST_SEED_BASE:-8300000}
photon_mass=${PHOTON_REGULATOR_MASS:-0.000001}
electric_charge=${ELECTRIC_CHARGE:-0.3028221209}
run_id=${ROBUST_RUN_ID:-run_$(date -u +%Y%m%dT%H%M%SZ)}
output_root=${ROBUST_OUTPUT_ROOT:-$project_dir/fair_study/seed_robustness}
run_dir="$output_root/$run_id"

# These profiles are preregistered. Do not alter them after inspecting a final
# test sample. Their order is the deterministic tie breaker on validation R_Z.
profiles=(depth2 depth3 depth4 depth3_800)
box_grids=(40 80 160)
benchmarks=(
  "vector 1.000"
  "vector 10.000"
  "scalar 1.000"
  "scalar 6.310"
)

fail() {
  echo "error: $*" >&2
  exit 2
}

require_uint() {
  local name=$1
  local value=$2
  [[ "$value" =~ ^[0-9]+$ ]] || fail "$name must be a non-negative integer"
}

for item in \
  "ROBUST_REPLICATES:$replicates" \
  "ROBUST_TRAIN_EVENTS:$train_events" \
  "ROBUST_VALIDATION_EVENTS:$validation_events" \
  "ROBUST_TEST_EVENTS:$test_events" \
  "ROBUST_CELLS:$cells" \
  "ROBUST_SAMPLES:$samples" \
  "ROBUST_BOX_RESTARTS:$box_restarts" \
  "ROBUST_PAIRED_BOOTSTRAPS:$paired_bootstraps" \
  "ROBUST_AGGREGATE_BOOTSTRAPS:$aggregate_bootstraps" \
  "ROBUST_SEED_BASE:$seed_base"; do
  require_uint "${item%%:*}" "${item#*:}"
done

((replicates >= 10)) || fail "ROBUST_REPLICATES must be at least 10"
((train_events > 0 && validation_events > 0 && test_events > 0)) || \
  fail "all event budgets must be positive"
((cells > 0 && samples > 0)) || fail "TFoam settings must be positive"
((box_restarts > 0)) || fail "box restarts must be positive"
((paired_bootstraps >= 500 && aggregate_bootstraps >= 100)) || \
  fail "paired bootstraps must be >=500 and aggregate bootstraps >=100"
[[ "$run_id" =~ ^[A-Za-z0-9._-]+$ ]] || \
  fail "ROBUST_RUN_ID may contain only letters, digits, dot, underscore, dash"
[[ ! -e "$run_dir" ]] || fail "output already exists: $run_dir"

largest_seed=$((seed_base + replicates * 10000 + 500))
((largest_seed < 4294967295)) || fail "seed schedule exceeds 32-bit range"
aggregate_bootstrap_seed=$((seed_base + 99))

lookup_rate() {
  local file=$1
  local mass=$2
  local column=$3
  awk -F, -v target="$mass" -v col="$column" \
    'NR>1 && sprintf("%.3f",$1)==sprintf("%.3f",target){print $col; exit}' \
    "$file"
}

record_seed() {
  local replicate=$1
  local signal_type=$2
  local mass=$3
  local purpose=$4
  local profile=$5
  local seed=$6
  printf '%s,%s,%s,%s,%s,%s\n' \
    "$replicate" "$signal_type" "$mass" "$purpose" "$profile" "$seed" \
    >>"$run_dir/seed_manifest.csv"
}

validate_generated() {
  local file=$1 cut_mass=$2 photon=$3 log=$4 process=$5
  local generator_mass=$6 coupling=$7 seed=$8 event_count=$9
  local qe2_min pt_min eta_min eta_max energy_max
  IFS=, read -r qe2_min pt_min eta_min eta_max energy_max < <(
    awk -F, -v target="$cut_mass" \
      'NR>1 && sprintf("%.3f",$1)==sprintf("%.3f",target) \
       {print $2","$3","$4","$5","$6; exit}' \
      "$project_dir/config/paper_cuts.csv"
  )
  "$project_dir/bin/validate_sealed_sample" "$file" "$qe2_min" "$pt_min" \
    "$eta_min" "$eta_max" "$energy_max" "$photon" 100 \
    "$process" "$generator_mass" "$cut_mass" "$coupling" "$seed" \
    "$event_count" "$cells" "$samples" >>"$log" 2>&1
}

generate_signal() {
  local signal_type=$1
  local mass=$2
  local events=$3
  local seed=$4
  local output=$5
  local log=$6
  local generator="$project_dir/bin/generate_${signal_type}"
  local command=(
    "$generator" --mass "$mass" --events "$events" --cells "$cells"
    --samples "$samples" --seed "$seed" --output "$output"
  )
  if [[ "$signal_type" == "vector" ]]; then
    command+=(--integrate-paper-cut --quiet)
  else
    command+=(--selected)
  fi
  "${command[@]}" >"$log" 2>&1
  validate_generated "$output" "$mass" 0 "$log" "$signal_type" \
    "$mass" 0.0001 "$seed" "$events"
}

generate_photon() {
  local cut_mass=$1
  local events=$2
  local seed=$3
  local output=$4
  local log=$5
  "$project_dir/bin/generate_vector" \
    --mass "$photon_mass" --cut-mass "$cut_mass" \
    --coupling "$electric_charge" --events "$events" --cells "$cells" \
    --samples "$samples" --seed "$seed" --integrate-paper-cut --quiet \
    --output "$output" >"$log" 2>&1
  validate_generated "$output" "$cut_mass" 1 "$log" vector \
    "$photon_mass" "$electric_charge" "$seed" "$events"
}

mkdir -p "$run_dir"
printf '%s\n' \
  'replicate,signal_type,mass_GeV,purpose,model_profile,seed' \
  >"$run_dir/seed_manifest.csv"
printf '%s\n' \
  'run_id,replicates,train_attempts_per_class,validation_attempts_per_class,test_attempts_per_class,cells,samples,feature_set,profiles,box_quantile_grids,box_restarts,paired_bootstraps,aggregate_bootstraps,seed_base,aggregate_bootstrap_seed,photon_regulator_mass_GeV,electric_charge' \
  >"$run_dir/run_config.csv"
printf '%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s\n' \
  "$run_id" "$replicates" "$train_events" "$validation_events" \
  "$test_events" "$cells" "$samples" 'electron' \
  'depth2;depth3;depth4;depth3_800' '40;80;160' "$box_restarts" \
  "$paired_bootstraps" "$aggregate_bootstraps" "$seed_base" \
  "$aggregate_bootstrap_seed" "$photon_mass" "$electric_charge" \
  >>"$run_dir/run_config.csv"
record_seed 0 all all aggregate_bootstrap NA "$aggregate_bootstrap_seed"

make -C "$project_dir" \
  bin/generate_vector bin/generate_scalar bin/train_tmva \
  bin/optimize_rectangular_fair bin/evaluate_fair_model \
  bin/validate_sealed_sample

method_manifest="$run_dir/method_manifest.sha256"
(
  cd "$project_dir"
  shasum -a 256 \
    src/generate_vector.cpp src/generate_scalar.cpp \
    include/DarkBosonKinematics.h src/validate_sealed_sample.cpp \
    src/train_tmva.cpp \
    src/optimize_rectangular_fair.cpp src/evaluate_fair_model.cpp \
    scripts/run_seed_robustness.sh scripts/summarize_seed_robustness.py \
    docs/seed_robustness_protocol.md config/paper_cuts.csv \
    results/background_rates_from_table_I.csv \
    frozen_baseline/results/vector_scan_fresh.csv \
    frozen_baseline/results/scalar_scan.csv \
    bin/generate_vector bin/generate_scalar bin/train_tmva \
    bin/optimize_rectangular_fair bin/evaluate_fair_model \
    bin/validate_sealed_sample
) >"$method_manifest"
(cd "$project_dir" && shasum -a 256 -c "$method_manifest" >/dev/null)

for ((replicate = 1; replicate <= replicates; ++replicate)); do
  rep_tag=$(printf 'rep_%03d' "$replicate")
  for point_index in "${!benchmarks[@]}"; do
    read -r signal_type mass <<<"${benchmarks[$point_index]}"
    mass_tag=${mass//./p}
    point_tag="${signal_type}_m${mass_tag}"
    point_dir="$run_dir/$rep_tag/$point_tag"
    data_dir="$point_dir/data"
    models_dir="$point_dir/models"
    logs_dir="$point_dir/logs"
    mkdir -p "$data_dir" "$models_dir" "$logs_dir"

    block=$((seed_base + replicate * 10000 + point_index * 100))
    signal_train_seed=$((block + 1))
    signal_validation_seed=$((block + 2))
    signal_test_seed=$((block + 3))
    photon_train_seed=$((block + 11))
    photon_validation_seed=$((block + 12))
    photon_test_seed=$((block + 13))
    box_seed=$((block + 21))
    paired_bootstrap_seed=$((block + 22))
    tmva_seed=$((block + 31))

    signal_train="$data_dir/signal_train.root"
    signal_validation="$data_dir/signal_validation.root"
    signal_test="$data_dir/signal_test.root"
    photon_train="$data_dir/photon_train.root"
    photon_validation="$data_dir/photon_validation.root"
    photon_test="$data_dir/photon_test.root"

    generate_signal "$signal_type" "$mass" "$train_events" \
      "$signal_train_seed" "$signal_train" "$logs_dir/signal_train.log"
    generate_signal "$signal_type" "$mass" "$validation_events" \
      "$signal_validation_seed" "$signal_validation" \
      "$logs_dir/signal_validation.log"
    generate_photon "$mass" "$train_events" "$photon_train_seed" \
      "$photon_train" "$logs_dir/photon_train.log"
    generate_photon "$mass" "$validation_events" \
      "$photon_validation_seed" "$photon_validation" \
      "$logs_dir/photon_validation.log"

    record_seed "$replicate" "$signal_type" "$mass" signal_train NA \
      "$signal_train_seed"
    record_seed "$replicate" "$signal_type" "$mass" signal_validation NA \
      "$signal_validation_seed"
    record_seed "$replicate" "$signal_type" "$mass" photon_train NA \
      "$photon_train_seed"
    record_seed "$replicate" "$signal_type" "$mass" photon_validation NA \
      "$photon_validation_seed"

    if [[ "$signal_type" == "vector" ]]; then
      signal_xs=$(lookup_rate \
        "$project_dir/frozen_baseline/results/vector_scan_fresh.csv" \
        "$mass" 4)
    else
      signal_xs=$(lookup_rate \
        "$project_dir/frozen_baseline/results/scalar_scan.csv" "$mass" 4)
    fi
    photon_xs=$(lookup_rate \
      "$project_dir/results/background_rates_from_table_I.csv" "$mass" 2)
    dis_xs=$(lookup_rate \
      "$project_dir/results/background_rates_from_table_I.csv" "$mass" 3)
    [[ -n "$signal_xs" && -n "$photon_xs" && -n "$dis_xs" ]] || \
      fail "missing rate for $signal_type mass $mass"

    for profile in "${profiles[@]}"; do
      model_dir="$models_dir/$profile"
      "$project_dir/bin/train_tmva" \
        "$signal_train" "$signal_validation" \
        "$photon_train" "$photon_validation" \
        "$model_dir" "$signal_type" "$mass" \
        "$signal_xs" "$photon_xs" "$dis_xs" \
        electron "$profile" "$tmva_seed" validation_all \
        >"$logs_dir/tmva_${profile}.log" 2>&1
      record_seed "$replicate" "$signal_type" "$mass" tmva "$profile" \
        "$tmva_seed"
    done

    selected_metrics="$point_dir/selected_model_metrics.csv"
    selected_profile=$(python3 \
      "$project_dir/scripts/summarize_seed_robustness.py" select-profile \
      --models-dir "$models_dir" \
      --profiles 'depth2,depth3,depth4,depth3_800' \
      --output "$selected_metrics")

    boxes_dir="$point_dir/boxes"
    mkdir -p "$boxes_dir"
    # The fair optimizer requires final-test positional arguments. Validation
    # files are deliberately supplied again there; only the selected bounds are
    # retained. The sealed test files do not exist yet and are evaluated once,
    # jointly for BDT and box, below.
    for box_grid in "${box_grids[@]}"; do
      "$project_dir/bin/optimize_rectangular_fair" \
        "$signal_train" "$photon_train" \
        "$signal_validation" "$photon_validation" \
        "$signal_validation" "$photon_validation" \
        "$boxes_dir/q${box_grid}.csv" "$signal_type" "$mass" \
        "$signal_xs" "$photon_xs" "$dis_xs" electron \
        "$box_grid" "$box_restarts" "$box_seed" \
        >"$logs_dir/rectangular_q${box_grid}.log" 2>&1
    done
    box_metrics="$point_dir/selected_box_metrics.csv"
    selected_box_grid=$(python3 \
      "$project_dir/scripts/summarize_seed_robustness.py" select-box \
      --boxes-dir "$boxes_dir" --grids '40,80,160' --output "$box_metrics")
    record_seed "$replicate" "$signal_type" "$mass" box_optimizer NA \
      "$box_seed"

    # Generate the sealed test only after BDT profile, threshold, and box are
    # frozen from training/validation.
    generate_signal "$signal_type" "$mass" "$test_events" \
      "$signal_test_seed" "$signal_test" "$logs_dir/signal_test.log"
    generate_photon "$mass" "$test_events" "$photon_test_seed" \
      "$photon_test" "$logs_dir/photon_test.log"
    record_seed "$replicate" "$signal_type" "$mass" signal_test NA \
      "$signal_test_seed"
    record_seed "$replicate" "$signal_type" "$mass" photon_test NA \
      "$photon_test_seed"
    record_seed "$replicate" "$signal_type" "$mass" paired_bootstrap NA \
      "$paired_bootstrap_seed"

    selected_weights="$models_dir/$selected_profile/dataset/weights/TMVAClassification_BDTG.weights.xml"
    paired_output="$point_dir/paired_test.csv"
    "$project_dir/bin/evaluate_fair_model" \
      "$signal_test" "$photon_test" "$selected_weights" \
      "$selected_metrics" "$box_metrics" "$paired_output" \
      electron "$photon_xs" "$dis_xs" \
      "$paired_bootstraps" "$paired_bootstrap_seed" \
      >"$logs_dir/paired_test.log" 2>&1

    printf '%s\n' \
      'signal_type,mass_GeV,replicate,feature_set,selected_profile,selected_box_quantiles,signal_xs_pb,photon_xs_pb,dis_xs_pb,signal_train_seed,signal_validation_seed,signal_test_seed,photon_train_seed,photon_validation_seed,photon_test_seed,tmva_seed,box_seed,paired_bootstrap_seed' \
      >"$point_dir/point_metadata.csv"
    printf '%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s\n' \
      "$signal_type" "$mass" "$replicate" electron "$selected_profile" \
      "$selected_box_grid" \
      "$signal_xs" "$photon_xs" "$dis_xs" \
      "$signal_train_seed" "$signal_validation_seed" "$signal_test_seed" \
      "$photon_train_seed" "$photon_validation_seed" "$photon_test_seed" \
      "$tmva_seed" "$box_seed" "$paired_bootstrap_seed" \
      >>"$point_dir/point_metadata.csv"

    echo "completed replicate=$replicate $signal_type m=$mass profile=$selected_profile"
  done
done

python3 "$project_dir/scripts/summarize_seed_robustness.py" summarize \
  --run-dir "$run_dir" \
  --bootstrap-replicates "$aggregate_bootstraps" \
  --bootstrap-seed "$aggregate_bootstrap_seed"

(cd "$project_dir" && shasum -a 256 -c "$method_manifest" >/dev/null)
result_manifest="$run_dir/result_manifest.sha256"
find "$run_dir" -type f ! -name 'result_manifest.sha256' -print0 \
  | sort -z | xargs -0 shasum -a 256 >"$result_manifest"
shasum -a 256 -c "$result_manifest" >/dev/null

echo "Created robustness study: $run_dir"
