================================================================================
Installation
================================================================================

Get Roadmap CLI up and running on your system.

Prerequisites
=============

- **Python 3.10 or higher** - Check with ``python --version``
- **pip** (included with Python) or **Poetry** (for development)
- **Git** (optional, for GitHub integration features)

Quick Install (Recommended)
===========================

The recommended way to install Roadmap CLI is via PyPI using pip:

.. code-block:: bash

    pip install roadmap-cli

Verify the installation:

.. code-block:: bash

    roadmap --version

You should see the version number (e.g., ``roadmap-cli, version 0.7.0``).

OS-Specific Installation
========================

macOS
-----

Using Homebrew (if available):

.. code-block:: bash

    brew install roadmap-cli

Or via pip:

.. code-block:: bash

    python3 -m pip install --upgrade pip
    pip3 install roadmap-cli

Windows
-------

Using pip in Command Prompt or PowerShell:

.. code-block:: bash

    python -m pip install --upgrade pip
    pip install roadmap-cli

If you get a "command not found" error, make sure Python is in your PATH.
See `Python Setup on Windows <https://docs.python.org/3/using/windows.html>`_.

Linux
-----

Using pip:

.. code-block:: bash

    python3 -m pip install --upgrade pip
    pip3 install roadmap-cli

Or using your system package manager (if available):

.. code-block:: bash

    # Ubuntu/Debian
    sudo apt-get install python3-pip
    pip3 install roadmap-cli

    # Fedora/RHEL
    sudo dnf install python3-pip
    pip3 install roadmap-cli

Docker Installation
===================

If you prefer containerized deployment:

.. code-block:: bash

    docker run -it roadmap-cli/roadmap:latest roadmap --version

See the contributing guide for building Docker images from source.

Development Installation (From Source)
======================================

For contributing or testing the latest development version:

.. code-block:: bash

    git clone https://github.com/roadmap-cli/roadmap.git
    cd roadmap
    poetry install

Then run roadmap via Poetry:

.. code-block:: bash

    poetry run roadmap --version

This installs all development dependencies including:

- pytest (testing)
- ruff (linting)
- mypy (type checking)
- sphinx (documentation)

Upgrading from Previous Versions
=================================

To upgrade an existing installation to the latest version:

.. code-block:: bash

    pip install --upgrade roadmap-cli

Or with Poetry (development):

.. code-block:: bash

    poetry update

Verifying Your Installation
============================

Run the health check to verify everything is working:

.. code-block:: bash

    roadmap health

You should see a status report confirming system health.

Troubleshooting Installation
=============================

"command not found: roadmap"
----------------------------

If the roadmap command is not found after installation:

1. **Check Python location:**

   .. code-block:: bash

       python -m roadmap --version

2. **Verify pip installation:**

   .. code-block:: bash

       pip list | grep roadmap-cli

3. **Add Python to PATH** (if needed for your OS)

4. **Try user installation:**

   .. code-block:: bash

       pip install --user roadmap-cli

"ModuleNotFoundError: No module named 'roadmap'"
-------------------------------------------------

This usually means the package wasn't installed correctly:

.. code-block:: bash

    # Reinstall
    pip uninstall roadmap-cli -y
    pip install roadmap-cli

Permission Denied
-----------------

If you get permission errors on Linux/macOS:

.. code-block:: bash

    # Use --user flag
    pip install --user roadmap-cli

    # Or use sudo (less recommended)
    sudo pip install roadmap-cli

Python Version Mismatch
-----------------------

If you have multiple Python versions installed:

.. code-block:: bash

    python3 -m pip install roadmap-cli
    python3 -m roadmap --version

Getting Help
============

- View the :doc:`quickstart` guide
- Check the :doc:`configuration` documentation
- See :doc:`../troubleshooting` for more help
- Visit `GitHub Issues <https://github.com/roadmap-cli/roadmap/issues>`_
