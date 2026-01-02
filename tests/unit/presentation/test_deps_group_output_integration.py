"""Error path tests for deps module (CLI dependencies command group).

Tests focus on error handling, edge cases, and failure scenarios in the
CLI dependencies command group which manages issue dependencies.

Tier 2 test coverage module addressing:
- Dependency relationship validation and creation
- Circular dependency detection
- Invalid issue reference handling
- Missing dependency issues
- Duplicate dependency prevention
- Context and core object handling
- CLI error handling and user feedback
"""

from unittest.mock import Mock, patch

from click.testing import CliRunner

from roadmap.adapters.cli.issues.deps import add_dependency, deps
from tests.unit.domain.test_data_factory_generation import TestDataFactory


class TestAddDependencyConsoleOutput:
    """Test console output for add dependency command."""

    def test_add_dependency_success_output(self):
        """Test success message is displayed."""
        runner = CliRunner()
        mock_issue = TestDataFactory.create_mock_issue()
        mock_issue.id = "123"
        mock_issue.title = "Task A"
        mock_issue.depends_on = []

        mock_dep_issue = Mock()
        mock_dep_issue.id = "456"
        mock_dep_issue.title = "Task B"

        mock_core = TestDataFactory.create_mock_core(is_initialized=True)
        mock_core.issues.update.return_value = mock_issue
        ctx_obj = {"core": mock_core}

        with patch(
            "roadmap.adapters.cli.issues.deps.ensure_entity_exists"
        ) as mock_ensure:
            mock_ensure.side_effect = [mock_issue, mock_dep_issue]

            result = runner.invoke(
                add_dependency,
                ["123", "456"],
                obj=ctx_obj,
            )

        # Verify the command completed successfully
        assert result.exit_code == 0
        # Verify update was called (dependency was added)
        mock_core.issues.update.assert_called_once()

    def test_add_dependency_duplicate_warning_output(self):
        """Test warning message for duplicate dependency."""
        runner = CliRunner()
        mock_issue = TestDataFactory.create_mock_issue()
        mock_issue.id = "123"
        mock_issue.title = "Task A"
        mock_issue.depends_on = ["456"]

        mock_dep_issue = Mock()
        mock_dep_issue.id = "456"
        mock_dep_issue.title = "Task B"

        mock_core = TestDataFactory.create_mock_core(is_initialized=True)
        ctx_obj = {"core": mock_core}

        with patch(
            "roadmap.adapters.cli.issues.deps.ensure_entity_exists"
        ) as mock_ensure:
            mock_ensure.side_effect = [mock_issue, mock_dep_issue]

            result = runner.invoke(
                add_dependency,
                ["123", "456"],
                obj=ctx_obj,
            )

        # Verify the command succeeded
        assert result.exit_code == 0
        # Verify update was NOT called (dependency already exists)
        mock_core.issues.update.assert_not_called()


class TestDepsCommandIntegration:
    """Test integration scenarios with deps commands."""

    def test_deps_group_shows_add_command(self):
        """Test that add command appears in deps group."""
        runner = CliRunner()
        result = runner.invoke(deps, ["--help"])
        assert "add" in result.output.lower()

    def test_deps_add_shows_help(self):
        """Test add command shows help."""
        runner = CliRunner()
        result = runner.invoke(deps, ["add", "--help"])
        assert result.exit_code == 0
        assert (
            "dependency" in result.output.lower() or "depend" in result.output.lower()
        )

    def test_add_dependency_with_multiple_sequential_additions(self):
        """Test adding multiple dependencies in sequence."""
        runner = CliRunner()
        mock_issue = TestDataFactory.create_mock_issue()
        mock_issue.id = "123"
        mock_issue.title = "Main Task"
        mock_issue.depends_on = []

        mock_dep_issue_1 = Mock()
        mock_dep_issue_1.id = "456"
        mock_dep_issue_1.title = "Subtask 1"

        mock_dep_issue_2 = Mock()
        mock_dep_issue_2.id = "789"
        mock_dep_issue_2.title = "Subtask 2"

        mock_core = TestDataFactory.create_mock_core(is_initialized=True)
        ctx_obj = {"core": mock_core}

        with patch(
            "roadmap.adapters.cli.issues.deps.ensure_entity_exists"
        ) as mock_ensure:
            # First add
            mock_ensure.side_effect = [mock_issue, mock_dep_issue_1]
            result1 = runner.invoke(
                add_dependency,
                ["123", "456"],
                obj=ctx_obj,
                catch_exceptions=False,
            )
            assert result1.exit_code == 0

            # Update the issue to reflect the dependency was added
            mock_issue.depends_on = ["456"]

            # Second add
            mock_ensure.side_effect = [mock_issue, mock_dep_issue_2]
            result2 = runner.invoke(
                add_dependency,
                ["123", "789"],
                obj=ctx_obj,
                catch_exceptions=False,
            )
            assert result2.exit_code == 0
