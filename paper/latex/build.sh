#!/bin/sh
set -eu
cd "$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)"
# MacTeX installs its command-line tools here.
PATH="/Library/TeX/texbin:$PATH"
export PATH
if ! command -v latexmk >/dev/null 2>&1; then
    echo 'latexmk is required. Install a TeX distribution such as MacTeX or TeX Live.' >&2
    exit 1
fi
latexmk -pdf -interaction=nonstopmode -halt-on-error -file-line-error -outdir=build main.tex
cp build/main.pdf main.pdf
printf '\nPDF ready: %s/main.pdf\n' "$PWD"
