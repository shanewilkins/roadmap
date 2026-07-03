#!/usr/bin/env bash
set -uo pipefail

threshold=500
found=0

# Warn on tracked Python source files only; never fail the commit.
while IFS= read -r file; do
  [[ -z "$file" ]] && continue
  if [[ ! -f "$file" ]]; then
    continue
  fi
  lines=$(wc -l < "$file" | tr -d ' ')
  if [[ "$lines" -gt "$threshold" ]]; then
    if [[ "$found" -eq 0 ]]; then
      echo "[warn] Long files detected (>${threshold} lines):"
    fi
    found=1
    echo "  - ${file} (${lines} lines)"
  fi
done < <(git ls-files '*.py')

if [[ "$found" -eq 1 ]]; then
  echo "[warn] Consider splitting large files into smaller modules when practical."
fi

exit 0
