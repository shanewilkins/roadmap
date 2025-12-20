#!/bin/bash
# Generate API documentation from Python docstrings using Sphinx autodoc

set -e

echo "🔄 Generating API Documentation..."

# Change to project root
cd "$(dirname "$0")/.."

# Run sphinx-apidoc to generate .rst files from docstrings
echo "📚 Running sphinx-apidoc to generate API reference..."
poetry run sphinx-apidoc \
    -f \
    -o docs/sphinx/source/api \
    --implicit-namespaces \
    --module-first \
    --maxdepth 2 \
    roadmap \
    roadmap/tests \
    roadmap/**/*.pyc

echo "✅ API documentation generated!"
echo "   📁 Output: docs/sphinx/source/api/"
echo ""
echo "💡 Tip: Run build_sphinx_docs.sh to build the complete documentation"
