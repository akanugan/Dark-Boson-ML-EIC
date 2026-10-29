#!/usr/bin/env bash
# Build the simulation, selection, and evaluation programs.
set -euo pipefail
project_dir=$(cd "$(dirname "$0")" && pwd)
root_config=${ROOT_CONFIG:-root-config}
compiler=${CXX:-c++}
if [[ $# -gt 0 ]]; then
  echo 'Usage: ./build.sh' >&2
  exit 2
fi
command -v "$root_config" >/dev/null || { echo 'Set ROOT_CONFIG or put root-config on PATH.' >&2; exit 1; }
read -r -a root_cflags <<< "$("$root_config" --cflags)"
read -r -a root_libs <<< "$("$root_config" --libs)"
common=(-std=c++17 -O2 "${root_cflags[@]}" "-I$project_dir/include")
if [[ -n ${BOOST_INCLUDEDIR:-} ]]; then
  common+=("-I$BOOST_INCLUDEDIR")
fi
mkdir -p "$project_dir/bin"
for source in "$project_dir"/src/*.cpp; do
  name=$(basename "${source%.cpp}")
  echo "Building bin/$name"
  "$compiler" "${common[@]}" "$source" -o "$project_dir/bin/$name" "${root_libs[@]}" -lTMVA -lFoam
done
echo 'Build complete. No events generated or models fitted.'
