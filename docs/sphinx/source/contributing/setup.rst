================================================================================
Development Setup
================================================================================

Setting up your development environment.

.. note::

   This is a stub. Complete implementation coming in v.0.7.0.

Prerequisites
=============

- Python 3.10 or higher
- Poetry (for dependency management)
- Git
- Optional: Docker (for containerized development)

Installation
============

Clone and set up the development environment:

.. code-block:: bash

    git clone https://github.com/roadmap-cli/roadmap.git
    cd roadmap
    poetry install

This installs all dependencies including development tools:

- pytest - Testing framework
- ruff - Fast Python linter
- mypy - Static type checker
- sphinx - Documentation generation

Verifying Setup
===============

Run the test suite to verify your setup:

.. code-block:: bash

    poetry run pytest

All tests should pass.

See Also
========

- :doc:`development` - Development workflow
- :doc:`testing` - Testing guidelines
