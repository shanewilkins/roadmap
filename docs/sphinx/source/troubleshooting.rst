================================================================================
Troubleshooting
================================================================================

Solutions to common problems.

.. note::

   This is a stub. Complete implementation coming in v.0.7.0.

Installation Issues
===================

Command not found
-----------------

If you get "command not found: roadmap" after installation:

.. code-block:: bash

    # Try using Python module invocation
    python -m roadmap --version

    # Or install to user bin
    pip install --user roadmap-cli

ImportError
-----------

If you get import errors when installing from source:

.. code-block:: bash

    # Make sure you're using Poetry
    poetry install
    poetry run roadmap --version

Runtime Issues
==============

Data Corruption
---------------

If your roadmap data appears corrupted:

1. Stop all roadmap processes
2. Backup ``.roadmap/`` directory
3. Run recovery: ``roadmap health check``
4. Contact support if issue persists

Permission Denied
-----------------

If you get permission errors:

.. code-block:: bash

    # Check directory permissions
    ls -la .roadmap/

    # Fix if needed
    chmod -R u+rw .roadmap/

GitHub Sync Issues
==================

Authentication Failures
-----------------------

If GitHub sync fails with authentication errors:

1. Verify your GitHub token
2. Check token permissions
3. Ensure token is not expired
4. See :doc:`user-guide/workflows` for setup

Common Errors
=============

.. code-block:: text

    Error: "File is locked"
    Solution: Another roadmap process is running. Wait or kill the process.

.. code-block:: text

    Error: "Milestone not found"
    Solution: Check milestone name and project. Use 'roadmap milestone list'

Getting Help
============

- Check the :doc:`user-guide/faq` for FAQs
- Search `GitHub Issues <https://github.com/roadmap-cli/roadmap/issues>`_
- Review the :doc:`user-guide/commands` for command syntax
