"""Presenter for core initialization command output."""

from typing import TYPE_CHECKING, Union

if TYPE_CHECKING:
    from roadmap.core.domain.health import HealthStatus

import click  # type: ignore[import]


class CoreInitializationPresenter:
    """Handles all console output for core initialization commands."""

    def __init__(self):
        """Initialize presenter."""
        pass

    # ========== Init Command Output ==========

    def present_initialization_header(self) -> None:
        """Show initialization header."""
        click.secho("🚀 Roadmap CLI Initialization", fg="cyan", bold=True)
        click.echo()

    def present_force_reinitialize_warning(self, name: str) -> None:
        """Show warning about force re-initialization."""
        click.secho(
            f"⚠️  --force specified: removing existing {name}/",
            fg="yellow",
        )

    def present_already_initialized_info(self, name: str) -> None:
        """Show info that roadmap is already initialized."""
        click.secho(
            f"ℹ️  Roadmap already initialized in {name}/",
            fg="cyan",
        )
        click.echo(
            "    Updating configuration while preserving existing data.", err=False
        )
        click.echo()

    def present_initialization_error(self, error: str) -> None:
        """Show initialization error."""
        click.secho(f"❌ {error}", fg="red", bold=True)

    def present_initialization_tip(self) -> None:
        """Show helpful tip for initialization errors."""
        click.secho(
            "Tip: use --force to reinitialize or --dry-run to preview.",
            fg="yellow",
        )

    def present_already_in_progress_error(self) -> None:
        """Show error that initialization is already in progress."""
        click.secho(
            "❌ Initialization already in progress. Try again later.",
            fg="red",
            bold=True,
        )

    def present_creating_structure(self, name: str) -> None:
        """Show status while creating structure."""
        click.secho(f"🗂️  Creating roadmap structure in {name}/...", fg="white")

    def present_existing_projects_found(self, count: int) -> None:
        """Show info about existing projects found."""
        click.secho(
            f"\n  💡 {count} projects found. All will be available.",
            fg="white",
        )

    def present_project_created(self, project_name: str) -> None:
        """Show that a project was created."""
        click.secho(f"✅ Created project: {project_name}", fg="green")

    def present_project_joined(self, project_name: str) -> None:
        """Show that team member joined existing project."""
        click.secho(f"✅ Joined existing project: {project_name}", fg="green")

    def present_projects_joined(self, main_project: str, count: int) -> None:
        """Show that team member joined with multiple projects available."""
        click.secho(
            f"✅ Joined {main_project} ({count} projects available)", fg="green"
        )

    def present_initialization_warning(self, message: str) -> None:
        """Show warning message after initialization."""
        click.secho(
            "⚠️  Initialization completed with warnings; see above.",
            fg="yellow",
        )

    def present_initialization_failed(self, error: str) -> None:
        """Show initialization failure message."""
        click.secho(f"❌ Failed to initialize roadmap: {error}", fg="red", bold=True)

    # ========== Status Command Output ==========

    def present_status_header(self) -> None:
        """Show status command header."""
        click.secho("📊 Roadmap Status Report", fg="cyan", bold=True)
        click.echo()

    def present_status_section(self, title: str) -> None:
        """Show status section header."""
        click.secho(f"\n{title}", fg="cyan", bold=True)
        click.secho("─" * (len(title)), fg="white")

    def present_status_item(self, label: str, value: str, ok: bool = True) -> None:
        """Show a status item."""
        color = "green" if ok else "yellow"
        icon = "✓" if ok else "⚠"
        click.secho(f"{icon} {label}: {value}", fg=color)

    def present_status_not_initialized(self) -> None:
        """Show that roadmap is not initialized."""
        click.secho("❌ Roadmap not initialized in .roadmap/", fg="red")
        click.echo("Run 'roadmap init' to get started.")

    # ========== Health Check Output ==========

    def present_health_header(self) -> None:
        """Show health check header."""
        click.secho("🏥 Roadmap Health Check", fg="cyan", bold=True)
        click.echo()

    def present_health_section(self, title: str) -> None:
        """Show health section header."""
        click.secho(f"\n{title}", fg="cyan", bold=True)
        click.secho("─" * (len(title)), fg="white")

    def present_health_check(
        self, check_name: str, status: Union[str, "HealthStatus"], message: str = ""
    ) -> None:
        """Show individual health check result.

        Args:
            check_name: Name of the health check
            status: HealthStatus enum value or string
            message: Optional details about the check
        """
        from roadmap.infrastructure.health import HealthStatus

        # Convert status to string if it's an enum
        status_str = status.name if isinstance(status, HealthStatus) else str(status)

        # Map status to display values
        status_map = {
            "HEALTHY": ("✅", "green"),
            "DEGRADED": ("⚠️", "yellow"),
            "UNHEALTHY": ("❌", "red"),
            "healthy": ("✅", "green"),
            "warning": ("⚠️", "yellow"),
            "error": ("❌", "red"),
        }

        icon, color = status_map.get(status_str, ("?", "white"))
        display_name = check_name.replace("_", " ").title()

        click.secho(f"{icon} {display_name}: {status_str}", fg=color)
        if message:
            click.echo(f"  {message}")

    def present_overall_health(self, status: Union[str, "HealthStatus"]) -> None:
        """Show overall health status.

        Args:
            status: HealthStatus enum value or string
        """
        from roadmap.infrastructure.health import HealthStatus

        # Convert status to string if it's an enum
        status_str = status.name if isinstance(status, HealthStatus) else str(status)

        status_map = {
            "HEALTHY": ("✅", "green"),
            "DEGRADED": ("⚠️", "yellow"),
            "UNHEALTHY": ("❌", "red"),
            "healthy": ("✅", "green"),
            "warning": ("⚠️", "yellow"),
            "error": ("❌", "red"),
        }

        icon, color = status_map.get(status_str, ("?", "white"))

        click.echo()
        click.secho(
            f"{icon} Overall Status: {status_str}",
            fg=color,
            bold=True,
        )

    def present_health_warning(self, message: str) -> None:
        """Show health warning."""
        click.secho(f"⚠️  {message}", fg="yellow")

    # ========== GitHub Integration Output ==========

    def present_github_testing(self) -> None:
        """Show message while testing GitHub connection."""
        click.secho("🔍 Testing GitHub connection...", fg="yellow")

    def present_github_credentials_stored(self) -> None:
        """Show message that credentials were stored."""
        click.secho("🔒 Credentials stored securely", fg="green")

    def present_github_unavailable(self, reason: str) -> None:
        """Show GitHub integration unavailable message."""
        click.secho(
            f"⚠️  GitHub integration not available: {reason}",
            fg="yellow",
        )

    def present_github_setup_failed(self, error: str) -> None:
        """Show GitHub setup failure."""
        click.secho(f"❌ GitHub setup failed: {error}", fg="red")

    # ========== Generic Output Methods ==========

    def present_error(self, message: str) -> None:
        """Show generic error message."""
        click.secho(f"❌ {message}", fg="red", bold=True)

    def present_warning(self, message: str) -> None:
        """Show generic warning message."""
        click.secho(f"⚠️  {message}", fg="yellow")

    def present_info(self, message: str) -> None:
        """Show generic info message."""
        click.secho(f"ℹ️  {message}", fg="cyan")

    def present_success(self, message: str) -> None:
        """Show generic success message."""
        click.secho(f"✅ {message}", fg="green", bold=True)

    def present_initialization_complete(self, created_new: bool) -> None:
        """Show initialization completion with next steps.

        Args:
            created_new: Whether a new roadmap was created or existing was joined
        """
        click.echo()
        if created_new:
            click.secho("✅ Roadmap initialized successfully!", fg="green", bold=True)
            click.echo("   📁 Data stored in: .roadmap/")
        else:
            click.secho("✅ Initialization complete!", fg="green", bold=True)

        click.echo()
        click.echo("Next steps:")
        click.echo('   • roadmap issue create "Your first task"')
        click.echo('   • roadmap milestone create "v1.0"')
        click.echo("   • roadmap list")
        click.echo()

    def present_existing_projects_info(self, project_names: list) -> None:
        """Show info about existing projects found.

        Args:
            project_names: List of project names that were found
        """
        click.echo()
        if len(project_names) == 1:
            click.secho(
                f"ℹ️  Found existing project: {project_names[0]}",
                fg="cyan",
            )
        else:
            projects_str = ", ".join(project_names[:3])
            if len(project_names) > 3:
                projects_str += f", +{len(project_names) - 3} more"
            click.secho(
                f"ℹ️  Found {len(project_names)} projects: {projects_str}",
                fg="cyan",
            )
        click.secho("   Run 'roadmap project list' to see all", fg="white")
