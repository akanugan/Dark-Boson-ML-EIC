#!/usr/bin/env bash
set -euo pipefail

project_dir=$(cd "$(dirname "$0")/.." && pwd)
sdk_include=/Library/Developer/CommandLineTools/SDKs/MacOSX26.2.sdk/usr/include/c++/v1

mkdir -p "$project_dir/plots"
make -C "$project_dir" bin/plot_results
CPLUS_INCLUDE_PATH="$sdk_include${CPLUS_INCLUDE_PATH:+:$CPLUS_INCLUDE_PATH}" \
  "$project_dir/bin/plot_results" \
  "$project_dir/results/ml/ml_metrics.csv" \
  "$project_dir/plots" \
  "$project_dir/models/vector_m10p000/test_scores.csv"
