================================================================================
Developer Setup Guide
================================================================================

Complete guide to setting up your development environment for contributing to Roadmap CLI.

System Prerequisites
====================

**Required**:

- Python 3.10 or higher
- Poetry 1.7.0+
- Git 2.20+
- pip

**Optional**:

- Docker (for containerized development)
- Docker Compose (for multi-service testing)
- VS Code (recommended editor with Python extension)

**Verification**:

.. code-block:: bash

    python3 --version          # Should be 3.10+
    poetry --version           # Should be 1.7.0+
    git --version              # Should be 2.20+
    pip --version              # Should be 24.0+

Installation & Setup
====================

**Step 1: Clone the repository**

.. code-block:: bash

    git clone https://github.com/roadmap-cli/roadmap.git
    cd roadmap

**Step 2: Install dependencies with Poetry**

.. code-block:: bash

    poetry install

This installs:

- Core dependencies (Click, PyGithub, Pydantic, etc.)
- Development dependencies (pytest, ruff, mypy)
- Documentation dependencies (Sphinx, Napoleon)
- Profiling tools

**Step 3: Activate virtual environment**

.. code-block:: bash

    poetry shell

Or use Poetry with commands:

.. code-block:: bash

    poetry run roadmap --help

**Step 4: Verify installation**

.. code-block:: bash

    poetry run pytest -v

All 2500+ tests should pass with no errors.

Development Environment Structure
==================================

Your development environment will have this structure:

.. code-block:: text

    roadmap/
    ├── roadmap/              # Main package
    │   ├── adapters/         # CLI and persistence adapters
    │   ├── core/             # Domain models and services
    │   ├── infrastructure/   # GitHub, logging, etc.
    │   ├── shared/           # Utilities and shared code
    │   └── __init__.py       # Package initialization
    ├── tests/                # Test suite (2500+ tests)
    ├── docs/                 # Documentation (Sphinx)
    ├── scripts/              # Development scripts
    ├── pyproject.toml        # Poetry configuration
    ├── pytest.ini            # Pytest configuration
    ├── pyrightconfig.json    # Pyright type checking
    └── README.md             # Project README

Poetry Configuration
====================

The `pyproject.toml` file defines:

- **Name**: roadmap-cli
- **Version**: 0.7.0 (see version in pyproject.toml)
- **Python**: 3.10+
- **Entry Point**: `roadmap` command

Key dependencies:

.. code-block:: toml

    [tool.poetry.dependencies]
    python = "^3.10"
    click = "^8.1"
    pydantic = "^2.0"
    pyyaml = "^6.0"
    pygithub = "^1.58"

Development tools:

.. code-block:: toml

    [tool.poetry.group.dev.dependencies]
    pytest = "^7.0"
    pytest-cov = "^4.0"
    ruff = "^0.2.0"
    mypy = "^1.0"
    sphinx = "^7.0"

Pre-commit Hooks
================

The project uses pre-commit hooks for quality checks:

.. code-block:: bash

    # Install hooks
    poetry run pre-commit install

    # Run checks manually
    poetry run pre-commit run --all-files

Hooks check:

- Python syntax errors
- YAML/JSON formatting
- Trailing whitespace
- Large file detection
- Ruff linting
- Type checking (mypy)
- Code style (Pyright)
- Docstring validation

IDE Setup
=========

**VS Code Recommended**:

Install extensions:

- Python (Microsoft)
- Pylance (Microsoft) - Type checking and intellisense
- Ruff (Charliermarsh) - Linting
- Python Docstring Generator (Nils Werner)

Settings in `.vscode/settings.json`:

.. code-block:: json

    {
        "python.defaultInterpreterPath": "${workspaceFolder}/.venv/bin/python",
        "python.linting.enabled": true,
        "python.linting.pylintEnabled": false,
        "python.linting.ruffEnabled": true,
        "[python]": {
            "editor.formatOnSave": true,
            "editor.defaultFormatter": "charliermarsh.ruff"
        },
        "python.testing.pytestEnabled": true,
        "python.testing.pytestArgs": ["tests"]
    }

**PyCharm Setup**:

1. Open project in PyCharm
2. Configure interpreter: Settings → Python Interpreter → Add → Existing Environment
3. Point to Poetry venv: `~/.cache/pypoetry/virtualenvs/<project-name-hash>/bin/python`
4. Enable pytest: Settings → Tools → Python Integrated Tools → pytest

Configuration Files
====================

**pyproject.toml**

Main Poetry configuration. Update version here for releases.

**pytest.ini**

Pytest configuration including markers and test paths.

**pyrightconfig.json**

Pyright type checker configuration. Used for static type analysis.

**pyproject.toml [tool.ruff]**

Ruff linter rules and exclusions.

Docker Development
==================

Optional: Use Docker for isolated development environment.

**Build development image**:

.. code-block:: bash

    docker build --target development -t roadmap-dev .

**Run in container**:

.. code-block:: bash

    docker run -it -v $(pwd):/workspace roadmap-dev

**Using Docker Compose**:

.. code-block:: bash

    docker-compose -f docker-compose.dev.yml up

Running the Application
=======================

**From source**:

.. code-block:: bash

    poetry run roadmap --help

**After development install**:

.. code-block:: bash

    # Within Poetry shell
    roadmap --help
    roadmap project list

**Test a specific command**:

.. code-block:: bash

    poetry run roadmap project create "Test Project"
    poetry run roadmap project list
    poetry run roadmap project view "Test Project"

Troubleshooting Setup Issues
=============================

**Poetry not found**

Install Poetry:

.. code-block:: bash

    curl -sSL https://install.python-poetry.org | python3 -

Add to PATH (if needed):

.. code-block:: bash

    export PATH="$HOME/.local/bin:$PATH"

**Wrong Python version**

Check Python version:

.. code-block:: bash

    python3 --version

Install Python 3.10+ using:

- macOS: `brew install python@3.10`
- Ubuntu: `sudo apt-get install python3.10`
- Windows: Download from python.org

**Virtual environment conflicts**

Clear cache and reinstall:

.. code-block:: bash

    poetry cache clear . --all
    poetry install --no-cache

**Pre-commit hook failures**

Manually run hooks:

.. code-block:: bash

    poetry run pre-commit run --all-files

**Tests failing**

Verify clean state:

.. code-block:: bash

    poetry run pytest --tb=short
    poetry run pytest -v tests/unit/  # Run unit tests only

Next Steps
==========

Your development environment is ready! Next:

1. Read :doc:`development` - Development workflow
2. Read :doc:`testing` - Testing guidelines
3. Check out the issue backlog on GitHub
4. Join the contributor community

Quick Commands Reference
========================

.. code-block:: bash

    # Install and activate
    poetry install
    poetry shell

    # Run application
    roadmap project list

    # Run tests
    poetry run pytest                 # All tests
    poetry run pytest tests/unit/     # Unit tests only
    poetry run pytest -k test_name    # Specific test

    # Code quality
    poetry run ruff check .           # Lint
    poetry run ruff format .          # Format
    poetry run mypy roadmap/          # Type check

    # Documentation
    poetry run sphinx-build -b html docs/sphinx/source docs/sphinx/build

    # Profiling
    poetry run python scripts/baseline_profiler.py

See Also
========

- :doc:`development` - Development workflow and patterns
- :doc:`testing` - Testing guidelines and examples
- :doc:`../architecture/overview` - Architecture overview
- GitHub Issues - Contribution ideas
