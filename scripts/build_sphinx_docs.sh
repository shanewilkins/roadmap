#!/bin/bash
# Sphinx Documentation Build Script

set -e

echo "🔄 Building Sphinx Documentation..."

# Change to project root
cd "$(dirname "$0")/.."

# Install documentation dependencies
echo "📦 Installing documentation dependencies..."
poetry install --with dev

# Generate API documentation from docstrings
echo "📚 Generating API documentation from docstrings..."
bash scripts/generate_api_docs.sh

# Build Sphinx documentation
echo "🌐 Building Sphinx HTML documentation..."
cd docs/sphinx
poetry run sphinx-build -b html source build/html

echo "✅ Documentation build complete!"
echo ""
echo "📂 Output location:"
echo "   • Sphinx docs: docs/sphinx/build/html/index.html"
echo ""
echo "💡 Tip: Run serve_sphinx_docs.sh to preview the documentation locally"
