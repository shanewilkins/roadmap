"""Comprehensive integration tests for RoadmapCore entity operations.

Tests cover:
- Advanced entity operations (milestones, issues, dependencies)
- Complex filtering and querying scenarios
- Bulk operations and performance
- Multi-milestone and cross-entity workflows
"""

import os
from datetime import datetime, timedelta
from unittest.mock import Mock, patch

import pytest

from roadmap.core.domain import (
    MilestoneStatus,
    Priority,
    Status,
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
            core.milestones.create(name, headline=f"Description for {name}")

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
        core.milestones.create("Milestone 1", headline="Description 1")
        core.milestones.create("Milestone 2", headline="Description 2")

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
                name=name, headline=f"Description for {name}", due_date=due_date
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


class TestRoadmapCoreFindExisting:
    """Test find_existing_roadmap class method and directory discovery."""

    def test_find_existing_roadmap_success(self, temp_dir):
        """Test finding existing roadmap in directory."""
        # Create and initialize a roadmap
        core = RoadmapCore(temp_dir)
        core.initialize()

        # Now find it using the class method
        found_core = RoadmapCore.find_existing_roadmap(temp_dir)
        assert found_core is not None
        assert found_core.root_path == temp_dir
        assert found_core.is_initialized()

    def test_find_existing_roadmap_not_found(self, temp_dir):
        """Test finding roadmap when none exists."""
        result = RoadmapCore.find_existing_roadmap(temp_dir)
        assert result is None

    def test_find_existing_roadmap_current_directory(self, temp_dir):
        """Test finding roadmap in current directory."""
        # Change to temp directory
        original_cwd = os.getcwd()
        try:
            os.chdir(temp_dir)

            # Create roadmap in current directory
            core = RoadmapCore(temp_dir)
            core.initialize()

            # Find without specifying path
            found_core = RoadmapCore.find_existing_roadmap()
            assert found_core is not None
            assert found_core.is_initialized()
        finally:
            os.chdir(original_cwd)

    def test_find_existing_roadmap_alternative_names(self, temp_dir):
        """Test finding roadmap with alternative directory names."""
        # Create roadmap with custom name
        custom_name = "my-roadmap"
        core = RoadmapCore(temp_dir, roadmap_dir_name=custom_name)
        core.initialize()

        # Should find it by searching all directories
        found_core = RoadmapCore.find_existing_roadmap(temp_dir)
        assert found_core is not None
        assert found_core.roadmap_dir_name == custom_name

    def test_find_existing_roadmap_multiple_candidates(self, temp_dir):
        """Test finding roadmap when multiple directories exist."""
        # Create some non-roadmap directories
        (temp_dir / "other_dir").mkdir()
        (temp_dir / "another_dir").mkdir()

        # Create actual roadmap
        core = RoadmapCore(temp_dir)
        core.initialize()

        # Should find the real roadmap
        found_core = RoadmapCore.find_existing_roadmap(temp_dir)
        assert found_core is not None
        assert found_core.roadmap_dir_name == ".roadmap"


class TestRoadmapCoreMilestoneOperations:
    """Test milestone creation, updates, and management."""

    @pytest.fixture
    def core(self, temp_dir):
        """Create and initialize RoadmapCore for testing."""
        core = RoadmapCore(temp_dir)
        core.initialize()
        return core

    def test_update_milestone_success(self, core):
        """Test successful milestone update."""
        # Create milestone first
        milestone = core.milestones.create(
            name="Test Milestone",
            headline="Original description",
            due_date=datetime.now() + timedelta(days=30),
        )
        assert milestone is not None

        # Update milestone
        result = core.milestones.update(
            name="Test Milestone",
            headline="Updated description",
            status=MilestoneStatus.OPEN,
        )
        assert result is True

        # Verify updates
        updated_milestone = core.milestones.get("Test Milestone")
        assert updated_milestone.headline == "Updated description"
        assert updated_milestone.status == MilestoneStatus.OPEN

    def test_update_milestone_clear_due_date(self, core):
        """Test clearing due date from milestone."""
        # Create milestone with due date
        milestone = core.milestones.create(
            name="Test Milestone",
            headline="Description",
            due_date=datetime.now() + timedelta(days=30),
        )
        assert milestone.due_date is not None

        # Clear due date
        result = core.milestones.update(name="Test Milestone", clear_due_date=True)
        assert result is True

        # Verify due date is cleared
        updated_milestone = core.milestones.get("Test Milestone")
        assert updated_milestone.due_date is None

    def test_update_milestone_nonexistent(self, core):
        """Test updating nonexistent milestone."""
        result = core.milestones.update(
            name="Nonexistent Milestone", headline="New description"
        )
        assert result is False

    def test_update_milestone_not_initialized(self, temp_dir):
        """Test updating milestone on uninitialized roadmap."""
        core = RoadmapCore(temp_dir)  # Not explicitly initialized

        # Updating on uninitialized core returns False (milestone not found)
        result = core.milestones.update(name="Test Milestone", headline="Description")
        assert result is False

    def test_update_milestone_save_error(self, core):
        """Test milestone update with save error."""
        # Create milestone first
        milestone = core.milestones.create(
            name="Test Milestone", headline="Original description"
        )
        assert milestone is not None

        # Mock parser to raise exception
        with patch(
            "roadmap.adapters.persistence.parser.MilestoneParser.save_milestone_file"
        ) as mock_save:
            mock_save.side_effect = Exception("Save failed")

            result = core.milestones.update(
                name="Test Milestone", headline="Updated description"
            )
            assert result is False


class TestRoadmapCoreIssueAssignment:
    """Test issue assignment to milestones."""

    @pytest.fixture
    def core(self, temp_dir):
        """Create and initialize RoadmapCore for testing."""
        core = RoadmapCore(temp_dir)
        core.initialize()
        return core

    def test_assign_issue_to_milestone_success(self, core):
        """Test successful issue assignment to milestone."""
        # Create issue and milestone
        issue = core.issues.create(title="Test Issue", priority=Priority.MEDIUM)
        core.milestones.create(name="Test Milestone", headline="Milestone description")

        # Assign issue to milestone
        result = core.issues.assign_to_milestone(issue.id, "Test Milestone")
        assert result is True

        # Verify assignment
        updated_issue = core.issues.get(issue.id)
        assert updated_issue.milestone == "Test Milestone"

    def test_assign_issue_to_milestone_issue_not_found(self, core):
        """Test assigning nonexistent issue to milestone."""
        # Create milestone
        core.milestones.create(name="Test Milestone", headline="Milestone description")

        result = core.issues.assign_to_milestone("nonexistent-id", "Test Milestone")
        assert result is False

    def test_assign_issue_to_milestone_milestone_not_found(self, core):
        """Test assigning issue to nonexistent milestone."""
        # Create issue
        issue = core.issues.create(title="Test Issue", priority=Priority.MEDIUM)

        result = core.issues.assign_to_milestone(issue.id, "Nonexistent Milestone")
        assert result is False

    def test_assign_issue_to_milestone_both_not_found(self, core):
        """Test assigning nonexistent issue to nonexistent milestone."""
        result = core.issues.assign_to_milestone(
            "nonexistent-id", "Nonexistent Milestone"
        )
        assert result is False


class TestRoadmapCoreMilestoneProgress:
    """Test milestone progress tracking and statistics."""

    @pytest.fixture
    def core(self, temp_dir):
        """Create and initialize RoadmapCore for testing."""
        core = RoadmapCore(temp_dir)
        core.initialize()
        return core

    def test_get_milestone_progress_with_issues(self, core):
        """Test milestone progress calculation with various issue states."""
        # Create milestone
        core.milestones.create(name="Test Milestone", headline="Milestone description")

        # Create issues with different statuses
        issue1 = core.issues.create(title="Issue 1", priority=Priority.HIGH)
        issue2 = core.issues.create(title="Issue 2", priority=Priority.MEDIUM)
        issue3 = core.issues.create(title="Issue 3", priority=Priority.LOW)

        # Update their statuses after creation
        core.issues.update(issue1.id, status=Status.CLOSED)
        core.issues.update(issue2.id, status=Status.IN_PROGRESS)
        core.issues.update(issue3.id, status=Status.TODO)

        # Assign all issues to milestone
        core.issues.assign_to_milestone(issue1.id, "Test Milestone")
        core.issues.assign_to_milestone(issue2.id, "Test Milestone")
        core.issues.assign_to_milestone(issue3.id, "Test Milestone")

        # Get progress
        progress = core.milestones.get_progress("Test Milestone")

        assert progress["total"] == 3
        assert progress["completed"] == 1
        assert (
            abs(progress["progress"] - (100.0 / 3)) < 0.01
        )  # 1/3 * 100, approximately
        assert progress["by_status"]["closed"] == 1
        assert progress["by_status"]["in-progress"] == 1
        assert progress["by_status"]["todo"] == 1

    def test_get_milestone_progress_no_issues(self, core):
        """Test milestone progress with no assigned issues."""
        # Create milestone with no issues
        core.milestones.create(name="Empty Milestone", headline="No issues assigned")

        progress = core.milestones.get_progress("Empty Milestone")

        assert progress["total"] == 0
        assert progress["completed"] == 0
        assert progress["progress"] == 0.0
        assert progress["by_status"] == {}

    def test_get_milestone_progress_nonexistent_milestone(self, core):
        """Test progress for nonexistent milestone."""
        progress = core.milestones.get_progress("Nonexistent Milestone")

        # Should return empty progress dict
        assert progress["total"] == 0
        assert progress["completed"] == 0
        assert progress["progress"] == 0.0
        assert progress["by_status"] == {}


class TestRoadmapCoreBacklogOperations:
    """Test backlog and issue listing operations."""

    @pytest.fixture
    def core(self, temp_dir):
        """Create and initialize RoadmapCore for testing."""
        core = RoadmapCore(temp_dir)
        core.initialize()
        return core

    def test_get_backlog_issues(self, core):
        """Test getting backlog (unassigned) issues."""
        # Create milestone
        core.milestones.create(name="Test Milestone", headline="Milestone description")

        # Create issues - some assigned, some not
        issue1 = core.issues.create(title="Assigned Issue", priority=Priority.HIGH)
        core.issues.create(title="Backlog Issue 1", priority=Priority.MEDIUM)
        core.issues.create(title="Backlog Issue 2", priority=Priority.LOW)

        # Assign one issue to milestone
        core.issues.assign_to_milestone(issue1.id, "Test Milestone")

        # Get backlog
        backlog = core.issues.get_backlog()

        # Should only contain unassigned issues
        assert len(backlog) == 2
        backlog_titles = [issue.title for issue in backlog]
        assert "Backlog Issue 1" in backlog_titles
        assert "Backlog Issue 2" in backlog_titles
        assert "Assigned Issue" not in backlog_titles

    def test_get_backlog_issues_empty(self, core):
        """Test getting backlog when all issues are assigned."""
        # Create milestone
        core.milestones.create(name="Test Milestone", headline="Milestone description")

        # Create issue and assign it
        issue = core.issues.create(title="Assigned Issue", priority=Priority.HIGH)
        core.issues.assign_to_milestone(issue.id, "Test Milestone")

        # Backlog should be empty
        backlog = core.issues.get_backlog()
        assert len(backlog) == 0

    def test_get_milestone_issues(self, core):
        """Test getting issues for specific milestone."""
        # Create milestones
        core.milestones.create(name="Milestone 1", headline="First milestone")
        core.milestones.create(name="Milestone 2", headline="Second milestone")

        # Create issues
        issue1 = core.issues.create(title="Issue for M1", priority=Priority.HIGH)
        issue2 = core.issues.create(title="Issue for M2", priority=Priority.MEDIUM)
        issue3 = core.issues.create(title="Another for M1", priority=Priority.LOW)

        # Assign issues to milestones
        core.issues.assign_to_milestone(issue1.id, "Milestone 1")
        core.issues.assign_to_milestone(issue2.id, "Milestone 2")
        core.issues.assign_to_milestone(issue3.id, "Milestone 1")

        # Get milestone 1 issues
        m1_issues = core.issues.get_by_milestone("Milestone 1")
        assert len(m1_issues) == 2
        m1_titles = [issue.title for issue in m1_issues]
        assert "Issue for M1" in m1_titles
        assert "Another for M1" in m1_titles

        # Get milestone 2 issues
        m2_issues = core.issues.get_by_milestone("Milestone 2")
        assert len(m2_issues) == 1
        assert m2_issues[0].title == "Issue for M2"

    def test_get_milestone_issues_empty(self, core):
        """Test getting issues for milestone with no assignments."""
        # Create milestone
        core.milestones.create(name="Empty Milestone", headline="No issues assigned")

        # Create unassigned issue
        core.issues.create(title="Unassigned Issue", priority=Priority.MEDIUM)

        # Should return empty list
        issues = core.issues.get_by_milestone("Empty Milestone")
        assert len(issues) == 0

    def test_get_milestone_issues_nonexistent_milestone(self, core):
        """Test getting issues for nonexistent milestone."""
        issues = core.issues.get_by_milestone("Nonexistent Milestone")
        assert len(issues) == 0
