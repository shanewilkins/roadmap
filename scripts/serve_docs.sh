#!/bin/bash
# Documentation Development Server

cd "$(dirname "$0")/.."

echo "🌐 Starting MkDocs development server..."
echo "📍 Open http://localhost:8000 in your browser"
echo "🔄 Docs will auto-reload on changes"
echo ""

poetry run mkdocs serve
