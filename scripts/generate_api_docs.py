#!/usr/bin/env python3
"""
API Documentation Generator

Generates comprehensive API documentation using Sphinx autodoc.
"""

import subprocess
from pathlib import Path


def setup_sphinx_project(docs_dir: Path, project_root: Path):
    """Set up Sphinx documentation project."""

    # Create sphinx directory structure
    sphinx_dir = docs_dir / "sphinx"
    sphinx_dir.mkdir(exist_ok=True)

    source_dir = sphinx_dir / "source"
    build_dir = sphinx_dir / "build"

    source_dir.mkdir(exist_ok=True)
    build_dir.mkdir(exist_ok=True)

    # Create conf.py
    conf_content = f"""# Configuration file for the Sphinx documentation builder.

import os
import sys
sys.path.insert(0, '{project_root.absolute()}')

# -- Project information -----------------------------------------------------
project = 'Roadmap CLI'
copyright = '2025, Roadmap CLI Team'
author = 'Roadmap CLI Team'
release = '0.1.0'

# -- General configuration ---------------------------------------------------
extensions = [
    'sphinx.ext.autodoc',
    'sphinx.ext.viewcode',
    'sphinx.ext.napoleon',
    'sphinx.ext.intersphinx',
    'sphinx.ext.githubpages',
    'myst_parser',
    'sphinx_click',
]

templates_path = ['_templates']
exclude_patterns = []

# -- Options for HTML output ------------------------------------------------
html_theme = 'sphinx_rtd_theme'
html_static_path = ['_static']

# -- Extension configuration -------------------------------------------------
autodoc_default_options = {{
    'members': True,
    'member-order': 'bysource',
    'special-members': '__init__',
    'undoc-members': True,
    'exclude-members': '__weakref__'
}}

napoleon_google_docstring = True
napoleon_numpy_docstring = True
napoleon_include_init_with_doc = False
napoleon_include_private_with_doc = False

intersphinx_mapping = {{
    'python': ('https://docs.python.org/3', None),
    'click': ('https://click.palletsprojects.com/en/8.1.x/', None),
}}

# Source file suffixes
source_suffix = {{
    '.rst': None,
    '.md': 'myst_parser',
}}
"""

    (source_dir / "conf.py").write_text(conf_content)

    # Create index.rst
    index_content = """Roadmap CLI API Documentation
=============================

.. toctree::
   :maxdepth: 2
   :caption: Contents:

   modules
   cli

Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`
"""

    (source_dir / "index.rst").write_text(index_content)

    # Create CLI documentation
    cli_content = """CLI Reference
=============

.. click:: roadmap.cli:main
   :prog: roadmap
   :nested: full
"""

    (source_dir / "cli.rst").write_text(cli_content)

    return sphinx_dir, source_dir, build_dir


def generate_api_docs(project_root: Path, source_dir: Path):
    """Generate API documentation using sphinx-apidoc."""

    # Generate module documentation
    roadmap_dir = project_root / "roadmap"

    cmd = [
        "sphinx-apidoc",
        "-f",  # Force overwrite
        "-o",
        str(source_dir),  # Output directory
        str(roadmap_dir),  # Source directory
        "--separate",  # Create separate files for modules
    ]

    try:
        subprocess.run(cmd, check=True, cwd=project_root)
        print("✅ Generated API documentation with sphinx-apidoc")
    except subprocess.CalledProcessError as e:
        print(f"❌ Failed to run sphinx-apidoc: {e}")
        return False

    return True


def build_sphinx_docs(sphinx_dir: Path, source_dir: Path, build_dir: Path):
    """Build Sphinx documentation."""

    cmd = [
        "sphinx-build",
        "-b",
        "html",  # HTML builder
        str(source_dir),
        str(build_dir / "html"),
    ]

    try:
        subprocess.run(cmd, check=True, cwd=sphinx_dir)
        print("✅ Built Sphinx HTML documentation")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Failed to build Sphinx docs: {e}")
        return False


def create_automation_scripts(project_root: Path):
    """Create automation scripts for documentation generation."""

    scripts_dir = project_root / "scripts"
    scripts_dir.mkdir(exist_ok=True)

    # Create documentation build script
    build_script = """#!/bin/bash
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
"""

    build_script_path = scripts_dir / "build_docs.sh"
    build_script_path.write_text(build_script)
    build_script_path.chmod(0o755)

    # Create documentation server script
    serve_script = """#!/bin/bash
# Documentation Development Server

cd "$(dirname "$0")/.."

echo "🌐 Starting MkDocs development server..."
echo "📍 Open http://localhost:8000 in your browser"
echo "🔄 Docs will auto-reload on changes"
echo ""

poetry run mkdocs serve
"""

    serve_script_path = scripts_dir / "serve_docs.sh"
    serve_script_path.write_text(serve_script)
    serve_script_path.chmod(0o755)

    print("✅ Created automation scripts:")
    print(f"   • {build_script_path}")
    print(f"   • {serve_script_path}")


def main():
    """Generate API documentation."""
    # Determine paths
    script_dir = Path(__file__).parent
    project_root = script_dir.parent
    docs_dir = project_root / "docs"

    print("🔄 Setting up API documentation...")

    # Setup Sphinx project
    sphinx_dir, source_dir, build_dir = setup_sphinx_project(docs_dir, project_root)
    print(f"✅ Set up Sphinx project in {sphinx_dir}")

    # Generate API docs
    if generate_api_docs(project_root, source_dir):
        print("✅ Generated API documentation")

    # Create automation scripts
    create_automation_scripts(project_root)

    print("\n📊 Documentation Setup Summary:")
    print(f"   • Sphinx project: {sphinx_dir}")
    print(f"   • API docs: {source_dir}")
    print(f"   • Build output: {build_dir}")
    print("\n🚀 Next steps:")
    print("   1. Install doc dependencies: poetry install --with dev")
    print("   2. Build all docs: ./scripts/build_docs.sh")
    print("   3. Serve docs: ./scripts/serve_docs.sh")


if __name__ == "__main__":
    main()
