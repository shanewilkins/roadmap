"""Handler for Git hooks management."""

import structlog
from rich.console import Console

from roadmap.adapters.git.git_hooks_manager import GitHookManager
from roadmap.infrastructure.core import RoadmapCore

logger = structlog.get_logger()


class GitHooksHandler:
    """Handles Git hooks installation, removal, and status checking."""

    def __init__(self, console: Console):
        """Initialize handler with console for output.

        Args:
            console: Rich Console instance
        """
        self.console = console

    def install_hooks(self, core: RoadmapCore):
        """Install Git hooks for roadmap integration.

        Args:
            core: RoadmapCore instance

        Raises:
            Exception: If hook installation fails
        """
        try:
            manager = GitHookManager(core)
            if manager.install_hooks():
                self.console.print(
                    "✅ Git hooks installed successfully", style="bold green"
                )
                self.console.print(
                    "Hooks will now automatically track commits and branch changes",
                    style="green",
                )
            else:
                self.console.print(
                    "❌ Failed to install hooks. Not a git repository?",
                    style="bold red",
                )
        except Exception as e:
            self.console.print(f"❌ Error installing hooks: {e}", style="bold red")
            raise

    def uninstall_hooks(self, core: RoadmapCore):
        """Remove Git hooks for roadmap integration.

        Args:
            core: RoadmapCore instance

        Raises:
            Exception: If hook removal fails
        """
        try:
            manager = GitHookManager(core)
            if manager.uninstall_hooks():
                self.console.print(
                    "✅ Git hooks removed successfully", style="bold green"
                )
            else:
                self.console.print("❌ Failed to remove hooks", style="bold red")
        except Exception as e:
            self.console.print(f"❌ Error removing hooks: {e}", style="bold red")
            raise

    def show_hooks_status(self, core: RoadmapCore):
        """Show status of installed Git hooks.

        Args:
            core: RoadmapCore instance

        Raises:
            Exception: If status check fails
        """
        try:
            manager = GitHookManager(core)
            status = manager.get_hooks_status()

            if not status:
                self.console.print("No hooks installed", style="yellow")
                return

            self.console.print("Git Hooks Status:", style="bold")
            self.console.print()

            for hook_name, hook_info in status.items():
                installed = "✅" if hook_info.get("is_roadmap_hook") else "❌"
                executable = "✓" if hook_info.get("executable") else "✗"
                self.console.print(
                    f"{installed} {hook_name:20} [executable: {executable}]"
                )

            self.console.print()
            self.console.print(
                "Run 'roadmap git hooks-install' to install all hooks", style="dim"
            )
        except Exception as e:
            self.console.print(f"❌ Error checking hooks: {e}", style="bold red")
            raise
