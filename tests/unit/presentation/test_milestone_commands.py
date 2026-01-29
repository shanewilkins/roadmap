"""Tests for milestone CLI commands."""

from pathlib import Path

import pytest

from roadmap.adapters.cli import main
from roadmap.infrastructure.coordination.core import RoadmapCore
from tests.unit.common.formatters.test_ansi_utilities import strip_ansi
from tests.unit.common.formatters.test_assertion_helpers import (
    assert_command_success,
    assert_issue_assigned_to_milestone,
    assert_issue_created,
    assert_milestone_created,
)


class TestMilestoneCreate:
    """Test milestone create command variants."""

    @pytest.mark.parametrize(
        "milestone_name,description",
        [
            ("v1.0", "First release"),
            ("v2.0", None),
        ],
    )
    def test_milestone_create_variants(self, cli_runner, milestone_name, description):
        """Test creating milestones with various options."""
        with cli_runner.isolated_filesystem():
            init_result = cli_runner.invoke(
                main, ["init", "-y", "--skip-github", "--skip-project"]
            )
            assert init_result.exit_code == 0
            args = ["milestone", "create", milestone_name]
            if description:
                args.extend(["--description", description])
            result = cli_runner.invoke(main, args)
            assert result.exit_code == 0
            assert "Created" in result.output or milestone_name in result.output

    def test_milestone_create_without_roadmap(self, cli_runner):
        """Test creating a milestone without initialized roadmap."""
        with cli_runner.isolated_filesystem():
            result = cli_runner.invoke(main, ["milestone", "create", "v1.0"])
            assert result.exit_code != 0


class TestMilestoneList:
    """Test milestone list command variants."""

    def test_milestone_list_with_milestones(self, cli_runner):
        """Test listing milestones."""
        with cli_runner.isolated_filesystem():
            init_result = cli_runner.invoke(
                main, ["init", "-y", "--skip-github", "--skip-project"]
            )
            assert init_result.exit_code == 0

            cli_runner.invoke(
                main, ["milestone", "create", "v1.0", "--description", "First release"]
            )
            cli_runner.invoke(
                main, ["milestone", "create", "v2.0", "--description", "Second release"]
            )

            result = cli_runner.invoke(main, ["milestone", "list"])
            assert result.exit_code == 0
            clean_output = strip_ansi(result.output)
            assert "v1.0" in clean_output
            assert "v2.0" in clean_output

    def test_milestone_list_empty(self, cli_runner):
        """Test listing milestones when none exist."""
        with cli_runner.isolated_filesystem():
            init_result = cli_runner.invoke(
                main, ["init", "-y", "--skip-github", "--skip-project"]
            )
            assert init_result.exit_code == 0
            result = cli_runner.invoke(main, ["milestone", "list"])
            assert result.exit_code == 0

    def test_milestone_list_without_roadmap(self, cli_runner):
        """Test listing milestones without initialized roadmap."""
        with cli_runner.isolated_filesystem():
            result = cli_runner.invoke(main, ["milestone", "list"])
            assert result.exit_code != 0


class TestMilestoneAssign:
    """Test milestone assign command variants."""

    def test_milestone_assign_success(self, cli_runner):
        """Test assigning an issue to a milestone."""
        with cli_runner.isolated_filesystem():
            init_result = cli_runner.invoke(
                main, ["init", "-y", "--skip-github", "--skip-project"]
            )
            assert init_result.exit_code == 0

            core = RoadmapCore(root_path=Path.cwd())

            cli_runner.invoke(
                main, ["milestone", "create", "v1.0", "--description", "First release"]
            )
            result = cli_runner.invoke(main, ["issue", "create", "test-issue"])

            assert_command_success(result)
            issue = assert_issue_created(core, "test-issue")
            assert_milestone_created(core, "v1.0")

            result = cli_runner.invoke(
                main, ["milestone", "assign", str(issue.id), "v1.0"]
            )
            assert_command_success(result)

            issue = core.issues.get(issue.id)
            assert issue is not None
            assert_issue_assigned_to_milestone(core, issue, "v1.0")

    def test_milestone_assign_invalid_target(self, cli_runner):
        """Test assigning to non-existent milestone or issue."""
        with cli_runner.isolated_filesystem():
            init_result = cli_runner.invoke(
                main, ["init", "-y", "--skip-github", "--skip-project"]
            )
            assert init_result.exit_code == 0

            result = cli_runner.invoke(
                main, ["milestone", "assign", "fake-id", "nonexistent"]
            )
            # Command should indicate failure - either via exit code or error message in output
            # The command may succeed (exit 0) but show error messages for individual operations
            assert (
                result.exit_code != 0
                or "failed" in result.output.lower()
                or "not found" in result.output.lower()
                or "error" in result.output.lower()
            )

    def test_milestone_assign_without_roadmap(self, cli_runner):
        """Test assigning without initialized roadmap."""
        with cli_runner.isolated_filesystem():
            result = cli_runner.invoke(main, ["milestone", "assign", "some-id", "v1.0"])
            assert result.exit_code != 0


class TestMilestoneDelete:
    """Test milestone delete command variants."""

    def test_milestone_delete_success(self, cli_runner):
        """Test deleting a milestone."""
        with cli_runner.isolated_filesystem():
            init_result = cli_runner.invoke(
                main, ["init", "-y", "--skip-github", "--skip-project"]
            )
            assert init_result.exit_code == 0

            cli_runner.invoke(
                main, ["milestone", "create", "v1.0", "--description", "First release"]
            )

            result = cli_runner.invoke(
                main, ["milestone", "delete", "v1.0"], input="y\n"
            )
            assert result.exit_code == 0
            assert "v1.0" in result.output

    def test_milestone_delete_nonexistent(self, cli_runner):
        """Test deleting a non-existent milestone."""
        with cli_runner.isolated_filesystem():
            init_result = cli_runner.invoke(
                main, ["init", "-y", "--skip-github", "--skip-project"]
            )
            assert init_result.exit_code == 0

            result = cli_runner.invoke(
                main, ["milestone", "delete", "nonexistent"], input="y\n"
            )
            assert result.exit_code == 0 or "nonexistent" in result.output

    def test_milestone_delete_without_roadmap(self, cli_runner):
        """Test deleting without initialized roadmap."""
        with cli_runner.isolated_filesystem():
            result = cli_runner.invoke(
                main, ["milestone", "delete", "v1.0"], input="y\n"
            )
            assert result.exit_code != 0
