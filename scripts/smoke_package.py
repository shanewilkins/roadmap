#!/usr/bin/env python3
"""Install a built Roadmap artifact and exercise its released-user path."""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import tempfile
import time
from pathlib import Path


def _run(command: list[str], *, cwd: Path | None = None, env: dict[str, str]) -> None:
    """Run one smoke-test command and fail immediately on an error."""
    print(f"+ {' '.join(command)}", flush=True)
    subprocess.run(command, cwd=cwd, env=env, check=True)


def _installable(source: str) -> str:
    """Return a local artifact's resolved path, or a pip requirement unchanged."""
    candidate = Path(source)
    if candidate.is_file():
        return str(candidate.resolve(strict=True))
    return source


def _check_inspection(roadmap: Path, workspace: Path, env: dict[str, str]) -> None:
    """Prove new adapter modules and machine output ship in the wheel."""
    prefix = [str(roadmap), "--workspace", str(workspace / ".roadmap")]
    created = subprocess.run(
        [
            *prefix,
            "project",
            "create",
            "--title",
            "[red]Literal project[/red]",
            "--owner",
            "alice",
            "--priority",
            "high",
            "--print-id",
        ],
        cwd=workspace,
        env=env,
        check=True,
        capture_output=True,
        text=True,
    )
    identity = created.stdout.strip()
    assert identity and "\n" not in identity, created.stdout
    inspected = subprocess.run(
        [*prefix, "project", "view", identity, "--format", "json"],
        cwd=workspace,
        env=env,
        check=True,
        capture_output=True,
        text=True,
    )
    payload = json.loads(inspected.stdout)
    assert payload["schema_version"] == 1 and payload["kind"] == "roadmap.project"
    assert payload["record"]["project"]["id"] == identity
    assert payload["record"]["project"]["name"] == "[red]Literal project[/red]"
    assert payload["record"]["project"]["owner"] == "alice"
    assert payload["record"]["project"]["priority"] == "high"
    print(
        "Installed workspace selection, ID-only creation and JSON inspection passed.",
        flush=True,
    )


def _install_with_retries(
    environment_python: Path,
    installable: str,
    *,
    retries: int,
    retry_delay: float,
    env: dict[str, str],
) -> None:
    """Install the target, retrying only to absorb index propagation lag."""
    command = [str(environment_python), "-m", "pip", "install", installable]
    for attempt in range(1, retries + 2):
        print(f"+ {' '.join(command)} (attempt {attempt})", flush=True)
        result = subprocess.run(command, env=env, check=False)
        if result.returncode == 0:
            return
        if attempt == retries + 1:
            raise SystemExit(result.returncode)
        time.sleep(retry_delay)


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


def smoke_test(
    artifact: str,
    python: Path,
    *,
    install_retries: int = 0,
    install_retry_delay: float = 15.0,
) -> None:
    """Install and exercise a wheel, source distribution, or PyPI spec."""
    installable = _installable(artifact)
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

        _install_with_retries(
            environment_python,
            installable,
            retries=install_retries,
            retry_delay=install_retry_delay,
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
        _check_inspection(roadmap, workspace, clean_environment)


def main() -> None:
    """Parse arguments and run the artifact smoke test."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "artifact",
        help="Wheel/sdist path to install, or a pip requirement such as "
        "'roadmap-cli==0.3.0'",
    )
    parser.add_argument(
        "--python",
        type=Path,
        default=Path(sys.executable),
        help="Python interpreter used to create the clean environment",
    )
    parser.add_argument(
        "--install-retries",
        type=int,
        default=0,
        help="Retry the install this many extra times (for index propagation lag)",
    )
    parser.add_argument(
        "--install-retry-delay",
        type=float,
        default=15.0,
        help="Seconds to wait between install retries",
    )
    arguments = parser.parse_args()
    smoke_test(
        arguments.artifact,
        arguments.python,
        install_retries=arguments.install_retries,
        install_retry_delay=arguments.install_retry_delay,
    )


if __name__ == "__main__":
    main()
