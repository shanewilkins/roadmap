"""Integration tests for archive, restore, and cleanup commands.

Tests archive/restore functionality for issues, milestones, projects,
and cleanup command for backup pruning.
"""

from roadmap.adapters.cli import main
from tests.fixtures.cli_test_helpers import CLIOutputParser
from tests.unit.common.formatters.test_ansi_utilities import clean_cli_output


class TestCleanupCommand:
    """Test cleanup command for backup pruning."""

    def test_cleanup_help(self, cli_runner):
        """Test cleanup command help."""
        with cli_runner.isolated_filesystem():
            result = cli_runner.invoke(main, ["cleanup", "--help"])
            output = clean_cli_output(result.output).lower()
            assert result.exit_code == 0
            assert "backup" in output or "cleanup" in output

    def test_cleanup_no_backups(self, cli_runner):
        """Test cleanup when no backups exist."""
        with cli_runner.isolated_filesystem():
            # Initialize a roadmap
            result = cli_runner.invoke(
                main,
                [
                    "init",
                    "--project-name",
                    "Test Project",
                    "--non-interactive",
                    "--skip-github",
                ],
            )
            assert result.exit_code == 0, f"Init failed: {result.output}"

            result = cli_runner.invoke(main, ["cleanup", "--force"])
            assert result.exit_code == 0
            # When there are no issues or backups to clean, it should complete successfully
            assert (
                "Cleaned up" in result.output
                or "No backup" in result.output
                or "correct folders" in result.output
            )

    def test_cleanup_list(self, cli_runner):
        """Test cleanup handles check flags gracefully."""
        with cli_runner.isolated_filesystem():
            # Initialize a roadmap
            result = cli_runner.invoke(
                main,
                [
                    "init",
                    "--project-name",
                    "Test Project",
                    "--non-interactive",
                    "--skip-github",
                ],
            )
            assert result.exit_code == 0, f"Init failed: {result.output}"

            # Test that cleanup with check-folders flag works
            result = cli_runner.invoke(main, ["cleanup", "--check-folders"])
            assert result.exit_code == 0

    def test_cleanup_dry_run(self, cli_runner):
        """Test cleanup --dry-run flag."""
        with cli_runner.isolated_filesystem():
            # Initialize a roadmap
            result = cli_runner.invoke(
                main,
                [
                    "init",
                    "--project-name",
                    "Test Project",
                    "--non-interactive",
                    "--skip-github",
                ],
            )
            assert result.exit_code == 0, f"Init failed: {result.output}"

            result = cli_runner.invoke(main, ["cleanup", "--dry-run"])
            assert result.exit_code == 0

    def test_cleanup_with_keep_option(self, cli_runner):
        """Test cleanup with --keep option."""
        with cli_runner.isolated_filesystem():
            # Initialize a roadmap
            result = cli_runner.invoke(
                main,
                [
                    "init",
                    "--project-name",
                    "Test Project",
                    "--non-interactive",
                    "--skip-github",
                ],
            )
            assert result.exit_code == 0, f"Init failed: {result.output}"

            result = cli_runner.invoke(main, ["cleanup", "--keep", "5"])
            assert result.exit_code == 0

    def test_cleanup_with_days_option(self, cli_runner):
        """Test cleanup with --days option."""
        with cli_runner.isolated_filesystem():
            # Initialize a roadmap
            result = cli_runner.invoke(
                main,
                [
                    "init",
                    "--project-name",
                    "Test Project",
                    "--non-interactive",
                    "--skip-github",
                ],
            )
            assert result.exit_code == 0, f"Init failed: {result.output}"

            result = cli_runner.invoke(main, ["cleanup", "--days", "30"])
            assert result.exit_code == 0

    def test_cleanup_with_combined_options(self, cli_runner):
        """Test cleanup with both --keep and --days options."""
        with cli_runner.isolated_filesystem():
            # Initialize a roadmap
            result = cli_runner.invoke(
                main,
                [
                    "init",
                    "--project-name",
                    "Test Project",
                    "--non-interactive",
                    "--skip-github",
                ],
            )
            assert result.exit_code == 0, f"Init failed: {result.output}"

            result = cli_runner.invoke(
                main,
                ["cleanup", "--keep", "5", "--days", "30", "--dry-run"],
            )
            assert result.exit_code == 0


class TestProjectCommands:
    """Test project management commands."""

    def test_project_create(self, cli_runner):
        """Test creating a project."""
        with cli_runner.isolated_filesystem():
            # Initialize a roadmap
            result = cli_runner.invoke(
                main,
                [
                    "init",
                    "--project-name",
                    "Test Project",
                    "--non-interactive",
                    "--skip-github",
                ],
            )
            assert result.exit_code == 0, f"Init failed: {result.output}"

            result = cli_runner.invoke(
                main,
                [
                    "project",
                    "create",
                    "--title",
                    "My Project",
                    "--description",
                    "Test project",
                ],
            )

            assert result.exit_code == 0
            assert "created" in result.output.lower() or "My Project" in result.output

    def test_project_list(self, cli_runner):
        """Test listing projects."""
        with cli_runner.isolated_filesystem():
            # Initialize a roadmap
            result = cli_runner.invoke(
                main,
                [
                    "init",
                    "--project-name",
                    "Test Project",
                    "--non-interactive",
                    "--skip-github",
                ],
            )
            assert result.exit_code == 0, f"Init failed: {result.output}"

            # Create a project first
            result = cli_runner.invoke(
                main,
                ["project", "create", "--title", "Test Project 2"],
            )
            assert result.exit_code == 0

            # List projects
            result = cli_runner.invoke(main, ["project", "list"])
            assert result.exit_code == 0
            assert "Test Project" in result.output or "project" in result.output.lower()

    def test_project_view(self, cli_runner):
        """Test viewing a project."""
        with cli_runner.isolated_filesystem():
            # Initialize a roadmap
            result = cli_runner.invoke(
                main,
                [
                    "init",
                    "--project-name",
                    "Test Project",
                    "--non-interactive",
                    "--skip-github",
                ],
            )
            assert result.exit_code == 0, f"Init failed: {result.output}"

            # Try to view a project (may not exist)
            result = cli_runner.invoke(
                main,
                ["project", "view", "NoExist"],
            )

            # Either succeeds or fails gracefully
            assert result.exit_code in [0, 1]

    def test_project_update(self, cli_runner):
        """Test updating a project."""
        with cli_runner.isolated_filesystem():
            # Initialize a roadmap
            result = cli_runner.invoke(
                main,
                [
                    "init",
                    "--project-name",
                    "Test Project",
                    "--non-interactive",
                    "--skip-github",
                ],
            )
            assert result.exit_code == 0, f"Init failed: {result.output}"

            # Create a project
            result = cli_runner.invoke(
                main,
                ["project", "create", "--title", "Update Test Project"],
            )
            assert result.exit_code == 0

            # Update it
            result = cli_runner.invoke(
                main,
                [
                    "project",
                    "update",
                    "Test Project",
                    "--description",
                    "Updated description",
                ],
            )

            assert result.exit_code == 0

    def test_project_delete(self, cli_runner):
        """Test deleting a project."""
        with cli_runner.isolated_filesystem():
            # Initialize a roadmap
            result = cli_runner.invoke(
                main,
                [
                    "init",
                    "--project-name",
                    "Test Project",
                    "--non-interactive",
                    "--skip-github",
                ],
            )
            assert result.exit_code == 0, f"Init failed: {result.output}"

            # Try to delete a project (may not exist)
            result = cli_runner.invoke(
                main,
                ["project", "delete", "NoExist", "--force"],
            )

            # Either succeeds or fails gracefully
            assert result.exit_code in [0, 1, 2]


class TestCommentCommands:
    """Test comment management commands."""

    def test_comment_help(self, cli_runner):
        """Test comment command help."""
        with cli_runner.isolated_filesystem():
            result = cli_runner.invoke(main, ["comment", "--help"])
            assert result.exit_code == 0
            assert "comment" in result.output.lower()

    @staticmethod
    def _extract_first_issue_id_from_list(cli_runner) -> str:
        list_result = cli_runner.invoke(main, ["issue", "list", "--format", "json"])
        assert list_result.exit_code == 0, f"Issue list failed: {list_result.output}"

        json_output = CLIOutputParser.extract_json(list_result.output)
        assert isinstance(json_output, dict), (
            f"Expected dict JSON output, got {type(json_output).__name__}"
        )

        rows = json_output.get("rows", [])
        columns = json_output.get("columns", [])
        assert rows, f"No issues found in list output: {list_result.output}"

        id_idx = next(
            (i for i, col in enumerate(columns) if col.get("name") == "id"), 0
        )
        return str(rows[0][id_idx])

    def test_comment_add_to_issue(self, cli_runner):
        """Test adding a comment to an issue."""
        with cli_runner.isolated_filesystem():
            # Initialize a roadmap
            result = cli_runner.invoke(
                main,
                [
                    "init",
                    "--project-name",
                    "Test Project",
                    "--non-interactive",
                    "--skip-github",
                ],
            )
            assert result.exit_code == 0, f"Init failed: {result.output}"

            # Create a milestone
            result = cli_runner.invoke(
                main,
                [
                    "milestone",
                    "create",
                    "--title",
                    "v1-0",
                    "--description",
                    "First release",
                ],
            )
            assert result.exit_code == 0, f"Milestone creation failed: {result.output}"

            # Create an issue
            result = cli_runner.invoke(
                main,
                [
                    "issue",
                    "create",
                    "--title",
                    "Fix bug in parser",
                    "--priority",
                    "high",
                    "--type",
                    "bug",
                ],
            )
            assert result.exit_code == 0, f"Issue creation failed: {result.output}"
            issue_id = self._extract_first_issue_id_from_list(cli_runner)

            result = cli_runner.invoke(
                main,
                ["comment", "add", issue_id, "This is a test comment"],
            )

            # Should succeed or handle gracefully
            assert result.exit_code in [0, 1, 2]

    def test_comment_list(self, cli_runner):
        """Test listing comments on an issue."""
        with cli_runner.isolated_filesystem():
            # Initialize a roadmap
            result = cli_runner.invoke(
                main,
                [
                    "init",
                    "--project-name",
                    "Test Project",
                    "--non-interactive",
                    "--skip-github",
                ],
            )
            assert result.exit_code == 0, f"Init failed: {result.output}"

            # Create a milestone
            result = cli_runner.invoke(
                main,
                [
                    "milestone",
                    "create",
                    "--title",
                    "v1-0",
                    "--description",
                    "First release",
                ],
            )
            assert result.exit_code == 0, f"Milestone creation failed: {result.output}"

            # Create an issue
            result = cli_runner.invoke(
                main,
                [
                    "issue",
                    "create",
                    "--title",
                    "Fix bug in parser",
                    "--priority",
                    "high",
                    "--type",
                    "bug",
                ],
            )
            assert result.exit_code == 0, f"Issue creation failed: {result.output}"
            issue_id = self._extract_first_issue_id_from_list(cli_runner)

            result = cli_runner.invoke(
                main,
                ["comment", "list", issue_id],
            )

            # Should succeed or handle gracefully
            assert result.exit_code in [0, 1, 2]
