#!/bin/bash
# Sphinx Documentation Development Server

cd "$(dirname "$0")/.."

echo "🌐 Starting Sphinx documentation server..."
echo "📍 Open http://localhost:8000 in your browser"
echo "🔄 Docs will auto-reload on changes"
echo ""

cd docs/sphinx/build/html
python -m http.server 8000
