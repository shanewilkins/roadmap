#!/bin/bash
# Fast test runner script - skips slow integration tests
# Usage: ./scripts/test_fast.sh

echo "🚀 Running fast tests (excluding slow integration tests)..."
echo "=================================================="

cd "$(dirname "$0")/.."

# Run tests excluding slow ones
poetry run pytest -m "not slow" --tb=short -v

echo ""
echo "📊 For complete test suite (including slow tests):"
echo "   poetry run pytest"
echo ""
echo "🎯 For unit tests only (fastest):"
echo "   poetry run pytest -m unit"
