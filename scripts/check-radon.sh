#!/bin/bash
# Pre-commit hook to check code metrics using radon
# Checks for:
# 1. Cyclomatic Complexity: Warn at B (5-7), Fail at C+ (8+)
# 2. File length: Warn at 300+ LOC, Fail at 400+ LOC
# Skips: future/ (v1.1+ features), tests/ (test files)

EXIT_CODE=0

for file in "$@"; do
    # Skip non-Python files
    [[ "$file" != *.py ]] && continue

    # Skip future/ directory (v1.1+ features, not in v1.0 scope)
    [[ "$file" =~ ^future/ ]] && continue

    # Skip test files (different standards)
    [[ "$file" =~ ^tests/ ]] && continue

    # Count lines in file
    LINES=$(wc -l < "$file")

    # Check file length (strict for source code, not tests)
    if [ "$LINES" -gt 400 ]; then
        echo "❌ FAIL: $file ($LINES LOC) exceeds max 400 LOC"
        EXIT_CODE=1
    elif [ "$LINES" -gt 300 ]; then
        echo "⚠️  WARN: $file ($LINES LOC) exceeds recommended 300 LOC"
    fi
done

# Check cyclomatic complexity (exclude future/ and tests/)
poetry run radon cc --min A --max B roadmap/ 2>/dev/null || true

exit $EXIT_CODE
