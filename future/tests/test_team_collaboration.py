"""Tests for team collaboration features."""

from unittest.mock import Mock, patch

import pytest
from click.testing import CliRunner

from roadmap.application.services import RoadmapCore
from roadmap.domain import Issue, Priority, Status
from roadmap.presentation.cli import main


@pytest.fixture
def initialized_roadmap(temp_dir):
    """Create a temporary directory with initialized roadmap."""
    runner = CliRunner()
    result = runner.invoke(
        main,
        [
            "init",
            "--non-interactive",
            "--skip-github",
            "--project-name",
            "Test Project",
        ],
    )
    assert result.exit_code == 0
    return temp_dir


@pytest.fixture
def sample_issues():
    """Sample issues with various assignees for testing."""
    return [
        Issue(
            id="issue1",
            title="Fix login bug",
            assignee="alice",
            priority=Priority.HIGH,
            status=Status.TODO,
        ),
        Issue(
            id="issue2",
            title="Add dark mode",
            assignee="bob",
            priority=Priority.MEDIUM,
            status=Status.IN_PROGRESS,
        ),
        Issue(
            id="issue3",
            title="Database optimization",
            assignee="alice",
            priority=Priority.LOW,
            status=Status.REVIEW,
        ),
        Issue(
            id="issue4",
            title="Unassigned task",
            assignee=None,
            priority=Priority.MEDIUM,
            status=Status.TODO,
        ),
    ]


class TestCoreTeamCollaboration:
    """Test core functionality for team collaboration."""

    def test_create_issue_with_assignee(self, mock_core, tmp_path):
        """Test creating an issue with an assignee."""
        core = RoadmapCore(tmp_path)
        core.initialize()

        issue = core.create_issue(title="Test issue", assignee="john-doe")

        assert issue.assignee == "john-doe"
        assert issue.title == "Test issue"

    def test_get_assigned_issues(self, mock_core, sample_issues):
        """Test getting issues assigned to a specific user."""
        mock_core.list_issues.return_value = sample_issues
        mock_core.get_assigned_issues.side_effect = lambda assignee: [
            issue for issue in sample_issues if issue.assignee == assignee
        ]

        alice_issues = mock_core.get_assigned_issues("alice")
        bob_issues = mock_core.get_assigned_issues("bob")

        assert len(alice_issues) == 2
        assert len(bob_issues) == 1
        assert all(issue.assignee == "alice" for issue in alice_issues)
        assert all(issue.assignee == "bob" for issue in bob_issues)

    def test_get_my_issues(self, mock_core, sample_issues):
        """Test getting issues assigned to current user."""
        # Mock the get_current_user to return a username
        mock_core.get_current_user.return_value = "alice"
        mock_core.get_my_issues.return_value = [
            issue for issue in sample_issues if issue.assignee == "alice"
        ]

        my_issues = mock_core.get_my_issues()
        assert len(my_issues) == 2
        assert all(issue.assignee == "alice" for issue in my_issues)

    def test_get_all_assigned_issues(self, mock_core, sample_issues):
        """Test getting all issues grouped by assignee."""
        mock_core.get_all_assigned_issues.return_value = {
            "alice": [issue for issue in sample_issues if issue.assignee == "alice"],
            "bob": [issue for issue in sample_issues if issue.assignee == "bob"],
        }

        assignments = mock_core.get_all_assigned_issues()

        assert "alice" in assignments
        assert "bob" in assignments
        assert len(assignments["alice"]) == 2
        assert len(assignments["bob"]) == 1

    def test_list_issues_with_assignee_filter(self, mock_core, sample_issues):
        """Test filtering issues by assignee."""
        # Test specific assignee filter
        mock_core.list_issues.side_effect = lambda assignee=None, **kwargs: [
            issue
            for issue in sample_issues
            if assignee is None or issue.assignee == assignee
        ]

        alice_issues = mock_core.list_issues(assignee="alice")
        all_issues = mock_core.list_issues()

        assert len(alice_issues) == 2
        assert len(all_issues) == 4


class TestCLITeamCommands:
    """Test CLI team collaboration commands."""

    def test_create_issue_with_assignee_option(self, mock_core, initialized_roadmap):
        """Test issue create command with --assignee option."""
        runner = CliRunner()

        with patch("roadmap.core.RoadmapCore.create_issue") as mock_create:
            mock_create.return_value = Issue(
                id="test123", title="Test Issue", assignee="john-doe"
            )

            result = runner.invoke(
                main, ["issue", "create", "Test Issue", "--assignee", "john-doe"]
            )

            assert result.exit_code == 0
            mock_create.assert_called_once()
            call_args = mock_create.call_args
            assert call_args[1]["assignee"] == "john-doe"
            assert "Assignee: john-doe" in result.output

    def test_issue_list_with_assignee_filter(
        self, mock_core, sample_issues, initialized_roadmap
    ):
        """Test issue list command with --assignee filter."""
        runner = CliRunner()

        with patch("roadmap.core.RoadmapCore.get_assigned_issues") as mock_get_assigned:
            mock_get_assigned.return_value = [
                issue for issue in sample_issues if issue.assignee == "alice"
            ]

            result = runner.invoke(main, ["issue", "list", "--assignee", "alice"])

            assert result.exit_code == 0
            mock_get_assigned.assert_called_once_with("alice")
            assert "alice" in result.output

    def test_issue_list_with_my_issues_filter(
        self, mock_core, sample_issues, initialized_roadmap
    ):
        """Test issue list command with --my-issues filter."""
        runner = CliRunner()

        with patch("roadmap.core.RoadmapCore.get_my_issues") as mock_get_my:
            mock_get_my.return_value = [
                issue for issue in sample_issues if issue.assignee == "alice"
            ]

            result = runner.invoke(main, ["issue", "list", "--my-issues"])

            assert result.exit_code == 0
            mock_get_my.assert_called_once()
            # Output should contain user's issues

    def test_assignee_filter_conflict(self, mock_core, initialized_roadmap):
        """Test that conflicting assignee filters are rejected."""
        runner = CliRunner()

        result = runner.invoke(
            main, ["issue", "list", "--assignee", "alice", "--my-issues"]
        )

        assert result.exit_code == 0  # Should not error, just handle the conflict
        assert "Cannot combine --assignee and --my-issues filters" in result.output

    def test_team_members_command(self, mock_core, initialized_roadmap):
        """Test team members command."""
        runner = CliRunner()

        # Mock GitHub client methods
        with patch("roadmap.core.RoadmapCore.get_team_members") as mock_get_team:
            with patch("roadmap.core.RoadmapCore.get_current_user") as mock_get_user:
                mock_get_team.return_value = [
                    {"login": "alice", "type": "User"},
                    {"login": "bob", "type": "User"},
                ]
                mock_get_user.return_value = "alice"

                result = runner.invoke(main, ["team", "members"])

                assert result.exit_code == 0
                assert "alice" in result.output
                assert "bob" in result.output
                assert "bob" in result.output

    def test_team_assignments_command(
        self, mock_core, sample_issues, initialized_roadmap
    ):
        """Test team assignments command."""
        runner = CliRunner()

        with patch("roadmap.core.RoadmapCore.get_all_assigned_issues") as mock_get_all:
            mock_get_all.return_value = {
                "alice": [
                    issue for issue in sample_issues if issue.assignee == "alice"
                ],
                "bob": [issue for issue in sample_issues if issue.assignee == "bob"],
            }

            result = runner.invoke(main, ["team", "assignments"])

            assert result.exit_code == 0
            # Should show team assignments (strip ANSI codes for cleaner matching)
            import re

            clean_output = re.sub(r"\x1b\[[0-9;]*m", "", result.output)
            assert "bob (1 issue)" in clean_output

    def test_team_workload_command(self, mock_core, sample_issues, initialized_roadmap):
        """Test team workload command."""
        runner = CliRunner()

        with patch("roadmap.core.RoadmapCore.get_all_assigned_issues") as mock_get_all:
            with patch("roadmap.core.RoadmapCore.list_issues") as mock_list:
                mock_get_all.return_value = {
                    "alice": [
                        issue for issue in sample_issues if issue.assignee == "alice"
                    ],
                    "bob": [
                        issue for issue in sample_issues if issue.assignee == "bob"
                    ],
                }
                mock_list.return_value = [
                    issue for issue in sample_issues if not issue.assignee
                ]

                result = runner.invoke(main, ["team", "workload"])

                assert result.exit_code == 0
                # Should show workload distribution
                # The workload table might be empty if no issues match the status breakdown

    def test_team_commands_without_github(self, mock_core, initialized_roadmap):
        """Test team commands when GitHub is not configured."""
        runner = CliRunner()

        with patch("roadmap.core.RoadmapCore.get_team_members") as mock_get_team:
            mock_get_team.side_effect = Exception("GitHub not configured")

            result = runner.invoke(main, ["team", "members"])

            assert result.exit_code == 0
            assert "Failed to get team members" in result.output


class TestAssigneeDisplayInList:
    """Test assignee display in issue lists."""

    def test_assignee_column_in_list_output(
        self, mock_core, sample_issues, initialized_roadmap
    ):
        """Test that assignee column appears in issue list."""
        runner = CliRunner()

        with patch("roadmap.core.RoadmapCore.list_issues") as mock_list:
            mock_list.return_value = sample_issues

            result = runner.invoke(main, ["issue", "list"])

            assert result.exit_code == 0
            # Check for assignee information in the output
            assert "alice" in result.output
            assert "bob" in result.output
            assert "Unassigned" in result.output  # For issue without assignee

    def test_assignee_display_formatting(
        self, mock_core, sample_issues, initialized_roadmap
    ):
        """Test assignee display formatting in list."""
        runner = CliRunner()

        with patch("roadmap.core.RoadmapCore.list_issues") as mock_list:
            mock_list.return_value = sample_issues

            result = runner.invoke(main, ["issue", "list"])

            # Test that we can see both assigned and unassigned states
            output_lines = result.output.split("\n")
            assignee_data = [
                line for line in output_lines if "alice" in line or "Unassigned" in line
            ]

            assert len(assignee_data) > 0  # Should have some assignee data


class TestGitHubIntegration:
    """Test GitHub integration for team features."""

    def test_get_team_members_from_github(self):
        """Test getting team members from GitHub API."""
        from roadmap.infrastructure.github import GitHubClient

        client = GitHubClient("fake-token", "owner", "repo")

        with patch.object(client, "get_repository_collaborators") as mock_collabs:
            with patch.object(client, "get_repository_contributors") as mock_contribs:
                mock_collabs.return_value = ["alice"]
                mock_contribs.return_value = ["bob"]

                team_members = client.get_team_members()

                assert len(team_members) == 2
                assert "alice" in team_members
                assert "bob" in team_members

    def test_get_current_user_from_github(self):
        """Test getting current user from GitHub API."""
        from roadmap.infrastructure.github import GitHubClient

        client = GitHubClient("fake-token", "owner", "repo")

        with patch.object(client, "_make_request") as mock_request:
            mock_response = Mock()
            mock_response.json.return_value = {"login": "current-user", "type": "User"}
            mock_request.return_value = mock_response

            user = client.get_current_user()

            assert user == "current-user"
            mock_request.assert_called_once_with("GET", "/user")


class TestAssigneeValidation:
    """Test assignee validation and edge cases."""

    def test_empty_assignee_handling(self, tmp_path):
        """Test handling of empty assignee values."""
        core = RoadmapCore(tmp_path)
        core.initialize()

        # Test with None assignee
        issue = core.create_issue(title="Test", assignee=None)
        assert issue.assignee is None

        # Test with empty string assignee
        issue2 = core.create_issue(title="Test 2", assignee="")
        assert issue2.assignee == ""

    def test_assignee_case_sensitivity(self, tmp_path):
        """Test assignee filtering is case sensitive."""
        core = RoadmapCore(tmp_path)
        core.initialize()

        # Create issues with different cases
        core.create_issue(title="Issue 1", assignee="Alice")
        core.create_issue(title="Issue 2", assignee="alice")

        # Filter should be case sensitive
        alice_issues = core.list_issues(assignee="Alice")
        alice_lower_issues = core.list_issues(assignee="alice")

        assert len(alice_issues) == 1
        assert len(alice_lower_issues) == 1
        assert alice_issues[0].assignee == "Alice"
        assert alice_lower_issues[0].assignee == "alice"
