# Roadmap Scripts

Utility scripts and installation formulas for development and distribution.

## Scripts

### `checkpoint_journey.py`
Runs the cumulative installed-artifact journey against an isolated workspace.

```bash
uv run --locked python scripts/checkpoint_journey.py --help
```

### `smoke_package.py`
Verifies the built wheel or source distribution in an isolated environment.

```bash
uv run --locked python scripts/smoke_package.py --help
```

### `analyze_coverage_hotspots.py`
Analyzes `coverage.json` produced by `pytest-cov` and prints the least-covered files.

```bash
uv run python scripts/analyze_coverage_hotspots.py --coverage-file coverage.json --top 20
```

### `requirements_journey.py`
Verifies optional adoption, capture, acceptance, criterion evidence, stale manual
edits and projection rebuild using an installed candidate in an isolated workspace.
Pass `--previous-roadmap-command` to additionally prove published 0.3.1 refuses
the explicitly upgraded workspace. CI runs the candidate journey in every package job.

```bash
uv run --locked python scripts/requirements_journey.py --help
```

All scripts are development utilities and are not part of the production package.
