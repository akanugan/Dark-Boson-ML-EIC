#!/usr/bin/env bash
set -euo pipefail

project_dir=$(cd "$(dirname "$0")/.." && pwd)
study="$project_dir/fair_study/rigorous"
selected="$study/development_frozen/selected_models.csv"
sealed="$project_dir/data/ml/sealed/root"
output="$study/final"
primary_bootstrap=50000
oracle_bootstrap=5000

[[ ! -e "$output" ]] || {
  echo "Refusing to overwrite final sealed evaluation: $output" >&2
  exit 1
}

[[ -f "$study/frozen_method_manifest.sha256" ]] || {
  echo "Missing frozen manifest; run generate_sealed_tests.sh first" >&2
  exit 1
}
[[ -f "$study/sealed_data_manifest.sha256" ]] || {
  echo "Missing sealed data manifest" >&2
  exit 1
}

(cd "$project_dir" && shasum -a 256 -c "$study/frozen_method_manifest.sha256" \
  >/dev/null) || {
  echo "Frozen method/model verification failed; sealed data not opened" >&2
  exit 1
}
(cd "$project_dir" && shasum -a 256 -c "$study/sealed_data_manifest.sha256" \
  >/dev/null) || {
  echo "Sealed data verification failed; data not opened" >&2
  exit 1
}

mkdir -p "$output"

python3 "$project_dir/scripts/run_sealed_evaluation.py" \
  "$primary_bootstrap" "$oracle_bootstrap"

python3 "$project_dir/scripts/summarize_rigorous_final.py"

(cd "$project_dir" && shasum -a 256 -c "$study/frozen_method_manifest.sha256" \
  >/dev/null)
(cd "$project_dir" && shasum -a 256 -c "$study/sealed_data_manifest.sha256" \
  >/dev/null)

final_manifest="$study/final_results_manifest.sha256"
[[ ! -e "$final_manifest" ]] || {
  echo "Refusing to overwrite final result manifest" >&2
  exit 1
}
find "$output" -type f -print0 | sort -z | xargs -0 shasum -a 256 \
  >"$final_manifest"
shasum -a 256 -c "$final_manifest" >/dev/null
