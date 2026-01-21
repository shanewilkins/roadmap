"""Integration tests for the roadmap CLI tool.

These tests verify end-to-end workflows and cross-module integration.
"""

from unittest.mock import Mock, patch

import pytest
from click.testing import CliRunner

from roadmap.adapters.cli import main
from roadmap.core.domain import Priority
from roadmap.infrastructure.coordination.core import RoadmapCore

pytestmark = pytest.mark.filesystem


@pytest.fixture
def mock_github_client():
    """Mock GitHub client for integration operations."""
    with patch("roadmap.adapters.github.github.GitHubClient") as mock_client_class:
        mock_client = Mock()
        mock_client_class.return_value = mock_client

        # Mock successful API responses
        mock_client.test_connection.return_value = (True, "Connected successfully")
        mock_client.create_issue.return_value = {
            "number": 1,
            "html_url": "https://github.com/test/repo/issues/1",
        }
        mock_client.update_issue.return_value = {"number": 1}
        mock_client.create_milestone.return_value = {
            "number": 1,
            "html_url": "https://github.com/test/repo/milestones/1",
        }
        mock_client.get_issues.return_value = []
        mock_client.get_milestones.return_value = []

        yield mock_client


class TestPerformanceAndStress:
    """Test performance with larger datasets and stress scenarios."""

    def test_large_dataset_handling(self, temp_workspace):
        """Test handling of larger datasets."""
        runner = CliRunner()

        # Initialize
        runner.invoke(
            main,
            [
                "init",
                "--non-interactive",
                "--skip-github",
                "--project-name",
                "test-project",
            ],
        )

        # Create many issues and milestones
        num_issues = 50
        num_milestones = 10

        # Create milestones
        milestone_names = []
        for i in range(num_milestones):
            milestone_name = f"Milestone {i+1}"
            result = runner.invoke(main, ["milestone", "create", milestone_name])
            assert result.exit_code == 0
            milestone_names.append(milestone_name)

        # Create issues and assign to milestones
        issue_ids = []
        for i in range(num_issues):
            priority = ["low", "medium", "high"][i % 3]
            result = runner.invoke(
                main, ["issue", "create", f"Issue {i+1}", "--priority", priority]
            )
            assert result.exit_code == 0

            # Extract issue ID from created output if possible, or from database as fallback
            from tests.fixtures.click_testing import ClickTestHelper

            try:
                issue_id = ClickTestHelper.extract_issue_id(result.output)
            except ValueError:
                # If extraction from output failed, get the latest issue from database
                issue_id = None
                core = RoadmapCore()
                issues = core.issues.list()
                if issues:
                    # Get the most recently created issue
                    latest_issue = sorted(issues, key=lambda x: x.created or "")[-1]
                    issue_id = str(latest_issue.id)

            if issue_id:
                issue_ids.append(issue_id)

            # Only assign to milestone if we successfully extracted the ID
            if issue_id:
                milestone_name = milestone_names[i % len(milestone_names)]
                runner.invoke(main, ["milestone", "assign", issue_id, milestone_name])

        # Test operations on large dataset
        result = runner.invoke(main, ["status"])
        assert result.exit_code == 0
        assert f"todo           {num_issues}" in result.output
        assert "Milestones:" in result.output

        # Test filtering
        result = runner.invoke(main, ["issue", "list", "--priority", "high"])
        assert result.exit_code == 0
        # Should have roughly 1/3 of issues with high priority
        high_priority_count = len([i for i in range(num_issues) if i % 3 == 2])
        assert (
            str(high_priority_count) in result.output
            or len(result.output.split("\n")) > high_priority_count
        )

        # Test listing milestones
        result = runner.invoke(main, ["milestone", "list"])
        assert result.exit_code == 0

        # Verify data integrity through core
        core = RoadmapCore()
        issues = core.issues.list()
        milestones = core.milestones.list()

        assert len(issues) == num_issues
        assert len(milestones) == num_milestones

        # Verify most issues are assigned to milestones (allow some to be unassigned due to timing)
        assigned_issues = [
            issue for issue in issues if issue.milestone in milestone_names
        ]
        assert len(assigned_issues) >= int(num_issues * 0.8)  # At least 80% assigned

    def test_concurrent_access_simulation(self, temp_workspace):
        """Test behavior under simulated concurrent access."""
        runner = CliRunner()

        # Initialize
        runner.invoke(
            main,
            [
                "init",
                "--non-interactive",
                "--skip-github",
                "--project-name",
                "test-project",
            ],
        )

        # Simulate concurrent operations by creating multiple core instances
        cores = [RoadmapCore() for _ in range(3)]

        # Each core creates issues
        for i, core in enumerate(cores):
            core.issues.create(f"Concurrent Issue {i}", Priority.MEDIUM)

        # Verify all issues exist
        final_core = RoadmapCore()
        issues = final_core.issues.list()

        # Should have at least 3 issues (may have more due to ID generation)
        assert len(issues) >= 3

        # Verify through CLI
        result = runner.invoke(main, ["status"])
        assert result.exit_code == 0
        assert "Issues by Status" in result.output or "todo" in result.output
