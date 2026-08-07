#!/usr/bin/env bash
set -euo pipefail

# Fail if any function or method exceeds CC > 15.
violations="$( {
  uv run radon cc roadmap --exclude=tests -s |
    awk '
      /^[^[:space:]].*\.py$/ { file=$0; next }
      /^[[:space:]]+[FMC][[:space:]]/ {
        line=$0
        if (line ~ /\([0-9]+\)$/) {
          cc=line
          sub(/^.*\(/, "", cc)
          sub(/\)$/, "", cc)
          if ((cc + 0) > 15) {
            gsub(/^[[:space:]]+/, "", line)
            print file "|" line
          }
        }
      }
    '
} || true )"

if [[ -n "$violations" ]]; then
  echo "$violations"
  exit 1
fi

exit 0
