#!/bin/bash
# Documentation Build Script

set -e

echo "🔄 Building Roadmap CLI Documentation..."

# Change to project root
cd "$(dirname "$0")/.."

# Install documentation dependencies
echo "📦 Installing documentation dependencies..."
poetry install --with dev

# Generate CLI reference
echo "📝 Generating CLI reference..."
python scripts/generate_cli_docs.py

# Generate API documentation
echo "📚 Generating API documentation..."
python scripts/generate_api_docs.py

# Build MkDocs site
echo "🌐 Building MkDocs site..."
poetry run mkdocs build

# Build Sphinx documentation
echo "📖 Building Sphinx documentation..."
cd docs/sphinx
poetry run sphinx-build -b html source build/html

echo "✅ Documentation build complete!"
echo ""
echo "📂 Output locations:"
echo "   • MkDocs site: site/"
echo "   • Sphinx docs: docs/sphinx/build/html/"
echo "   • CLI reference: docs/CLI_REFERENCE_AUTO.md"
