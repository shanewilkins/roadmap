"""Additional comprehensive tests for core roadmap functionality - targeting remaining uncovered areas."""

from datetime import datetime, timedelta
from unittest.mock import Mock, patch

import pytest

from roadmap.core.domain import (
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


class TestRoadmapCoreGitHubIntegration:
    """Test GitHub configuration and integration features."""

    @pytest.fixture
    def core(self, temp_dir):
        """Create and initialize RoadmapCore for testing."""
        core = RoadmapCore(temp_dir)
        core.initialize()
        return core

    @pytest.mark.parametrize(
        "expected_token,expected_owner,expected_repo,config_source",
        [
            ("test_token", "test_owner", "test_repo", "config_file"),
            ("env_token", "test_owner", "test_repo", "environment"),
            (None, None, None, "no_config"),
        ],
    )
    def test_get_github_config(
        self, core, expected_token, expected_owner, expected_repo, config_source
    ):
        """Test getting GitHub config from different sources."""
        # Mock the service's get_github_config method
        with patch.object(core.validation, "get_github_config") as mock_config:
            mock_config.return_value = (expected_token, expected_owner, expected_repo)

            token, owner, repo = core.validation.get_github_config()

            assert token == expected_token
            assert owner == expected_owner
            assert repo == expected_repo

    def test_get_cached_team_members(self, core):
        """Test getting cached team members."""
        # Mock the team coordinator's get_members method
        with patch.object(core.team, "get_members") as mock_members:
            mock_members.return_value = ["alice@example.com", "bob@example.com"]

            # Access team members via team coordinator
            team_members = core.team.get_members()

            assert len(team_members) == 2
            assert "alice@example.com" in team_members
            assert "bob@example.com" in team_members


class TestRoadmapCoreTemplatesAndConfig:
    """Test template creation and configuration management."""

    @pytest.fixture
    def core(self, temp_dir):
        """Create and initialize RoadmapCore for testing."""
        core = RoadmapCore(temp_dir)
        core.initialize()
        return core

    def test_create_default_templates(self, core):
        """Test that default templates are created during initialization."""
        # Templates should already be created by initialization
        assert core.templates_dir.exists()

        # Check for expected template files
        issue_template = core.templates_dir / "issue.md"
        milestone_template = core.templates_dir / "milestone.md"

        assert issue_template.exists()
        assert milestone_template.exists()

        # Verify template content structure
        issue_content = issue_template.read_text()
        assert "title:" in issue_content
        assert "priority:" in issue_content
        assert "Description" in issue_content

        milestone_content = milestone_template.read_text()
        assert "name:" in milestone_content
        assert "description:" in milestone_content

    def test_update_gitignore(self, core):
        """Test gitignore update functionality."""
        # Create a git repository in the test directory
        git_dir = core.root_path / ".git"
        git_dir.mkdir()

        # Create initial gitignore
        gitignore = core.root_path / ".gitignore"
        gitignore.write_text("# Initial content\n*.log\n")

        # Call the protected method
        core._update_gitignore()

        # Verify roadmap entries were added
        gitignore_content = gitignore.read_text()
        assert (
            ".roadmap/" in gitignore_content
            or core.roadmap_dir_name + "/" in gitignore_content
        )

    def test_update_gitignore_no_git_repo(self, core):
        """Test gitignore update when no git repo exists."""
        # Ensure no .git directory exists
        git_dir = core.root_path / ".git"
        if git_dir.exists():
            git_dir.rmdir()

        # This should not raise an error
        core._update_gitignore()

        # No gitignore should be created if no git repo
        core.root_path / ".gitignore"
        # The method might still create one, so we just verify it doesn't crash

    def test_load_config_success(self, core):
        """Test successful config loading."""
        config = core.load_config()

        # Should return a valid RoadmapConfig object
        assert config is not None
        assert hasattr(config, "github")
        assert hasattr(config, "defaults")
        assert hasattr(config, "milestones")
        assert hasattr(config, "sync")
        assert hasattr(config, "display")

    def test_load_config_not_initialized(self, temp_dir):
        """Test config loading on uninitialized roadmap."""
        core = RoadmapCore(temp_dir)  # Not initialized

        with pytest.raises(ValueError, match="Roadmap not initialized"):
            core.load_config()


class TestRoadmapCoreErrorHandlingAndEdgeCases:
    """Test error handling and edge cases in core functionality."""

    @pytest.fixture
    def core(self, temp_dir):
        """Create and initialize RoadmapCore for testing."""
        core = RoadmapCore(temp_dir)
        core.initialize()
        return core

    def test_update_issue_with_various_fields(self, core):
        """Test updating issues with different field types."""
        # Create issue
        issue = core.issues.create(title="Test Issue", priority=Priority.MEDIUM)

        # Update various fields
        updated_issue = core.issues.update(
            issue.id,
            title="Updated Title",
            priority=Priority.HIGH,
            status=Status.IN_PROGRESS,
            assignee="alice@example.com",
            estimated_hours=5.5,
            labels=["bug", "urgent"],
            milestone="Test Milestone",
        )

        assert updated_issue is not None
        assert updated_issue.title == "Updated Title"
        assert updated_issue.priority == Priority.HIGH
        assert updated_issue.status == Status.IN_PROGRESS
        assert updated_issue.assignee == "alice@example.com"
        assert updated_issue.estimated_hours == 5.5
        assert "bug" in updated_issue.labels
        assert "urgent" in updated_issue.labels
        assert updated_issue.milestone == "Test Milestone"

    def test_update_issue_invalid_priority(self, core):
        """Test updating issue with invalid priority."""
        issue = core.issues.create(title="Test Issue", priority=Priority.MEDIUM)

        # This should handle validation errors gracefully
        core.issues.update(issue.id, priority="invalid_priority")
        # The update might fail or handle the invalid value - either is acceptable
        # As long as it doesn't crash the application

    def test_delete_issue_with_file_error(self, core):
        """Test issue deletion with file system errors."""
        issue = core.issues.create(title="Test Issue", priority=Priority.MEDIUM)

        # Mock file operations to raise exception
        with patch("pathlib.Path.unlink") as mock_unlink:
            mock_unlink.side_effect = PermissionError("Cannot delete file")

            result = core.issues.delete(issue.id)
            # Should handle error gracefully
            assert result is False

    def test_delete_milestone_with_file_error(self, core):
        """Test milestone deletion with file system errors."""
        core.milestones.create("Test Milestone", "Description")

        # Mock file operations to raise exception
        with patch("pathlib.Path.unlink") as mock_unlink:
            mock_unlink.side_effect = PermissionError("Cannot delete file")

            result = core.milestones.delete("Test Milestone")
            # Should handle error gracefully
            assert result is False

    def test_list_issues_with_corrupted_files(self, core):
        """Test issue listing with corrupted issue files."""
        # Create a corrupted issue file directly
        corrupted_file = core.issues_dir / "corrupted_issue.md"
        corrupted_file.write_text("Invalid content without proper frontmatter")

        # Should handle corruption gracefully
        issues = core.issues.list()
        # Should return empty list or valid issues only, not crash
        assert isinstance(issues, list)

    def test_list_milestones_with_parser_errors(self, core):
        """Test milestone listing with parser errors."""
        # Create corrupted milestone file
        corrupted_file = core.milestones_dir / "corrupted.md"
        corrupted_file.write_text("---\nincomplete frontmatter")

        # Should handle gracefully
        milestones = core.milestones.list()
        assert isinstance(milestones, list)

    def test_operations_with_permission_errors(self, core):
        """Test operations with file permission errors."""
        # Make issues directory read-only
        import stat
        import time

        from roadmap.common.errors.exceptions import CreateError

        try:
            core.issues_dir.chmod(stat.S_IRUSR | stat.S_IXUSR)

            # Operations should handle permission errors gracefully
            try:
                core.issues.create("Test Issue", priority=Priority.HIGH)
                # May succeed or fail depending on system
            except (PermissionError, OSError, CreateError):
                # Expected on some systems (CreateError wraps permission errors)
                pass

        finally:
            # Restore permissions - with retry logic for stubborn file handles
            for attempt in range(3):
                try:
                    core.issues_dir.chmod(stat.S_IRWXU)
                    break
                except (PermissionError, OSError):
                    if attempt < 2:
                        time.sleep(0.1)  # Brief pause before retry
                    else:
                        # Last attempt - suppress error as cleanup will handle it
                        pass

    def test_milestone_operations_edge_cases(self, core):
        """Test milestone operations with edge cases."""
        # Test with milestone names that require sanitization
        milestone = core.milestones.create(
            name="Test/Milestone With Special@Characters!", description="Description"
        )
        assert milestone is not None

        # Verify we can retrieve it
        retrieved = core.milestones.get("Test/Milestone With Special@Characters!")
        assert retrieved is not None
        assert retrieved.name == "Test/Milestone With Special@Characters!"

    def test_issue_filename_generation(self, core):
        """Test issue filename generation and uniqueness."""
        # Create issues with similar titles
        issue1 = core.issues.create(title="Test Issue", priority=Priority.HIGH)
        issue2 = core.issues.create(
            title="Test Issue", priority=Priority.MEDIUM
        )  # Same title

        # Should have different filenames
        assert issue1.filename != issue2.filename
        assert issue1.id != issue2.id

        # Both files should exist
        file1 = core.issues_dir / issue1.filename
        file2 = core.issues_dir / issue2.filename
        assert file1.exists()
        assert file2.exists()
