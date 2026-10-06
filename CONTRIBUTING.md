# Contributing to Roadmap CLI

Thanks for your interest in contributing.
We welcome bug fixes, documentation improvements, tests, and new features.

## Before You Start

- Search existing issues and pull requests before opening new work.
- Keep changes focused and small when possible.
- Add or update tests for behavioral changes.
- Keep documentation in sync with code changes.

## Development Setup

1. Clone the repository.
2. Install dependencies with uv.

```bash
uv sync --all-extras --locked
```

3. Run the CLI help to verify setup.

```bash
uv run roadmap --help
```

## Local Quality Checks

Run these before opening a pull request.

```bash
uv run --locked --extra dev ruff format --config config/ruff.toml roadmap tests
uv run --locked --extra dev ruff check --config config/ruff.toml roadmap tests
uv run --locked --extra dev python tests/policy/architecture_checker.py
uv run --locked --extra dev ty check
uv run --locked --extra dev radon cc roadmap --exclude '*/migrations/*' --total-average --show-complexity --min D
uv run --locked --extra dev xenon --exclude '*/migrations/*' --max-absolute B --max-modules B --max-average A roadmap
uv run --locked --extra dev pytest -q
```

CI also validates workflow semantics with actionlint 1.7.12 and exercises the
full suite on every supported Python minor. Package compatibility is verified
from one exact wheel/source-distribution build on Ubuntu 24.04 x64 and macOS 15
ARM64.

ty is the sole type checker and targets the minimum supported Python version,
3.12. Development dependencies have one declaration in the `dev` extra.
Pre-commit runs architecture enforcement, Ruff, Xenon, and ty; the descriptive
Radon report stays in CI. CI retains JSON/XML coverage reports for 14 days.
Release tags run the same full quality/test/package workflow before building
the distributions for publication.

Optional security check.

```bash
uv run --locked --extra dev bandit -c config/bandit.toml -r roadmap --severity-level=high
```

CI also audits the complete locked runtime/development dependency set with a
pinned, isolated pip-audit tool. To reproduce it locally:

```bash
uv export --locked --all-extras --all-groups --no-emit-project --no-header --output-file /tmp/roadmap-audit-requirements.txt
uv tool run --from pip-audit==2.10.1 pip-audit --require-hashes --no-deps --disable-pip --strict --requirement /tmp/roadmap-audit-requirements.txt
```

Known vulnerabilities or dependency-collection failures fail the quality job.
The audit uses the lockfile's versions and hashes and does not automatically
upgrade packages. Dependabot alerts continue to provide monitoring between CI
runs.

## Pull Request Guidelines

- Write clear commit messages describing intent.
- Include a concise summary of what changed and why.
- Link related issues when applicable.
- Mention any follow-up work that remains.
- Ensure CI passes before requesting review.

## Coding Guidelines

- Follow `architecture.toml`; do not add or broaden an
  `architecture-baseline.toml` exception to bypass a dependency violation.
- Keep functions readable and avoid unnecessary complexity.
- Prefer explicit types for new code.
- Preserve backward compatibility unless the change is intentionally breaking.

## Testing Guidelines

- Add unit tests for new logic.
- Add integration tests when behavior crosses layers.
- Update fixtures only when needed and keep them minimal.
- Do not reduce coverage for modified areas.

## Security

If your change touches auth, token handling, file operations, or network flows, include security considerations in the pull request description.
For vulnerability reports, do not open a public issue.
See SECURITY.md for the disclosure process.

## Release Notes

For user-visible changes, update CHANGELOG.md under Unreleased.
