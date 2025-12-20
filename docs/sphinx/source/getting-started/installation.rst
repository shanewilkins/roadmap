================================================================================
Installation
================================================================================

Prerequisites
=============

- Python 3.10 or higher
- pip or Poetry (for development)
- Git (optional, for GitHub integration)

Installing from PyPI
=====================

The recommended way to install Roadmap CLI is via PyPI:

.. code-block:: bash

    pip install roadmap-cli

This installs the stable, production-ready version.

Installing from Source (Development)
=====================================

To install from source for development:

.. code-block:: bash

    git clone https://github.com/roadmap-cli/roadmap.git
    cd roadmap
    poetry install

This installs the latest development version with all dependencies.

Verifying the Installation
===========================

To verify your installation:

.. code-block:: bash

    roadmap --version

You should see the version number displayed.

Troubleshooting
===============

**Command not found: roadmap**

If you get a "command not found" error:

1. Ensure Python is in your PATH
2. Try ``python -m roadmap`` instead
3. For Poetry installations, ensure you're in the project directory

**Version mismatch**

If you have multiple Python versions installed:

.. code-block:: bash

    python3 -m pip install roadmap-cli

See the :doc:`../troubleshooting` page for more help.
