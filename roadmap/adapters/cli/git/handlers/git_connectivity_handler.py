"""Handler for Git connectivity and authentication testing."""

import structlog
from rich.console import Console

from roadmap.infrastructure.coordination.core import RoadmapCore

logger = structlog.get_logger()


class GitConnectivityHandler:
    """Handles testing and verifying Git repository connectivity."""

    def __init__(self, console: Console):
        """Initialize handler with console for output.

        Args:
            console: Rich Console instance
        """
        self.console = console

    def test_git_connectivity(self, core: RoadmapCore):
        """Test and verify Git repository connectivity for self-hosting.

        Args:
            core: RoadmapCore instance

        Raises:
            Exception: If git connectivity test fails
        """
        from roadmap.adapters.cli.services.sync_service import (
            get_sync_backend,
            test_backend_connectivity,
        )

        self.console.print("🔌 Git Repository Connectivity Test", style="bold cyan")
        self.console.print()

        # Try to create vanilla git backend to test connectivity
        self.console.print("🧪 Testing Git repository connectivity...", style="cyan")
        logger.debug("git_connectivity_testing")

        try:
            # Use sync service to create vanilla git backend
            backend = get_sync_backend("git", core, {})

            if backend is None:
                self.console.print(
                    "❌ Could not initialize Git backend (not in a git repository?)",
                    style="bold red",
                )
                logger.warning("git_backend_initialization_failed")
                return

            # Test authentication (connectivity check)
            success, message = test_backend_connectivity(backend, "git")
            if success:
                self.console.print(message, style="green")
                self.console.print(
                    "Your git repository is accessible and ready for syncing",
                    style="dim",
                )
                logger.info("git_connectivity_verified")
            else:
                self.console.print(
                    "⚠️  Could not verify git remote access",
                    style="yellow",
                )
                self.console.print()
                self.console.print(
                    "This might be due to:",
                    style="dim",
                )
                self.console.print("  • SSH key not configured", style="dim")
                self.console.print("  • HTTPS credentials needed", style="dim")
                self.console.print("  • Network connectivity issues", style="dim")
                self.console.print(
                    "  • Remote repository doesn't exist yet",
                    style="dim",
                )
                self.console.print()
                self.console.print(
                    "For SSH: Make sure your SSH key is in ~/.ssh/",
                    style="dim",
                )
                self.console.print(
                    "For HTTPS: Configure git credentials with: git config credential.helper",
                    style="dim",
                )
                logger.warning("git_connectivity_verification_failed")

        except ValueError as e:
            self.console.print(
                f"❌ Git repository error: {e}",
                style="bold red",
            )
            logger.error(
                "git_repository_error",
                error=str(e),
                error_type=type(e).__name__,
            )
            self.console.print()
            self.console.print(
                "Make sure you're in a git repository directory",
                style="dim",
            )
        except Exception as e:
            self.console.print(
                f"❌ Connectivity test failed: {e}",
                style="bold red",
            )
            logger.error(
                "git_connectivity_error",
                error=str(e),
                error_type=type(e).__name__,
            )
