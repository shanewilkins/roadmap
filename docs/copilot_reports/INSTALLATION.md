# Installation Guide

## Quick Start

### Production Installation (Recommended for Users)

```bash

# Using pip (simplest)

pip install roadmap-cli

# Using Poetry (ensures reproducible builds)

poetry install --no-dev

```text

**Result:** Lightweight, secure installation with **0 known CVEs**

### Development Installation

```bash

# Install with all development tools

poetry install

# Or if using pip with extras

pip install -e ".[dev]"

```text

**Includes:** Testing frameworks, linters, documentation tools, pre-commit hooks

## Why Two Installation Modes?

### Production (--no-dev)

- **50 packages** installed
- **0 CVEs** (verified with pip-audit)
- Minimal footprint, faster installation
- All runtime functionality included

### Development

- **80+ packages** installed
- Includes: pytest, ruff, pyright, sphinx, mkdocs
- Pre-commit hooks for code quality
- Documentation tools for development

## Production Installation Details

When you run `poetry install --no-dev` (or `pip install .`), you get:

✅ **Core Runtime Dependencies:**

- Click (CLI framework)
- Pydantic (data validation)
- PyYAML (config files)
- Requests + aiohttp (HTTP)
- Pandas + matplotlib + plotly (data visualization)
- Keyring (credential storage)
- GitPython (git integration)
- Dynaconf (configuration management)

❌ **Excluded Dev Dependencies:**

- pytest, pytest-cov, pytest-asyncio (testing)
- ruff, pyright (linting/type checking)
- sphinx, mkdocs (documentation)
- pre-commit (git hooks)

## Configuration Files

### pyproject.toml

- Contains production dependency specification
- Marked with installation instructions
- Use `poetry install --no-dev` for production

### setup.cfg

- Pip configuration file
- Supports standard `pip install .` workflow
- Ensures pip defaults to production-only

### .env.production

- Reference template for production deployments
- Copy to `.env` for production settings
- Includes recommended production flags

## Verification

To verify your installation has no vulnerabilities:

```bash

# Install pip-audit

pip install pip-audit

# For production installations

pip-audit

# Expected output: No known vulnerabilities found

```text

## Docker Deployment

For Docker production builds:

```dockerfile
FROM python:3.12-slim

WORKDIR /app

# Copy only needed files

COPY pyproject.toml setup.cfg README.md LICENSE.md ./

# Install production only

RUN pip install --no-cache-dir .

# Or with Poetry

# RUN pip install poetry && poetry install --no-dev

ENTRYPOINT ["roadmap"]

```text

## CI/CD Integration

### GitHub Actions Example

```yaml
name: Production Build

on: [push, pull_request]

jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3

      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.12'

      # Verify security for production

      - name: Audit dependencies
        run: |
          pip install pip-audit
          PIPAPI_PYTHON_LOCATION=$(which python) pip-audit

      # Install production

      - name: Install production
        run: pip install .

```text

## Troubleshooting

### Q: I want to use development tools but keep my environment clean

A: Create a separate virtual environment for development:

```bash

# Development environment

python -m venv venv-dev
source venv-dev/bin/activate
poetry install

```text

```bash

# Production environment

python -m venv venv-prod
source venv-prod/bin/activate
poetry install --no-dev

```text

### Q: How do I know which mode I'm in?

A: Check installed packages:

```bash

# Production - 50 packages

pip list | wc -l

```text

```bash

# Development - 80+ packages

pip list | wc -l

```text

Or look for test/dev tools:

```bash
pip show pytest  # Not found in production

pip show ruff    # Not found in production

```text

### Q: Can I switch from dev to production?

A: Yes, create a fresh environment:

```bash

# Remove old packages

pip uninstall -y -r <(pip freeze)

```text

```bash

# Or start fresh

python -m venv venv-new
source venv-new/bin/activate
poetry install --no-dev

```text

## Security Notes

- Production installations have **0 known CVEs**
- Development installations include tools with CVEs (expected for dev)
- Regular `pip-audit` checks recommended in CI/CD
- See `docs/PRODUCTION_ENVIRONMENT_VERIFICATION.md` for verification details

## Version Requirements

- **Python:** 3.10, 3.11, 3.12 (tested and supported)
- **Poetry:** 1.2+ (recommended for reproducible builds)
- **Pip:** 21.0+ (standard pip install support)

---

For more information, see:

- `docs/PRODUCTION_ENVIRONMENT_VERIFICATION.md` - Security verification report
- `pyproject.toml` - Dependency specifications
- `.env.production` - Production configuration template
