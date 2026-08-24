#!/usr/bin/env python3
"""Install a built Roadmap artifact and exercise its released-user path."""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
import tempfile
from pathlib import Path


def _run(command: list[str], *, cwd: Path | None = None, env: dict[str, str]) -> None:
    """Run one smoke-test command and fail immediately on an error."""
    print(f"+ {' '.join(command)}", flush=True)
    subprocess.run(command, cwd=cwd, env=env, check=True)


def _environment_python(environment: Path) -> Path:
    """Return the virtual environment's Python executable."""
    scripts_directory = "Scripts" if os.name == "nt" else "bin"
    executable = "python.exe" if os.name == "nt" else "python"
    return environment / scripts_directory / executable


def _environment_command(environment: Path) -> Path:
    """Return the installed Roadmap console-script path."""
    scripts_directory = "Scripts" if os.name == "nt" else "bin"
    executable = "roadmap.exe" if os.name == "nt" else "roadmap"
    return environment / scripts_directory / executable


def smoke_test(artifact: Path, python: Path) -> None:
    """Install and exercise a wheel or source distribution in isolation."""
    artifact = artifact.resolve(strict=True)
    python = python.resolve(strict=True)

    clean_environment = os.environ.copy()
    clean_environment.pop("PYTHONHOME", None)
    clean_environment.pop("PYTHONPATH", None)
    clean_environment["PIP_DISABLE_PIP_VERSION_CHECK"] = "1"

    with tempfile.TemporaryDirectory(prefix="roadmap-package-smoke-") as directory:
        root = Path(directory)
        environment = root / "environment"
        workspace = root / "workspace"
        workspace.mkdir()

        _run([str(python), "-m", "venv", str(environment)], env=clean_environment)
        environment_python = _environment_python(environment)
        roadmap = _environment_command(environment)

        _run(
            [
                str(environment_python),
                "-m",
                "pip",
                "install",
                str(artifact),
            ],
            env=clean_environment,
        )
        _run(
            [
                str(environment_python),
                "-c",
                (
                    "from importlib.metadata import version; "
                    "from pathlib import Path; "
                    "import roadmap, sys; "
                    "assert roadmap.__version__ == version('roadmap-cli'); "
                    "assert Path(roadmap.__file__).resolve().is_relative_to("
                    "Path(sys.prefix).resolve()); "
                    "print(roadmap.__file__, roadmap.__version__)"
                ),
            ],
            cwd=workspace,
            env=clean_environment,
        )
        _run([str(roadmap), "--help"], cwd=workspace, env=clean_environment)
        _run([str(roadmap), "--version"], cwd=workspace, env=clean_environment)
        _run(
            [
                str(roadmap),
                "init",
                "--non-interactive",
                "--skip-project",
            ],
            cwd=workspace,
            env=clean_environment,
        )
        _run(
            [str(roadmap), "issue", "create", "--title", "Package smoke test"],
            cwd=workspace,
            env=clean_environment,
        )
        _run([str(roadmap), "issue", "list"], cwd=workspace, env=clean_environment)


def main() -> None:
    """Parse arguments and run the artifact smoke test."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("artifact", type=Path, help="Wheel or sdist to install")
    parser.add_argument(
        "--python",
        type=Path,
        default=Path(sys.executable),
        help="Python interpreter used to create the clean environment",
    )
    arguments = parser.parse_args()
    smoke_test(arguments.artifact, arguments.python)


if __name__ == "__main__":
    main()
