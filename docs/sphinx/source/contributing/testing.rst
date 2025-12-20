================================================================================
Testing Guidelines
================================================================================

Testing strategy and best practices for Roadmap CLI.

.. note::

   This is a stub. Complete implementation coming in v.0.7.0.

Test Organization
=================

Tests are organized in the ``tests/`` directory:

.. code-block:: text

    tests/
    ├── unit/           # Unit tests
    ├── integration/    # Integration tests
    ├── e2e/           # End-to-end tests
    └── fixtures/      # Shared test fixtures

Running Tests
=============

Run all tests:

.. code-block:: bash

    poetry run pytest

Run specific test file:

.. code-block:: bash

    poetry run pytest tests/unit/test_issue.py

Run with coverage:

.. code-block:: bash

    poetry run pytest --cov=roadmap

Test Coverage
=============

We maintain 85%+ code coverage. View coverage reports:

.. code-block:: bash

    poetry run pytest --cov=roadmap --cov-report=html
    # Open htmlcov/index.html in browser

Test Fixtures
=============

Common fixtures are defined in ``tests/conftest.py``.

Writing Tests
=============

Use pytest conventions:

.. code-block:: python

    def test_create_issue():
        """Test issue creation."""
        issue = Issue("Test issue")
        assert issue.title == "Test issue"

See Also
========

- :doc:`setup` - Development setup
- :doc:`development` - Development workflow
