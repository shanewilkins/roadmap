"""Roadmap's sole process composition root."""

from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from roadmap.adapters.cli import (
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
    from roadmap.common.observability.otel_init import initialize_tracing

    initialize_tracing()


def _initialize_logging() -> None:
    import structlog

    from roadmap.common.logging import setup_logging

    if not structlog.is_configured():
        setup_logging(log_level="INFO", debug_mode=False, log_to_file=True)


def _create_console() -> Any:
    from roadmap.common.console import get_console

    return get_console()


@dataclass(frozen=True)
class BootstrapInputs:
    """Explicit environment and factories used to build one CLI process."""

    working_directory: Callable[[], Path] = Path.cwd
    core_builder: Callable[[Path, str], Any] = _create_core
    existing_core_builder: Callable[[Path], Any | None] = _find_existing_core
    logging_initializer: Callable[[], None] = _initialize_logging
    tracing_initializer: Callable[[], None] = _initialize_tracing
    console_factory: Callable[[], Any] = _create_console


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
    )
    return create_cli(runtime, command_registry=command_registry)


cli = build_cli()


def main() -> None:
    """Execute the Bootstrap-assembled console adapter."""
    cli()
