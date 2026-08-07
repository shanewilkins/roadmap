# Configuration file for the Sphinx documentation builder.

import sys
from pathlib import Path

sys.path.insert(0, "/Users/shane/roadmap")

# -- Project information -----------------------------------------------------
project = "Roadmap CLI"
copyright = "2025, Roadmap CLI Team"
author = "Roadmap CLI Team"


# Get version from pyproject.toml
def get_version():
    """Extract version from pyproject.toml."""
    pyproject = Path(__file__).parent.parent.parent.parent / "pyproject.toml"
    if pyproject.exists():
        with open(pyproject) as f:
            for line in f:
                if line.strip().startswith('version = "'):
                    return line.split('"')[1]
    return "0.6.0"


release = get_version()
version = release

# -- General configuration ---------------------------------------------------
extensions = [
    "sphinx.ext.autodoc",
    "sphinx.ext.viewcode",
    "sphinx.ext.napoleon",
    "sphinx.ext.intersphinx",
    "sphinx.ext.githubpages",
    "myst_parser",
    "sphinx_click",
]

templates_path = ["_templates"]
exclude_patterns = []

# -- Options for HTML output ------------------------------------------------
html_theme = "sphinx_rtd_theme"
html_static_path = ["_static"]

# -- Extension configuration -------------------------------------------------
autodoc_default_options = {
    "members": True,
    "member-order": "bysource",
    "special-members": "__init__",
    "undoc-members": True,
    "exclude-members": "__weakref__",
}

napoleon_google_docstring = True
napoleon_numpy_docstring = True
napoleon_include_init_with_doc = False
napoleon_include_private_with_doc = False

intersphinx_mapping = {
    "python": ("https://docs.python.org/3", None),
    "click": ("https://click.palletsprojects.com/en/8.1.x/", None),
}

# Source file suffixes
source_suffix = {
    ".rst": None,
    ".md": "myst_parser",
}
