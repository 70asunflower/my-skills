#!/usr/bin/env bash
# Compile the project with XeLaTeX. The table of contents needs at least TWO
# passes: pass 1 writes the .toc file, pass 2 reads it back to render entries.
# A single pass => blank TOC (normal LaTeX behaviour, NOT an error).
set -e
MAIN="$(ls -1 *.tex 2>/dev/null | head -n1)"
if [ -z "$MAIN" ]; then echo "No .tex file found in this folder."; exit 1; fi
echo "[compile] main file: $MAIN"
if command -v latexmk >/dev/null 2>&1; then
  latexmk -xelatex -interaction=nonstopmode "$MAIN"      # auto multi-pass
else
  for i in 1 2 3; do
    xelatex -interaction=nonstopmode -halt-on-error "$MAIN"
  done
fi
echo "[compile] done. Verify the TOC page is no longer blank."
