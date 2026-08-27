"""Executable contracts for the Phase 3 composition root."""

from __future__ import annotations

import ast
import subprocess
import sys
from pathlib import Path
from typing import Any

import click
from click.testing import CliRunner

from roadmap.bootstrap import BootstrapInputs, build_cli
from roadmap.bootstrap.core import create_core

ROOT = Path(__file__).resolve().parents[2]
CLI_ROOT = ROOT / "roadmap" / "adapters" / "inbound" / "cli"


def _imports(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    imports: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imports.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imports.add(node.module)
    return imports


def test_importing_cli_and_bootstrap_performs_no_boundary_initialization() -> None:
    """Imports remain free of workspace, keyring, network, and telemetry work."""
    program = r"""
import pathlib
import socket
import sys
from unittest.mock import patch

from click.testing import CliRunner

with (
    patch.object(pathlib.Path, "cwd", side_effect=AssertionError("cwd accessed")),
    patch.object(pathlib.Path, "exists", side_effect=AssertionError("filesystem accessed")),
    patch.object(socket, "create_connection", side_effect=AssertionError("network accessed")),
):
    import roadmap.adapters.inbound.cli
    import roadmap.bootstrap
    result = CliRunner().invoke(roadmap.bootstrap.cli, ["--help"])
    assert result.exit_code == 0, result.exception

for forbidden in (
    "roadmap.bootstrap.core",
    "roadmap.infrastructure.coordination.core",
    "roadmap.common.services.profiling",
    "roadmap.adapters.inbound.cli.issues",
    "roadmap.adapters.inbound.cli.projects",
    "roadmap.adapters.inbound.cli.sync",
):
    assert forbidden not in sys.modules, forbidden
"""
    result = subprocess.run(
        [sys.executable, "-c", program],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr


def test_help_and_version_do_not_construct_workspace() -> None:
    """Eager informational options stay independent of workspace state."""

    def forbidden(*_args: Any, **_kwargs: Any) -> Any:
        raise AssertionError("runtime initialization was attempted")

    inputs = BootstrapInputs(
        working_directory=forbidden,
        core_builder=forbidden,
        existing_core_builder=forbidden,
        console_factory=forbidden,
    )
    command = build_cli(inputs)
    runner = CliRunner()
    help_result = runner.invoke(command, ["--help"])
    version_result = runner.invoke(command, ["--version"])
    assert help_result.exit_code == 0, help_result.exception
    assert version_result.exit_code == 0, version_result.exception
    assert "0.2.0" in version_result.stdout


def test_bootstrap_construction_is_deterministic_from_explicit_inputs() -> None:
    """One explicit input set controls location and core construction."""
    calls: list[tuple[Any, ...]] = []
    core = object()

    def build_core(root: Path, directory: str) -> object:
        calls.append(("core", root, directory))
        return core

    inputs = BootstrapInputs(
        working_directory=lambda: Path("/explicit/workspace"),
        core_builder=build_core,
        existing_core_builder=lambda root: calls.append(("existing", root)),
        console_factory=lambda: calls.append(("console",)),
    )
    command = build_cli(inputs, command_registry={})

    @click.command()
    @click.pass_context
    def probe(ctx: click.Context) -> None:
        click.echo(str(ctx.obj["core"] is core))

    command.add_command(probe)
    runner = CliRunner()
    result = runner.invoke(command, ["probe"])
    second_result = runner.invoke(command, ["probe"])
    assert result.exit_code == 0, result.exception
    assert result.stdout.strip() == "True"
    assert second_result.exit_code == 0, second_result.exception
    assert calls == [
        ("core", Path("/explicit/workspace"), ".roadmap"),
        ("core", Path("/explicit/workspace"), ".roadmap"),
    ]


def test_bootstrap_returns_only_the_retained_command_capabilities(
    tmp_path: Path,
) -> None:
    """The old facade and coordinator graph cannot leak back into commands."""
    services = create_core(tmp_path)

    assert set(services.__dataclass_fields__) == {
        "root_path",
        "roadmap_dir",
        "configuration",
        "current_identity",
        "issue_queries",
        "issue_mutations",
        "local_git",
        "planning",
        "health",
    }
    assert not hasattr(services, "issues")
    assert not hasattr(services, "milestones")
    assert not hasattr(services, "projects")


def test_cli_modules_do_not_import_removed_ownership_zones() -> None:
    """Inbound commands receive Application capabilities through Click context."""
    forbidden_prefixes = (
        "roadmap.core",
        "roadmap.common",
        "roadmap.infrastructure",
        "roadmap.adapters.outbound",
    )
    offenders: list[str] = []
    for path in sorted(CLI_ROOT.rglob("*.py")):
        if any(imported.startswith(forbidden_prefixes) for imported in _imports(path)):
            offenders.append(str(path.relative_to(ROOT)))
    assert offenders == []
