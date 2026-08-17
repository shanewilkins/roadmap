"""Lazy Click adapter assembled by :mod:`roadmap.bootstrap`."""

import importlib
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from typing import Any

import click

from roadmap import __version__


def _handle_cli_exception(ctx: click.Context, error: Exception) -> Any:
    from roadmap.adapters.cli.exception_handler import handle_cli_exception

    return handle_cli_exception(ctx, error, show_traceback=False)


CommandLocation = tuple[str, str, str]

# fmt: off
COMMAND_REGISTRY: dict[str, CommandLocation] = {
    "init": ("roadmap.adapters.cli.core", "init", "Initialize a new roadmap structure."),
    "status": ("roadmap.adapters.cli.core", "status", "Show the current status of the roadmap."),
    "health": ("roadmap.adapters.cli.core", "health", "Health and diagnostics commands."),
    "today": ("roadmap.adapters.cli.today", "today", "Show your daily workflow summary for the upcoming milestone."),
    "cleanup": ("roadmap.infrastructure.maintenance", "cleanup", "Comprehensive roadmap cleanup - fix backups, folders, duplicates, and malformed files."),
    "analysis": ("roadmap.adapters.cli.analysis", "analysis", "Analysis and insights commands."),
    "comment": ("roadmap.adapters.cli.comment", "comment", "Manage comments on issues and milestones."),
    "config": ("roadmap.adapters.cli.config", "config", "Manage roadmap configuration."),
    "data": ("roadmap.adapters.cli.data", "data", "Export, import, and analyze roadmap data."),
    "git": ("roadmap.adapters.cli.git", "git", "Git integration and workflow management."),
    "issue": ("roadmap.adapters.cli.issues", "issue", "Manage issues."),
    "milestone": ("roadmap.adapters.cli.milestones", "milestone", "Manage milestones."),
    "project": ("roadmap.adapters.cli.projects", "project", "Manage projects (top-level planning documents)."),
    "sync": ("roadmap.adapters.cli.sync", "sync", "Sync roadmap with remote repository."),
    "validate-links": ("roadmap.adapters.cli.sync_validation", "validate_links", "Validate remote links in the database against YAML files."),
}
# fmt: on


@dataclass
class CliRuntime:
    """Explicit process collaborators supplied by Bootstrap."""

    core_factory: Callable[[str], Any]
    existing_core_factory: Callable[[], Any | None]
    logging_initializer: Callable[[], None]
    tracing_initializer: Callable[[], None]
    console_factory: Callable[[], Any]
    initialized: bool = False

    def initialize(self) -> None:
        if self.initialized:
            return
        self.logging_initializer()
        self.tracing_initializer()
        self.initialized = True


class RoadmapClickGroup(click.Group):
    """Click group that loads commands on demand and normalizes failures."""

    def __init__(
        self,
        *args: Any,
        command_registry: Mapping[str, CommandLocation],
        console_factory: Callable[[], Any],
        **kwargs: Any,
    ) -> None:
        super().__init__(*args, **kwargs)
        self._command_registry = dict(command_registry)
        self._console_factory = console_factory
        self._command_cache: dict[str, click.Command] = {}

    def list_commands(self, ctx: click.Context) -> list[str]:
        """List declared and explicitly attached commands deterministically."""
        return sorted(set(self._command_registry) | set(super().list_commands(ctx)))

    def format_commands(self, ctx: click.Context, formatter: click.HelpFormatter) -> None:  # fmt: skip
        """Render root help from static metadata without importing features."""
        names = sorted(self._command_registry)
        limit = formatter.width - 6 - max(map(len, names), default=0)
        rows = [(name, click.utils.make_default_short_help(self._command_registry[name][2], limit)) for name in names]  # fmt: skip
        with formatter.section("Commands"):
            formatter.write_dl(rows)

    def get_command(self, ctx: click.Context, name: str) -> click.Command | None:
        """Load one registered command only when Click requests it."""
        if (attached := super().get_command(ctx, name)) is not None:
            return attached
        if name in self._command_cache:
            return self._command_cache[name]
        location = self._command_registry.get(name)
        if location is None:
            return None
        module_path, attribute, _help = location
        try:
            self._command_cache[name] = command = getattr(importlib.import_module(module_path), attribute)  # fmt: skip
        except Exception as error:
            self._console_factory().print(
                f"⚠️  Failed to load command '{name}': {error}", style="yellow"
            )
            return None
        return command

    def invoke(self, ctx: click.Context) -> Any:
        """Invoke the CLI with centralized Roadmap exception handling."""
        try:
            return super().invoke(ctx)
        except (click.exceptions.Exit, click.ClickException, click.Abort, SystemExit):
            raise
        except Exception as error:
            return _handle_cli_exception(ctx, error)


def create_cli(
    runtime: CliRuntime,
    *,
    command_registry: Mapping[str, CommandLocation] = COMMAND_REGISTRY,
) -> RoadmapClickGroup:
    """Create a CLI bound only to collaborators explicitly supplied by Bootstrap."""

    @click.group(
        cls=RoadmapClickGroup,
        command_registry=command_registry,
        console_factory=runtime.console_factory,
    )
    @click.version_option(version=__version__)
    @click.pass_context
    def cli(ctx: click.Context) -> None:
        """Roadmap CLI - A command line tool for creating and managing roadmaps."""
        ctx.ensure_object(dict)
        ctx.obj.setdefault("core_factory", runtime.core_factory)
        ctx.obj.setdefault("existing_core_factory", runtime.existing_core_factory)
        ctx.obj.setdefault("console_factory", runtime.console_factory)
        runtime.initialize()

        if ctx.invoked_subcommand not in {None, "init"} and "core" not in ctx.obj:
            try:
                ctx.obj["core"] = runtime.core_factory(".roadmap")
            except Exception as error:
                _handle_cli_exception(ctx, error)

    return cli
