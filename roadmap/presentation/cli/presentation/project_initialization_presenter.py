"""
Presentation layer for project initialization display logic.

Handles all user-facing output:
- Displaying detected context
- Prompting for project information
- Showing project creation status and results
"""

import click

from roadmap.shared.console import get_console

console = get_console()


class ProjectInitializationPresenter:
    """Presenter for project initialization workflow."""

    @staticmethod
    def show_detected_context(detected_info: dict, interactive: bool) -> None:
        """Display detected project context.

        Args:
            detected_info: Dictionary with detected context information
            interactive: Whether in interactive mode
        """
        console.print("🔍 Detected Context:", style="bold blue")
        if detected_info.get("git_repo"):
            console.print(f"  Git repository: {detected_info['git_repo']}")
        else:
            console.print("  Git repository: Not detected", style="dim")
            if interactive:
                console.print(
                    "    💡 Consider running 'git init' to enable advanced features",
                    style="yellow",
                )
        if detected_info.get("project_name"):
            console.print(f"  Project name: {detected_info['project_name']}")
        console.print(f"  Directory: {detected_info.get('directory', 'current')}")
        console.print()

    @staticmethod
    def prompt_project_name(
        suggested_name: str | None = None, interactive: bool = True, yes: bool = False
    ) -> str | None:
        """Prompt user for project name.

        Args:
            suggested_name: Default project name to suggest
            interactive: Whether to prompt (only if True)
            yes: Skip prompts and use defaults

        Returns:
            Project name from user input or suggested name
        """
        if not interactive or yes:
            return suggested_name

        return click.prompt("Project name", default=suggested_name, show_default=True)

    @staticmethod
    def prompt_project_description(
        suggested_description: str | None = None,
        interactive: bool = True,
        yes: bool = False,
    ) -> str | None:
        """Prompt user for project description.

        Args:
            suggested_description: Default description to suggest
            interactive: Whether to prompt (only if True)
            yes: Skip prompts and use defaults

        Returns:
            Project description from user input or suggested description
        """
        if not interactive or yes:
            return suggested_description

        return click.prompt(
            "Project description",
            default=suggested_description,
            show_default=True,
        )

    @staticmethod
    def show_project_creation_status() -> None:
        """Show status message while creating project."""
        console.print("📋 Creating main project...", style="bold blue")

    @staticmethod
    def show_project_created(project_info: dict) -> None:
        """Display confirmation that project was created.

        Args:
            project_info: Dictionary with project information
        """
        console.print(
            f"✅ Created main project: {project_info['name']} (ID: {project_info['id'][:8]})",
            style="green",
        )

    @staticmethod
    def show_existing_projects(projects: list[dict]) -> None:
        """Display existing projects found during initialization.

        Args:
            projects: List of existing projects with name and id
        """
        console.print("✅ Joined existing project(s):", style="green")
        for proj in projects:
            console.print(f"  • {proj['name']} (ID: {proj['id'][:8]})")

        if len(projects) > 1:
            console.print(
                f"\n  💡 {len(projects)} projects found. All will be available.",
                style="dim",
            )

    @staticmethod
    def show_success_summary(
        name: str,
        github_configured: bool,
        project_info: dict | None,
        detected_info: dict,
    ) -> None:
        """Show comprehensive success summary and next steps.

        Args:
            name: Name of the roadmap directory
            github_configured: Whether GitHub integration was configured
            project_info: Information about created/joined project
            detected_info: Detected context information
        """
        console.print()
        console.print("✅ Setup Complete!", style="bold green")
        console.print()

        # Show what was created
        console.print("📁 Created:", style="bold cyan")
        console.print(f"  ✓ Roadmap structure: {name}/")
        console.print("    ├── issues/       (issue tracking)")
        console.print("    ├── milestones/   (milestone management)")
        console.print("    ├── projects/     (project documents)")
        console.print("    ├── templates/    (document templates)")
        console.print("    ├── artifacts/    (generated content)")
        console.print("    └── config.yaml   (configuration)")

        if project_info:
            console.print(
                f"  ✓ Main project: {project_info['name']} (ID: {project_info['id'][:8]})"
            )
        if github_configured:
            console.print("  ✓ GitHub integration: Connected and configured")
            console.print("    • Bidirectional sync enabled")
            console.print("    • Automatic issue linking")
            console.print("    • Webhook support ready")
        console.print("  ✓ Security: Secure file permissions and credential storage")

        console.print()
        console.print("🚀 Next Steps:", style="bold yellow")

        if project_info:
            console.print(f"  → roadmap project show {project_info['id'][:8]}")
        console.print('  → roadmap issue create "Your first issue"')
        if github_configured:
            console.print("  → roadmap sync bidirectional        # Sync with GitHub")
            console.print("  → roadmap git setup                 # Configure git hooks")
        console.print("  → roadmap user show-dashboard        # View your dashboard")

        console.print()
        console.print("📚 Learn More:", style="bold cyan")
        console.print("  → roadmap --help                    # All available commands")
        console.print("  → roadmap issue --help               # Issue management")
        if github_configured:
            console.print(
                "  → roadmap sync --help                # GitHub synchronization"
            )
            console.print("  → roadmap git --help                 # Git integration")
        console.print("  → roadmap project --help             # Project management")
        console.print("  → roadmap milestone --help           # Milestone tracking")

        console.print()
        console.print("💡 Pro Tips:", style="bold magenta")
        console.print("  • Use 'roadmap user show-dashboard' for daily task overview")

        if detected_info.get("has_git"):
            console.print(
                "  • Set up git hooks with 'roadmap git setup' for automatic updates"
            )
            if github_configured:
                console.print(
                    "  • Try 'roadmap sync bidirectional' to sync existing GitHub issues"
                )
        else:
            console.print(
                "  • Initialize git with 'git init' to enable advanced features:"
            )
            console.print("    - Automatic issue updates from commit messages")
            console.print("    - Git hooks for seamless integration")
            console.print("    - GitHub synchronization capabilities")

        console.print(
            "  • Create templates in .roadmap/templates/ for consistent formatting"
        )

    @staticmethod
    def show_warning(message: str, context: str | None = None) -> None:
        """Display a warning message.

        Args:
            message: Warning message to display
            context: Optional context about the warning
        """
        if context:
            console.print(f"⚠️  {message}", style="yellow")
            console.print(f"   {context}", style="dim")
        else:
            console.print(f"⚠️  {message}", style="yellow")

    @staticmethod
    def show_error(message: str) -> None:
        """Display an error message.

        Args:
            message: Error message to display
        """
        console.print(f"❌ {message}", style="bold red")
