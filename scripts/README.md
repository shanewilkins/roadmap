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

All scripts are development utilities and are not part of the production package.
