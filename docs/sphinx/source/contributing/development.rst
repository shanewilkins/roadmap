================================================================================
Development Workflow
================================================================================

Guidelines for developing and contributing to Roadmap CLI.

.. note::

   This is a stub. Complete implementation coming in v.0.7.0.

Code Style
==========

We follow PEP 8 with these guidelines:

- Line length: 88 characters (Black-compatible)
- Type hints required for all functions
- Google-style docstrings
- Ruff for linting (enforced by CI)

Running Linters
===============

.. code-block:: bash

    # Run ruff (linter and formatter)
    poetry run ruff check roadmap
    poetry run ruff format roadmap

    # Run mypy (type checking)
    poetry run mypy roadmap

Type Hints
==========

All functions should have complete type hints:

.. code-block:: python

    def process_issue(issue_id: str, status: str) -> Issue:
        """Process an issue.

        Args:
            issue_id: The issue identifier
            status: New status

        Returns:
            Updated Issue object
        """
        pass

Git Workflow
============

1. Create a feature branch
2. Make your changes
3. Run tests and linters
4. Commit with clear messages
5. Push and create a pull request

See Also
========

- :doc:`setup` - Development setup
- :doc:`testing` - Testing guidelines
