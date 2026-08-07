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
uv run ruff format --config config/ruff.toml roadmap tests
uv run ruff check --config config/ruff.toml roadmap tests
uv run pyright
uv run pytest -q
```

Optional full checks.

```bash
uv run bandit -r roadmap --severity-level=high
bash scripts/lint-imports-wrapper.sh
```

## Pull Request Guidelines

- Write clear commit messages describing intent.
- Include a concise summary of what changed and why.
- Link related issues when applicable.
- Mention any follow-up work that remains.
- Ensure CI passes before requesting review.

## Coding Guidelines

- Follow existing architecture boundaries.
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
