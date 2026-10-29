#!/usr/bin/env bash
# Build scientific tools from source. ROOT/TMVA and Boost headers are external.
set -euo pipefail
revision_dir=$(cd "$(dirname "$0")" && pwd)
project_dir=$(cd "$revision_dir/.." && pwd)
root_config=${ROOT_CONFIG:-root-config}
compiler=${CXX:-c++}
benchmarks=false
if [[ ${1:-} == --benchmarks ]]; then
  benchmarks=true
elif [[ $# -gt 0 ]]; then
  echo "Usage: revision/build.sh [--benchmarks]" >&2
  exit 2
fi
command -v "$root_config" >/dev/null || { echo 'Set ROOT_CONFIG or put root-config on PATH.' >&2; exit 1; }
read -r -a root_cflags <<< "$("$root_config" --cflags)"
read -r -a root_libs <<< "$("$root_config" --libs)"
common=(-std=c++17 -O2 "${root_cflags[@]}" "-I$project_dir/include")
if [[ -n ${BOOST_INCLUDEDIR:-} ]]; then
  common+=("-I$BOOST_INCLUDEDIR")
fi
libs=("${root_libs[@]}" -lTMVA -lFoam)
build_one() {
  local source=$1 output=$2
  mkdir -p "$(dirname "$output")"
  echo "Building ${output#"$project_dir/"}"
  "$compiler" "${common[@]}" "$source" -o "$output" "${libs[@]}"
}

# Original signal generators, BDT trainer and rectangular optimizer are still
# dependencies of the revised study. No LaTeX/compiler target is invoked.
for name in generate_vector generate_scalar train_tmva optimize_rectangular_fair; do
  build_one "$project_dir/src/$name.cpp" "$project_dir/bin/$name"
done
for source in "$revision_dir"/src/*.cpp; do
  build_one "$source" "$revision_dir/bin/$(basename "${source%.cpp}")"
done
for source in "$revision_dir"/stratified_repair/src/*.cpp; do
  build_one "$source" "$revision_dir/stratified_repair/bin/$(basename "${source%.cpp}")"
done
if $benchmarks; then
  for source in "$revision_dir"/rate_benchmark/sources/*.cpp; do
    build_one "$source" "$revision_dir/rate_benchmark/bin/$(basename "${source%.cpp}")"
  done
  for source in "$revision_dir"/rate_benchmark/*.cpp; do
    build_one "$source" "$revision_dir/rate_benchmark/bin/$(basename "${source%.cpp}")"
  done
fi
echo 'Build complete. This does not generate events, train models or run analyses.'
