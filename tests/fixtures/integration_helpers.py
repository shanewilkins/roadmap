"""Integration test helpers for common patterns.

Provides utilities for initializing roadmap, creating test data,
and asserting on CLI commands in a robust way.
"""

from typing import Any

from click.testing import CliRunner

from roadmap.adapters.cli import main
from roadmap.infrastructure.core import RoadmapCore


class IntegrationTestBase:
    """Base utilities for integration tests.

    Provides common patterns and assertion helpers to reduce boilerplate
    and improve test robustness.
    """

    @staticmethod
    def init_roadmap(
        cli_runner: CliRunner,
        project_name: str = "Test Project",
        skip_github: bool = True,
    ) -> RoadmapCore:
        """Initialize roadmap in isolated filesystem.

        Uses the CLI init command to ensure proper initialization,
        replicating actual user workflow.

        Args:
            cli_runner: Click CliRunner instance
            project_name: Project name for initialization
            skip_github: Whether to skip GitHub integration

        Returns:
            RoadmapCore instance for the initialized project

        Raises:
            AssertionError: If initialization fails
        """
        result = cli_runner.invoke(
            main,
            [
                "init",
                "--project-name",
                project_name,
                "--non-interactive",
            ]
            + (["--skip-github"] if skip_github else []),
        )

        if result.exit_code != 0:
            error_msg = "Failed to initialize roadmap\n"
            error_msg += f"Exit code: {result.exit_code}\n"
            error_msg += f"Output: {result.output}"
            if result.exception:
                error_msg += f"\nException: {result.exception}"
            raise AssertionError(error_msg)

        return RoadmapCore()

    @staticmethod
    def create_milestone(
        cli_runner: CliRunner,
        name: str,
        description: str = "",
        due_date: str | None = None,
    ) -> dict[str, Any]:
        """Create a milestone and return it.

        Args:
            cli_runner: Click CliRunner instance
            name: Milestone name
            description: Optional description
            due_date: Optional due date (YYYY-MM-DD format)

        Returns:
            Dictionary with milestone details (name, description, etc.)

        Raises:
            AssertionError: If milestone creation fails
        """
        cmd = ["milestone", "create", name]
        if description:
            cmd.extend(["--description", description])
        if due_date:
            cmd.extend(["--due-date", due_date])

        result = cli_runner.invoke(main, cmd)

        if result.exit_code != 0:
            error_msg = f"Failed to create milestone '{name}'\n"
            error_msg += f"Exit code: {result.exit_code}\n"
            error_msg += f"Output: {result.output}"
            if result.exception:
                error_msg += f"\nException: {result.exception}"
            raise AssertionError(error_msg)

        # Return milestone object from core
        core = RoadmapCore()
        try:
            return core.milestones.get(name)
        except Exception:
            # If not found immediately, return dict with known values
            return {
                "name": name,
                "description": description,
                "due_date": due_date,
            }

    @staticmethod
    def create_issue(
        cli_runner: CliRunner,
        title: str,
        description: str = "",
        priority: str | None = None,
        milestone: str | None = None,
        assignee: str | None = None,
    ) -> dict[str, Any]:
        """Create an issue and return it.

        Args:
            cli_runner: Click CliRunner instance
            title: Issue title
            description: Optional description
            priority: Optional priority (critical, high, medium, low)
            milestone: Optional milestone name
            assignee: Optional assignee

        Returns:
            Dictionary with issue details (title, priority, etc.)

        Raises:
            AssertionError: If issue creation fails
        """
        cmd = ["issue", "create", title]
        if description:
            cmd.extend(["--description", description])
        if priority:
            cmd.extend(["--priority", priority])
        if milestone:
            cmd.extend(["--milestone", milestone])
        if assignee:
            cmd.extend(["--assignee", assignee])

        result = cli_runner.invoke(main, cmd)

        if result.exit_code != 0:
            error_msg = f"Failed to create issue '{title}'\n"
            error_msg += f"Exit code: {result.exit_code}\n"
            error_msg += f"Output: {result.output}"
            if result.exception:
                error_msg += f"\nException: {result.exception}"
            raise AssertionError(error_msg)

        # Return a basic dict with what we know
        return {
            "title": title,
            "description": description,
            "priority": priority,
            "milestone": milestone,
            "assignee": assignee,
        }

    @staticmethod
    def assert_cli_success(
        result: Any, context: str = "", show_traceback: bool = True
    ) -> None:
        """Assert CLI command succeeded with detailed error context.

        If the command fails, provides comprehensive error information
        to help with debugging.

        Args:
            result: Click CliRunner result
            context: Optional context description (e.g., "Creating issue")
            show_traceback: Whether to include full traceback if exception occurred

        Raises:
            AssertionError: With detailed error information if command failed
        """
        if result.exit_code == 0:
            return

        error_msg = []
        if context:
            error_msg.append(f"❌ {context}")
        error_msg.append(f"Exit code: {result.exit_code}")
        error_msg.append(f"\n--- CLI Output ---\n{result.output}")

        if result.exception:
            import traceback

            error_msg.append("\n--- Exception ---")
            error_msg.append(f"{type(result.exception).__name__}: {result.exception}")
            if show_traceback:
                error_msg.append("\n--- Traceback ---")
                error_msg.append(
                    "".join(
                        traceback.format_exception(
                            type(result.exception),
                            result.exception,
                            result.exception.__traceback__,
                        )
                    )
                )

        raise AssertionError("\n".join(error_msg))

    @staticmethod
    def assert_exit_code(
        result: Any, expected: int, context: str = "", show_output: bool = True
    ) -> None:
        """Assert CLI exit code with optional output display.

        Args:
            result: Click CliRunner result
            expected: Expected exit code
            context: Optional context description
            show_output: Whether to include output in error message

        Raises:
            AssertionError: If exit code doesn't match
        """
        if result.exit_code == expected:
            return

        error_msg = []
        if context:
            error_msg.append(f"❌ {context}")
        error_msg.append(f"Expected exit code {expected}, got {result.exit_code}")
        if show_output:
            error_msg.append(f"Output: {result.output}")
        if result.exception:
            error_msg.append(f"Exception: {result.exception}")

        raise AssertionError("\n".join(error_msg))

    @staticmethod
    def get_roadmap_core() -> RoadmapCore:
        """Get RoadmapCore instance for the current workspace.

        Returns:
            RoadmapCore instance
        """
        return RoadmapCore()

    @staticmethod
    def roadmap_state() -> dict[str, Any]:
        """Get current state of roadmap (issues, milestones, etc.).

        Useful for verifying that CLI commands produced expected results.

        Returns:
            Dictionary with issues, milestones, and other state
        """
        core = RoadmapCore()
        return {
            "issues": core.issues.list(),
            "milestones": core.milestones.list(),
            "projects": core.projects.list(),
        }
