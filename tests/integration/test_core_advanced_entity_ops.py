"""Additional comprehensive tests for core roadmap functionality - targeting remaining uncovered areas."""

from datetime import datetime, timedelta
from unittest.mock import Mock, patch

import pytest

from roadmap.core.domain import (
    Priority,
)
from roadmap.infrastructure.core import RoadmapCore

pytestmark = pytest.mark.unit


class TestRoadmapCoreAdvancedIssueOperations:
    """Test advanced issue operations and filtering."""

    @pytest.fixture
    def core(self, temp_dir):
        """Create and initialize RoadmapCore for testing."""
        core = RoadmapCore(temp_dir)
        core.initialize()
        return core

    @pytest.mark.parametrize(
        "milestone_names,assign_rules,expected_unassigned_count",
        [
            (
                ["Milestone 1", "Milestone 2"],
                {
                    0: 0,
                    1: 0,
                    2: 1,
                },  # Assign issues 0,1 to milestone 0; issue 2 to milestone 1
                1,
            ),
            (
                ["Single Milestone"],
                {0: 0, 1: 0},  # Assign issues 0,1 to milestone 0
                2,
            ),
            (
                [],
                {},  # No milestones, no assignments
                4,
            ),
        ],
    )
    def test_get_issues_grouped_by_milestone(
        self, core, milestone_names, assign_rules, expected_unassigned_count
    ):
        """Test getting issues grouped by milestone with various configurations."""
        # Create milestones
        for name in milestone_names:
            core.milestones.create(name, f"Description for {name}")

        # Create issues
        created_issues = []
        issue_titles = ["Issue 1", "Issue 2", "Issue 3", "Backlog Issue"]
        priorities = [Priority.HIGH, Priority.MEDIUM, Priority.LOW, Priority.LOW]
        for title, priority in zip(issue_titles, priorities, strict=False):
            created_issues.append(core.issues.create(title=title, priority=priority))

        # Assign issues to milestones
        for issue_idx, milestone_idx in assign_rules.items():
            if milestone_idx < len(milestone_names):
                core.issues.assign_to_milestone(
                    created_issues[issue_idx].id, milestone_names[milestone_idx]
                )

        # Get grouped issues
        grouped = core.issues.get_grouped_by_milestone()

        assert "Backlog" in grouped
        assert len(grouped["Backlog"]) == expected_unassigned_count

        # Verify correct assignments if milestones exist
        if milestone_names:
            assert milestone_names[0] in grouped

    @pytest.mark.parametrize(
        "target_milestone,should_succeed",
        [
            ("Milestone 1", True),
            ("Milestone 2", True),
            (None, True),
            ("nonexistent-id", False),
        ],
    )
    def test_move_issue_to_milestone(self, core, target_milestone, should_succeed):
        """Test moving issues to different milestones."""
        # Create milestones
        core.milestones.create("Milestone 1", "Description 1")
        core.milestones.create("Milestone 2", "Description 2")

        # Create issue
        issue = core.issues.create(title="Test Issue", priority=Priority.MEDIUM)

        # Attempt to move to milestone
        result = core.issues.move_to_milestone(issue.id, target_milestone)
        assert result == should_succeed

        if should_succeed:
            updated_issue = core.issues.get(issue.id)
            assert updated_issue.milestone == target_milestone

    @pytest.mark.parametrize(
        "create_milestones,expected_result",
        [
            (
                [
                    ("Next Milestone", datetime.now() + timedelta(days=10)),
                    ("Later Milestone", datetime.now() + timedelta(days=20)),
                ],
                "Next Milestone",
            ),
            (
                [("Milestone Without Due Date", None)],
                None,
            ),
            (
                [
                    ("Milestone 1", None),
                    ("Milestone 2", None),
                ],
                None,
            ),
        ],
    )
    def test_get_next_milestone(self, core, create_milestones, expected_result):
        """Test getting the next upcoming milestone with various configurations."""
        # Create milestones
        for name, due_date in create_milestones:
            core.milestones.create(
                name=name, description=f"Description for {name}", due_date=due_date
            )

        # Get next milestone
        next_milestone = core.milestones.get_next()

        if expected_result is None:
            assert next_milestone is None
        else:
            assert next_milestone is not None
            assert next_milestone.name == expected_result


class TestRoadmapCoreTeamManagement:
    """Test team member management and assignment features."""

    @pytest.fixture
    def core(self, temp_dir):
        """Create and initialize RoadmapCore for testing."""
        core = RoadmapCore(temp_dir)
        core.initialize()
        return core

    def test_get_team_members(self, core):
        """Test getting team members from GitHub API."""
        # Mock GitHub client since get_team_members calls GitHub API
        with patch(
            "roadmap.core.services.github_integration_service.GitHubClient"
        ) as mock_github_client:
            mock_client = Mock()
            mock_client.get_team_members.return_value = [
                "alice@example.com",
                "bob@example.com",
            ]
            mock_github_client.return_value = mock_client

            # Mock GitHub config in the service
            with patch.object(core.github_service, "get_github_config") as mock_config:
                mock_config.return_value = ("token", "owner", "repo")

                team_members = core.team.get_members()

                # Should return team members from GitHub API
                assert len(team_members) == 2
                assert "alice@example.com" in team_members
                assert "bob@example.com" in team_members

    def test_get_team_members_empty(self, core):
        """Test getting team members when no issues have assignees."""
        # Create issues without assignees
        core.issues.create(title="Issue 1", priority=Priority.HIGH)
        core.issues.create(title="Issue 2", priority=Priority.MEDIUM)

        team_members = core.team.get_members()
        assert len(team_members) == 0

    @pytest.mark.parametrize(
        "mock_config_setup,expected_user",
        [
            ("success", "test_user"),
            ("config_not_found", None),
            ("api_error", None),
        ],
    )
    def test_get_current_user(self, core, mock_config_setup, expected_user):
        """Test getting current user from GitHub with various scenarios."""
        if mock_config_setup == "success":
            mock_config = Mock()
            mock_user = Mock()
            mock_user.name = "test_user"
            mock_config.user = mock_user

            with patch(
                "roadmap.core.services.github_integration_service.ConfigManager"
            ) as mock_cm_class:
                mock_cm_instance = Mock()
                mock_cm_instance.load.return_value = mock_config
                mock_cm_class.return_value = mock_cm_instance

                current_user = core.team.get_current_user()
                assert current_user == expected_user

        elif mock_config_setup == "config_not_found":
            with patch(
                "roadmap.core.services.github_integration_service.ConfigManager"
            ) as mock_cm_class:
                mock_cm_class.side_effect = Exception("Config not found")
                current_user = core.team.get_current_user()
                assert current_user == expected_user

        elif mock_config_setup == "api_error":
            with patch.object(core.github_service, "get_current_user") as mock_get_user:
                mock_get_user.return_value = None
                current_user = core.team.get_current_user()
                assert current_user == expected_user

    @pytest.mark.parametrize(
        "assignee,expected_count",
        [
            ("alice@example.com", 2),
            ("bob@example.com", 1),
            ("unassigned@example.com", 0),
        ],
    )
    def test_get_assigned_issues(self, core, assignee, expected_count):
        """Test getting issues assigned to specific users."""
        # Create issues with different assignees
        core.issues.create(
            title="Alice Issue 1", priority=Priority.HIGH, assignee="alice@example.com"
        )
        core.issues.create(
            title="Bob Issue", priority=Priority.MEDIUM, assignee="bob@example.com"
        )
        core.issues.create(
            title="Alice Issue 2", priority=Priority.LOW, assignee="alice@example.com"
        )

        assigned_issues = core.team.get_assigned_issues(assignee)
        assert len(assigned_issues) == expected_count

        if expected_count > 0:
            for issue in assigned_issues:
                assert issue.assignee == assignee

    @patch("roadmap.infrastructure.user_operations.UserOperations.get_current_user")
    def test_get_my_issues(self, mock_current_user, core):
        """Test getting issues assigned to current user."""
        mock_current_user.return_value = "alice@example.com"

        # Create issues
        core.issues.create(
            title="My Issue 1", priority=Priority.HIGH, assignee="alice@example.com"
        )
        core.issues.create(
            title="Someone Else's Issue",
            priority=Priority.MEDIUM,
            assignee="bob@example.com",
        )
        core.issues.create(
            title="My Issue 2", priority=Priority.LOW, assignee="alice@example.com"
        )

        my_issues = core.team.get_my_issues()
        assert len(my_issues) == 2
        my_titles = [issue.title for issue in my_issues]
        assert "My Issue 1" in my_titles
        assert "My Issue 2" in my_titles

    @patch("roadmap.infrastructure.team_coordinator.TeamCoordinator.get_current_user")
    def test_get_my_issues_no_current_user(self, mock_current_user, core):
        """Test getting my issues when current user is unknown."""
        mock_current_user.return_value = None

        # Create issues
        core.issues.create(
            title="Some Issue", priority=Priority.HIGH, assignee="alice@example.com"
        )

        my_issues = core.team.get_my_issues()
        assert len(my_issues) == 0

    def test_get_all_assigned_issues(self, core):
        """Test getting all issues grouped by assignee."""
        # Create issues with different assignees
        core.issues.create(
            title="Alice Issue 1", priority=Priority.HIGH, assignee="alice@example.com"
        )
        core.issues.create(
            title="Bob Issue", priority=Priority.MEDIUM, assignee="bob@example.com"
        )
        core.issues.create(
            title="Alice Issue 2", priority=Priority.LOW, assignee="alice@example.com"
        )
        core.issues.create(
            title="Unassigned Issue",
            priority=Priority.LOW,
            # No assignee
        )

        all_assigned = core.team.get_all_assigned_issues()

        assert "alice@example.com" in all_assigned
        assert "bob@example.com" in all_assigned

        assert len(all_assigned["alice@example.com"]) == 2
        assert len(all_assigned["bob@example.com"]) == 1

        # Unassigned issues should not appear in results
        assert "Unassigned Issue" not in [
            issue.title
            for assignee_issues in all_assigned.values()
            for issue in assignee_issues
        ]
