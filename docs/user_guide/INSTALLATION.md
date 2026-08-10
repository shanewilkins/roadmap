# Installation Guide

Roadmap CLI supports Python 3.13 and 3.14 on macOS and Linux. Windows is not
currently a supported runtime because parts of the local locking implementation
use POSIX APIs.

The distribution name is `roadmap-cli`; the command it installs is `roadmap`.
Do not install the unrelated `roadmap` distribution from PyPI.

## Install for regular use

An isolated tool environment avoids dependency conflicts with application
projects.

### uv tool (recommended)

```bash
uv tool install roadmap-cli
roadmap --version
roadmap --help
```

Upgrade or remove it with:

```bash
uv tool upgrade roadmap-cli
uv tool uninstall roadmap-cli
```

### pipx

```bash
pipx install roadmap-cli
roadmap --version
```

### pip in a virtual environment

```bash
python3.13 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install roadmap-cli
roadmap --version
```

Only runtime libraries are installed by these commands. Test, lint, type-check,
and documentation tools are development dependencies and are not part of a
normal user installation.

## Install from source for development

Install [uv](https://docs.astral.sh/uv/), then use the locked development
environment:

```bash
git clone https://github.com/shanewilkins/roadmap.git
cd roadmap
uv sync --all-extras --locked
uv run roadmap --version
uv run roadmap --help
```

Run development commands through `uv run` so they use the repository's managed
environment:

```bash
uv run pytest -n 0 tests/integration/cli/test_cli_root_commands.py
uv run ruff check --config config/ruff.toml roadmap tests
```

## Install a locally built artifact

Build both release artifacts outside the source package and install the wheel in
a fresh environment:

```bash
uv build
python3.13 -m venv /tmp/roadmap-package-check
/tmp/roadmap-package-check/bin/python -m pip install dist/roadmap_cli-*.whl
/tmp/roadmap-package-check/bin/roadmap --help
/tmp/roadmap-package-check/bin/roadmap --version
```

The repository's package smoke script performs a stronger check against either a
wheel or source distribution. It installs the artifact in a temporary virtual
environment, removes source-tree import overrides, and exercises help, version,
initialization, and an issue lifecycle:

```bash
python scripts/smoke_package.py dist/roadmap_cli-*.whl
python scripts/smoke_package.py dist/roadmap_cli-*.tar.gz
```

## Container installation

Build the project before the final image so the runtime image receives the same
wheel that is tested and released:

```dockerfile
FROM python:3.13-slim AS builder
WORKDIR /src
COPY . .
RUN python -m pip install build && python -m build

FROM python:3.13-slim
COPY --from=builder /src/dist/roadmap_cli-*.whl /tmp/
RUN python -m pip install --no-cache-dir /tmp/roadmap_cli-*.whl \
    && rm /tmp/roadmap_cli-*.whl
ENTRYPOINT ["roadmap"]
CMD ["--help"]
```

## Troubleshooting

### `roadmap` imports `roadmap.py` or reports that `roadmap` is not a package

An unrelated distribution named `roadmap` may be installed in the environment.
Inspect and remove it, then reinstall this project by its distribution name:

```bash
python -m pip show roadmap
python -m pip uninstall roadmap
python -m pip install --force-reinstall roadmap-cli
```

### The command is not found

For `uv tool`, ensure the tool directory is on `PATH`:

```bash
uv tool update-shell
```

For a virtual environment, activate it before running `roadmap`.

### Verify which package and version are running

```bash
roadmap --version
python -c 'import roadmap; print(roadmap.__file__, roadmap.__version__)'
python -m pip show roadmap-cli
```

If these locations or versions disagree, create a fresh isolated environment and
reinstall `roadmap-cli`.
