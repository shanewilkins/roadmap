"""Roadmap's sole process composition root."""

from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from roadmap.adapters.inbound.cli import (
    COMMAND_REGISTRY,
    CliRuntime,
    CommandLocation,
    RoadmapClickGroup,
    create_cli,
)


def _create_core(root_path: Path, roadmap_dir_name: str) -> Any:
    from roadmap.bootstrap.core import create_core

    return create_core(root_path, roadmap_dir_name)


def _find_existing_core(root_path: Path) -> Any | None:
    from roadmap.bootstrap.core import find_existing_core

    return find_existing_core(root_path)


def _initialize_tracing() -> None:
    """Tracing is intentionally disabled for the local-only CLI."""


def _initialize_logging() -> None:
    """The CLI emits deliberate user output; libraries stay quiet by default."""


def _create_console() -> Any:
    from rich.console import Console

    return Console()


def _create_initialization(root_path: Path, roadmap_dir_name: str) -> Any:
    from roadmap.bootstrap.core import create_initialization

    return create_initialization(root_path, roadmap_dir_name)


def _create_workspace_migration(root_path: Path) -> Any:
    from roadmap.adapters.outbound.persistence.documents import DocumentRepository
    from roadmap.adapters.outbound.persistence.migration import (
        FilesystemWorkspaceMigration,
    )
    from roadmap.adapters.outbound.persistence.projection import SQLiteProjection
    from roadmap.application.use_cases import WorkspaceMigration

    roadmap_dir = root_path / ".roadmap"
    documents = DocumentRepository(roadmap_dir)
    projection = SQLiteProjection(roadmap_dir / "db" / "projection.db", documents)
    return WorkspaceMigration(
        FilesystemWorkspaceMigration(
            roadmap_dir,
            projection,
            Path.home() / ".config" / "roadmap" / "config.yaml",
        )
    )


@dataclass(frozen=True)
class BootstrapInputs:
    """Explicit environment and factories used to build one CLI process."""

    working_directory: Callable[[], Path] = Path.cwd
    core_builder: Callable[[Path, str], Any] = _create_core
    existing_core_builder: Callable[[Path], Any | None] = _find_existing_core
    logging_initializer: Callable[[], None] = _initialize_logging
    tracing_initializer: Callable[[], None] = _initialize_tracing
    console_factory: Callable[[], Any] = _create_console
    migration_builder: Callable[[Path], Any] = _create_workspace_migration
    initialization_builder: Callable[[Path, str], Any] = _create_initialization


def build_cli(
    inputs: BootstrapInputs | None = None,
    *,
    command_registry: dict[str, CommandLocation] = COMMAND_REGISTRY,
) -> RoadmapClickGroup:
    """Build a deterministic CLI from explicit process inputs."""
    selected = inputs or BootstrapInputs()
    runtime = CliRuntime(
        core_factory=lambda roadmap_dir_name: selected.core_builder(
            selected.working_directory(), roadmap_dir_name
        ),
        existing_core_factory=lambda: selected.existing_core_builder(
            selected.working_directory()
        ),
        logging_initializer=selected.logging_initializer,
        tracing_initializer=selected.tracing_initializer,
        console_factory=selected.console_factory,
        migration_factory=lambda: selected.migration_builder(
            selected.working_directory()
        ),
        initialization_factory=lambda name: selected.initialization_builder(
            selected.working_directory(), name
        ),
    )
    return create_cli(runtime, command_registry=command_registry)


cli = build_cli()


def main() -> None:
    """Execute the Bootstrap-assembled console adapter."""
    cli()
