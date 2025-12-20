================================================================================
Development Workflow
================================================================================

Guidelines for developing features, fixing bugs, and contributing to Roadmap CLI.

Code Style & Standards
======================

**Python Standards**:

- Follow PEP 8 with ruff enforced rules
- Line length: 88 characters
- Type hints required for all functions
- Google-style docstrings
- Import order: stdlib, third-party, local

**Ruff Configuration** (automatic):

.. code-block:: bash

    # Lint
    poetry run ruff check roadmap/

    # Format
    poetry run ruff format roadmap/

    # Both check and format in one
    poetry run ruff check --fix roadmap/

**Type Hints** (required):

All functions must have complete type hints:

.. code-block:: python

    def create_issue(
        project_name: str,
        title: str,
        priority: str = "medium"
    ) -> Issue:
        """Create a new issue.

        Args:
            project_name: Name of the containing project
            title: Issue title
            priority: Priority level (default: medium)

        Returns:
            Created Issue object

        Raises:
            ProjectNotFoundError: If project doesn't exist
            ValidationError: If input is invalid
        """
        pass

**Docstrings** (Google style):

All public functions and classes need docstrings:

.. code-block:: python

    class IssueRepository:
        """Manages issue persistence operations.

        Provides methods for CRUD operations on issues including
        creation, retrieval, updates, and deletion with proper
        validation.

        Attributes:
            storage: The persistence storage backend
            validator: Issue validator instance
        """

        def get_issue(self, issue_id: str) -> Optional[Issue]:
            """Retrieve an issue by ID.

            Args:
                issue_id: Unique issue identifier

            Returns:
                Issue object if found, None otherwise

            Raises:
                InvalidIDError: If issue_id format is invalid
            """

Development Workflow
====================

**Step 1: Create a feature branch**

.. code-block:: bash

    git checkout -b feature/your-feature-name
    # or: git checkout -b fix/bug-description
    # or: git checkout -b docs/documentation-update

Use one of these prefixes:

- `feature/` - New features
- `fix/` - Bug fixes
- `refactor/` - Code refactoring
- `docs/` - Documentation
- `test/` - Test improvements
- `perf/` - Performance improvements

**Step 2: Make your changes**

.. code-block:: bash

    # Edit files, add features, fix bugs
    # Add/remove/update tests as needed
    vim roadmap/adapters/cli/issues.py
    vim tests/unit/presentation/test_issue.py

**Step 3: Run tests locally**

.. code-block:: bash

    # Run all tests
    poetry run pytest

    # Run specific test file
    poetry run pytest tests/unit/presentation/test_issue.py -v

    # Run with coverage
    poetry run pytest --cov=roadmap --cov-report=html

    # Run only failing tests
    poetry run pytest --lf

**Step 4: Format and lint**

.. code-block:: bash

    # Format code
    poetry run ruff format roadmap/

    # Check linting
    poetry run ruff check roadmap/

    # Type check
    poetry run mypy roadmap/

**Step 5: Commit with clear messages**

.. code-block:: bash

    git add roadmap/ tests/

    # Commit format:
    git commit -m "Add feature: [feature description]"
    git commit -m "Fix: [bug description]"
    git commit -m "Docs: [documentation update]"

Commit message format:

.. code-block:: text

    Type: Brief description (50 chars max)

    Optional longer explanation explaining:
    - What changed and why
    - Any breaking changes
    - Related GitHub issues

    Closes #123  # Reference issue numbers

**Step 6: Push and create pull request**

.. code-block:: bash

    git push origin feature/your-feature-name

Then create a pull request on GitHub with:

- Clear title
- Description of changes
- Reference to related issues
- Screenshots (if UI changes)

Code Organization
=================

**Package Structure**:

.. code-block:: text

    roadmap/
    ├── adapters/              # External integrations
    │   ├── cli/              # Click CLI commands
    │   ├── persistence/      # Data storage
    │   └── github/           # GitHub API
    ├── core/                 # Domain layer
    │   ├── domain/          # Data models
    │   ├── interfaces/      # Abstractions
    │   └── services/        # Business logic
    ├── infrastructure/       # Support services
    │   ├── github/          # GitHub operations
    │   └── logging/         # Observability
    ├── shared/              # Utilities
    │   ├── formatters/     # Output formatting
    │   └── validation/     # Input validation
    └── settings.py          # Configuration

**When adding features**:

1. Define models in `core/domain/`
2. Add business logic in `core/services/`
3. Add CLI command in `adapters/cli/`
4. Add tests in corresponding `tests/` location
5. Update documentation in `docs/`

Adding New Commands
===================

**Example: Add a new command**

1. Create command file in `roadmap/adapters/cli/commands.py`:

.. code-block:: python

    @click.command("new-command")
    @click.argument("name")
    @click.option("--project", help="Project name")
    def new_command(name: str, project: Optional[str]) -> None:
        """Execute new command.

        Args:
            name: Name parameter
            project: Optional project filter
        """
        pass

2. Register in CLI group:

.. code-block:: python

    @click.group()
    def cli():
        pass

    cli.add_command(new_command)

3. Add unit test in `tests/unit/presentation/test_new_command.py`

4. Add integration test in `tests/integration/test_new_command.py`

5. Document in user guide

Modifying Data Models
======================

**When changing Project, Milestone, or Issue models**:

1. Update dataclass in `core/domain/models.py`
2. Update validators in `core/services/validators.py`
3. Update serialization in `adapters/persistence/`
4. Add migration if needed
5. Update tests
6. Update documentation

Performance Considerations
==========================

When adding features, consider:

- **Query efficiency**: Minimize database calls
- **Memory usage**: Avoid loading unnecessary data
- **File I/O**: Batch operations when possible
- **API calls**: Cache GitHub responses

Profile slow operations:

.. code-block:: bash

    poetry run python -m cProfile -s cumtime roadmap/cli.py project list

Testing During Development
===========================

**Unit tests** (fast, isolated):

.. code-block:: bash

    poetry run pytest tests/unit/ -v

**Integration tests** (feature flows):

.. code-block:: bash

    poetry run pytest tests/integration/ -v

**Security tests** (input validation):

.. code-block:: bash

    poetry run pytest tests/security/ -v

**Watch mode** (re-run on changes):

.. code-block:: bash

    poetry run pytest-watch

**Coverage report**:

.. code-block:: bash

    poetry run pytest --cov=roadmap --cov-report=html
    # Open htmlcov/index.html in browser

Debugging
=========

**Print debugging**:

.. code-block:: python

    import logging
    logger = logging.getLogger(__name__)
    logger.debug(f"Debug: {variable}")

**Breakpoint debugging**:

.. code-block:: python

    breakpoint()  # Debugger pauses here
    # Use pdb commands: n, s, c, p variable, l

**Using IDE debugger**:

Set breakpoint in VS Code, press F5 to debug.

Common Development Tasks
========================

**Update dependencies**:

.. code-block:: bash

    poetry add package-name          # Add new
    poetry update                    # Update all
    poetry add --group dev package   # Dev dependency

**Generate API docs**:

.. code-block:: bash

    poetry run sphinx-apidoc -o docs/sphinx/source/api roadmap

**Build documentation locally**:

.. code-block:: bash

    poetry run sphinx-build -b html docs/sphinx/source docs/sphinx/build
    open docs/sphinx/build/html/index.html

**Run performance profiler**:

.. code-block:: bash

    poetry run python scripts/baseline_profiler.py

**Check code quality**:

.. code-block:: bash

    poetry run ruff check roadmap/
    poetry run mypy roadmap/
    poetry run pylint roadmap/

Getting Help
============

- Check :doc:`setup` for environment setup
- Read :doc:`testing` for test guidelines
- Review :doc:`../architecture/overview` for architecture
- Look at existing code for patterns
- Ask in GitHub discussions

Best Practices
==============

1. **Write tests first** - TDD approach preferred
2. **Keep commits small** - One feature per commit
3. **Write clear messages** - Future you will thank you
4. **Update docs** - Documentation is code
5. **Review others' code** - Learning opportunity
6. **Ask questions** - No question is too small

See Also
========

- :doc:`setup` - Development environment setup
- :doc:`testing` - Testing guidelines and examples
- :doc:`../architecture/overview` - Architecture overview
