"""Lazy Click adapter assembled by :mod:`roadmap.bootstrap`."""

import importlib
import stat
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import click


def _handle_cli_exception(ctx: click.Context, error: Exception) -> Any:
    from roadmap.adapters.inbound.cli.exception_handler import handle_cli_exception

    return handle_cli_exception(
        ctx, error, show_traceback=bool(ctx.find_root().params.get("debug", False))
    )


CommandLocation = tuple[str, str, str]


@dataclass(frozen=True, slots=True)
class WorkspaceServices:
    """Application capabilities injected into commands for one workspace."""

    root_path: Path
    roadmap_dir: Path
    configuration: Any
    current_identity: Any
    issue_queries: Any
    issue_mutations: Any
    local_git: Any
    planning: Any
    health: Any
    github_closures: Any

    def is_initialized(self) -> bool:
        return (
            self.roadmap_dir.is_dir() and (self.roadmap_dir / "config.yaml").is_file()
        )


# fmt: off
COMMAND_REGISTRY: dict[str, CommandLocation] = {
    "init": ("roadmap.adapters.inbound.cli.init", "init", "Initialize a new roadmap structure."),
    "status": ("roadmap.adapters.inbound.cli.status", "status", "Show the current status of the roadmap."),
    "health": ("roadmap.adapters.inbound.cli.health", "health", "Read-only diagnosis and explicit recovery."),
    "migrate": ("roadmap.adapters.inbound.cli.migrate", "migrate", "Upgrade a 0.1.1 workspace to the 0.2 canonical layout."),
    "today": ("roadmap.adapters.inbound.cli.today", "today", "Show your daily workflow summary for the upcoming milestone."),
    "cleanup": ("roadmap.adapters.inbound.cli.cleanup", "cleanup", "Preview or remove retention-qualified legacy backups."),
    "analysis": ("roadmap.adapters.inbound.cli.analysis", "analysis", "Analysis and insights commands."),
    "config": ("roadmap.adapters.inbound.cli.config", "config", "Manage roadmap configuration."),
    "data": ("roadmap.adapters.inbound.cli.data", "data", "Export canonical Roadmap data."),
    "git": ("roadmap.adapters.inbound.cli.git", "git", "Inspect local Git and link issue branches."),
    "github": ("roadmap.adapters.inbound.cli.github", "github", "Publish explicit committed closures to GitHub."),
    "issue": ("roadmap.adapters.inbound.cli.issues", "issue", "Manage issues."),
    "milestone": ("roadmap.adapters.inbound.cli.milestones", "milestone", "Manage milestones."),
    "project": ("roadmap.adapters.inbound.cli.projects", "project", "Manage projects (top-level planning documents)."),
}
# fmt: on


@dataclass
class CliRuntime:
    """Explicit process collaborators supplied by Bootstrap."""

    core_factory: Callable[[str], Any]
    existing_core_factory: Callable[[], Any | None]
    console_factory: Callable[[], Any]
    migration_factory: Callable[[], Any]
    initialization_factory: Callable[[str], Any]
    version: str
    workspace_factories: Callable[[Path], dict[str, Any]] | None = None


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
        rows = [(name, click.Command(name, help=self._command_registry[name][2]).get_short_help_str(limit)) for name in names]  # fmt: skip
        with formatter.section("Commands"):
            formatter.write_dl(rows)

    def get_command(self, ctx: click.Context, cmd_name: str) -> click.Command | None:
        """Load one registered command only when Click requests it."""
        if (attached := super().get_command(ctx, cmd_name)) is not None:
            return attached
        if cmd_name in self._command_cache:
            return self._command_cache[cmd_name]
        location = self._command_registry.get(cmd_name)
        if location is None:
            return None
        module_path, attribute, _help = location
        self._command_cache[cmd_name] = command = getattr(importlib.import_module(module_path), attribute)  # fmt: skip
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
    @click.version_option(version=runtime.version)
    @click.option(
        "--debug", is_flag=True, help="Show tracebacks for unexpected errors."
    )
    @click.option(
        "--workspace",
        type=click.Path(path_type=Path),
        help="Canonical workspace directory; overrides the current-directory default.",
    )
    @click.pass_context
    def cli(ctx: click.Context, debug: bool, workspace: Path | None) -> None:  # noqa: ARG001
        """Roadmap CLI - A command line tool for creating and managing roadmaps."""
        ctx.ensure_object(dict)
        ctx.obj.setdefault("core_factory", runtime.core_factory)
        ctx.obj.setdefault("existing_core_factory", runtime.existing_core_factory)
        ctx.obj.setdefault("console_factory", runtime.console_factory)
        ctx.obj.setdefault("migration_factory", runtime.migration_factory)
        ctx.obj.setdefault("initialization_factory", runtime.initialization_factory)
        if workspace is not None:
            if runtime.workspace_factories is None:
                raise click.ClickException(
                    "Explicit workspace selection requires Bootstrap"
                )
            selected = workspace.expanduser().absolute()
            ctx.obj.update(runtime.workspace_factories(selected))
            ctx.obj["workspace"] = selected
            ctx.obj.pop("core", None)
            if ctx.invoked_subcommand not in {None, "init", "migrate"}:
                try:
                    valid = stat.S_ISDIR(selected.stat().st_mode) and stat.S_ISREG(
                        (selected / "config.yaml").stat().st_mode
                    )
                except OSError as error:
                    raise click.ClickException(
                        f"Cannot open explicit workspace {selected}: {error}"
                    ) from error
                if not valid:
                    raise click.ClickException(
                        f"Explicit workspace is not initialized: {selected}"
                    )
        if (
            ctx.invoked_subcommand not in {None, "init", "migrate"}
            and "core" not in ctx.obj
        ):
            try:
                ctx.obj["core"] = ctx.obj["core_factory"](".roadmap")
            except Exception as error:
                _handle_cli_exception(ctx, error)

    return cli
