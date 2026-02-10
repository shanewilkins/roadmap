"""Integration test helpers for common patterns.

Provides utilities for initializing roadmap, creating test data,
and asserting on CLI commands in a robust way.
"""

from typing import Any

from click.testing import CliRunner

from roadmap.adapters.cli import main
from roadmap.infrastructure.coordination.core import RoadmapCore


class IntegrationTestBase:
    """Base utilities for integration tests.

    Provides common patterns and assertion helpers to reduce boilerplate
    and improve test robustness.
    """

    _open_cores: list[RoadmapCore] = []

    @classmethod
    def _register_core(cls, core: RoadmapCore) -> RoadmapCore:
        cls._open_cores.append(core)
        return core

    @classmethod
    def close_open_cores(cls) -> None:
        while cls._open_cores:
            core = cls._open_cores.pop()
            try:
                core.close()
            except Exception:
                pass

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

        return IntegrationTestBase._register_core(RoadmapCore())

    @staticmethod
    def create_milestone(
        cli_runner: CliRunner,
        name: str,
        headline: str = "",
        due_date: str | None = None,
    ) -> dict[str, Any]:
        """Create a milestone and return it.

        Args:
            cli_runner: Click CliRunner instance
            name: Milestone name
            headline: Optional headline
            due_date: Optional due date (YYYY-MM-DD format)

        Returns:
            Dictionary with milestone details (name, headline, etc.)

        Raises:
            AssertionError: If milestone creation fails
        """
        cmd = ["milestone", "create", "--title", name]
        if headline:
            cmd.extend(["--description", headline])
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
        core = IntegrationTestBase._register_core(RoadmapCore())
        try:
            milestone = core.milestones.get(name)
            if milestone is not None:
                return {
                    "name": milestone.name,
                    "headline": milestone.headline,
                    "due_date": str(milestone.due_date) if milestone.due_date else None,
                }
        except Exception:
            pass
        finally:
            core.close()

        # If not found immediately, return dict with known values
        return {
            "name": name,
            "headline": headline,
            "due_date": due_date,
        }

    @staticmethod
    def create_issue(
        cli_runner: CliRunner,
        title: str,
        description: str = "",
        issue_type: str | None = None,
        priority: str | None = None,
        labels: str | None = None,
        estimate: float | None = None,
        depends_on: list[str] | None = None,
        blocks: list[str] | None = None,
        milestone: str | None = None,
        assignee: str | None = None,
    ) -> dict[str, Any]:
        """Create an issue and return it.

        Args:
            cli_runner: Click CliRunner instance
            title: Issue title
            description: Optional description
            issue_type: Optional issue type (feature, bug, other)
            priority: Optional priority (critical, high, medium, low)
            labels: Optional labels (comma-separated)
            estimate: Optional estimated hours
            depends_on: Optional list of issue IDs this depends on
            blocks: Optional list of issue IDs this blocks
            milestone: Optional milestone name
            assignee: Optional assignee

        Returns:
            Dictionary with issue details (title, priority, etc.)

        Raises:
            AssertionError: If issue creation fails
        """
        cmd = ["issue", "create", "--title", title]
        if description:
            cmd.extend(["--content", description])
        if issue_type:
            cmd.extend(["--type", issue_type])
        if priority:
            cmd.extend(["--priority", priority])
        if labels:
            cmd.extend(["--labels", labels])
        if estimate is not None:
            cmd.extend(["--estimate", str(estimate)])
        if depends_on:
            for dep_id in depends_on:
                cmd.extend(["--depends-on", dep_id])
        if blocks:
            for block_id in blocks:
                cmd.extend(["--blocks", block_id])
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
            "issue_type": issue_type,
            "priority": priority,
            "labels": labels,
            "estimate": estimate,
            "depends_on": depends_on,
            "blocks": blocks,
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
        return IntegrationTestBase._register_core(RoadmapCore())

    @staticmethod
    def roadmap_state() -> dict[str, Any]:
        """Get current state of roadmap (issues, milestones, etc.).

        Useful for verifying that CLI commands produced expected results.

        Returns:
            Dictionary with issues, milestones, and other state
        """
        core = IntegrationTestBase._register_core(RoadmapCore())
        try:
            return {
                "issues": core.issues.list(),
                "milestones": core.milestones.list(),
                "projects": core.projects.list(),
            }
        finally:
            core.close()
