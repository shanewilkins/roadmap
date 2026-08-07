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

Writing Unit Tests
===================

**Example: Testing a service function**

.. code-block:: python

    # tests/unit/core/services/test_issue_service.py
    import pytest
    from roadmap.core.services import IssueService
    from roadmap.core.domain import Issue, Project

    @pytest.fixture
    def project():
        """Create a test project."""
        return Project(name="Test Project")

    @pytest.fixture
    def service(project):
        """Create an issue service with test project."""
        return IssueService(project)

    def test_create_issue(service):
        """Test creating a new issue."""
        issue = service.create_issue(
            title="Test Issue",
            priority="high"
        )

        assert issue.title == "Test Issue"
        assert issue.priority == "high"
        assert issue.status == "open"

    def test_create_issue_invalid_priority(service):
        """Test that invalid priority raises error."""
        with pytest.raises(ValidationError) as exc_info:
            service.create_issue(
                title="Test",
                priority="invalid"
            )

        assert "priority" in str(exc_info.value).lower()

Best Practices
==============

1. **Descriptive test names**

   ✅ Good: `test_create_issue_with_high_priority_sets_priority`

   ❌ Bad: `test_create`

2. **Arrange-Act-Assert pattern**

   .. code-block:: python

       def test_issue_status_update():
           # Arrange
           issue = Issue("Test", status="open")

           # Act
           issue.update_status("in-progress")

           # Assert
           assert issue.status == "in-progress"

3. **Test the public API, not implementation**

4. **Keep tests independent** - Each test should run in any order

5. **Use fixtures for common setup**

Running Tests with Coverage
============================

**View coverage report**:

.. code-block:: bash

    poetry run pytest --cov=roadmap --cov-report=html
    open htmlcov/index.html

**Current coverage**: 2506 tests, 92% code coverage

See Also
========

- :doc:`setup` - Development setup
- :doc:`development` - Development workflow
- pytest documentation: https://docs.pytest.org
