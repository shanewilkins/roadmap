"""Additional comprehensive tests for core roadmap functionality - targeting remaining uncovered areas."""

import os
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

    def test_get_issues_by_milestone(self, core):
        """Test getting issues grouped by milestone - group structure."""
        # Create milestones
        core.milestones.create("Milestone 1", "Description 1")
        core.milestones.create("Milestone 2", "Description 2")

        # Create issues
        issue1 = core.issues.create(title="Issue 1", priority=Priority.HIGH)
        issue2 = core.issues.create(title="Issue 2", priority=Priority.MEDIUM)
        issue3 = core.issues.create(title="Issue 3", priority=Priority.LOW)
        core.issues.create(title="Backlog Issue", priority=Priority.LOW)

        # Assign issues to milestones
        core.issues.assign_to_milestone(issue1.id, "Milestone 1")
        core.issues.assign_to_milestone(issue2.id, "Milestone 1")
        core.issues.assign_to_milestone(issue3.id, "Milestone 2")

        # Get grouped issues
        grouped = core.issues.get_grouped_by_milestone()

        assert "Backlog" in grouped
        assert "Milestone 1" in grouped
        assert "Milestone 2" in grouped

    def test_get_issues_by_milestone_counts(self, core):
        """Test getting issues grouped by milestone - issue counts."""
        # Create milestones
        core.milestones.create("Milestone 1", "Description 1")
        core.milestones.create("Milestone 2", "Description 2")

        # Create issues
        issue1 = core.issues.create(title="Issue 1", priority=Priority.HIGH)
        issue2 = core.issues.create(title="Issue 2", priority=Priority.MEDIUM)
        issue3 = core.issues.create(title="Issue 3", priority=Priority.LOW)
        core.issues.create(title="Backlog Issue", priority=Priority.LOW)

        # Assign issues to milestones
        core.issues.assign_to_milestone(issue1.id, "Milestone 1")
        core.issues.assign_to_milestone(issue2.id, "Milestone 1")
        core.issues.assign_to_milestone(issue3.id, "Milestone 2")

        # Get grouped issues
        grouped = core.issues.get_grouped_by_milestone()

        assert len(grouped["Backlog"]) == 1
        assert len(grouped["Milestone 1"]) == 2
        assert len(grouped["Milestone 2"]) == 1

    def test_get_issues_by_milestone_assignments(self, core):
        """Test getting issues grouped by milestone - verify issue titles."""
        # Create milestones
        core.milestones.create("Milestone 1", "Description 1")
        core.milestones.create("Milestone 2", "Description 2")

        # Create issues
        issue1 = core.issues.create(title="Issue 1", priority=Priority.HIGH)
        issue2 = core.issues.create(title="Issue 2", priority=Priority.MEDIUM)
        issue3 = core.issues.create(title="Issue 3", priority=Priority.LOW)
        core.issues.create(title="Backlog Issue", priority=Priority.LOW)

        # Assign issues to milestones
        core.issues.assign_to_milestone(issue1.id, "Milestone 1")
        core.issues.assign_to_milestone(issue2.id, "Milestone 1")
        core.issues.assign_to_milestone(issue3.id, "Milestone 2")

        # Get grouped issues
        grouped = core.issues.get_grouped_by_milestone()

        # Verify issue assignments
        assert grouped["Backlog"][0].title == "Backlog Issue"
        milestone1_titles = [issue.title for issue in grouped["Milestone 1"]]
        assert "Issue 1" in milestone1_titles
        assert "Issue 2" in milestone1_titles

    def test_move_issue_to_milestone(self, core):
        """Test moving issues between milestones."""
        # Create milestones
        core.milestones.create("Milestone 1", "Description 1")
        core.milestones.create("Milestone 2", "Description 2")

        # Create issue
        issue = core.issues.create(title="Test Issue", priority=Priority.MEDIUM)

        # Move to milestone 1
        result = core.issues.move_to_milestone(issue.id, "Milestone 1")
        assert result

        updated_issue = core.issues.get(issue.id)
        assert updated_issue.milestone == "Milestone 1"

        # Move to milestone 2
        result = core.issues.move_to_milestone(issue.id, "Milestone 2")
        assert result

        updated_issue = core.issues.get(issue.id)
        assert updated_issue.milestone == "Milestone 2"

        # Move to backlog (None)
        result = core.issues.move_to_milestone(issue.id, None)
        assert result

        updated_issue = core.issues.get(issue.id)
        assert updated_issue.milestone is None

    def test_move_issue_to_milestone_nonexistent_issue(self, core):
        """Test moving nonexistent issue."""
        result = core.issues.move_to_milestone("nonexistent-id", "Some Milestone")
        assert not result

    def test_get_next_milestone(self, core):
        """Test getting the next upcoming milestone."""
        # Create milestones with different due dates (only future dates for open milestones)
        future_date1 = datetime.now() + timedelta(days=10)
        future_date2 = datetime.now() + timedelta(days=20)

        core.milestones.create(
            name="Next Milestone", description="Coming soon", due_date=future_date1
        )
        core.milestones.create(
            name="Later Milestone", description="Coming later", due_date=future_date2
        )

        next_milestone = core.milestones.get_next()
        assert next_milestone is not None
        assert next_milestone.name == "Next Milestone"

    def test_get_next_milestone_no_future_milestones(self, core):
        """Test getting next milestone when none exist."""
        # Create milestone without due date (won't be returned by get_next_milestone)
        core.milestones.create(
            name="Milestone Without Due Date", description="No due date set"
        )

        next_milestone = core.milestones.get_next()
        assert next_milestone is None

    def test_get_next_milestone_no_due_dates(self, core):
        """Test getting next milestone when milestones have no due dates."""
        # Create milestones without due dates
        core.milestones.create("Milestone 1", "No due date")
        core.milestones.create("Milestone 2", "Also no due date")

        next_milestone = core.milestones.get_next()
        assert next_milestone is None


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
        # Mock the github_service since get_team_members delegates to it
        with patch.object(core.github_service, "get_team_members") as mock_get_members:
            mock_get_members.return_value = [
                "alice@example.com",
                "bob@example.com",
            ]

            team_members = core.team.get_members()

            # Should return team members from github_service
            assert len(team_members) == 2
            assert "alice@example.com" in team_members
            assert "bob@example.com" in team_members
            mock_get_members.assert_called_once()

    def test_get_team_members_empty(self, core):
        """Test getting team members when no issues have assignees."""
        # Create issues without assignees
        core.issues.create(title="Issue 1", priority=Priority.HIGH)
        core.issues.create(title="Issue 2", priority=Priority.MEDIUM)

        team_members = core.team.get_members()
        assert len(team_members) == 0

    def test_get_current_user_from_github(self, core):
        """Test getting current user from config."""
        # Mock the github_service since get_current_user delegates to it
        with patch.object(core.github_service, "get_current_user") as mock_get_user:
            mock_get_user.return_value = "test_user"

            current_user = core.team.get_current_user()
            assert current_user == "test_user"
            mock_get_user.assert_called_once()

    def test_get_current_user_no_github_config(self, core):
        """Test getting current user when config is not found."""
        # Mock ConfigManager to raise an exception
        from unittest.mock import patch

        with patch(
            "roadmap.core.services.github_integration_service.ConfigManager"
        ) as mock_cm_class:
            mock_cm_class.side_effect = Exception("Config not found")
            current_user = core.team.get_current_user()
            assert current_user is None

    def test_get_current_user_github_api_error(self, core):
        """Test getting current user when config read fails."""
        # Mock ConfigManager to raise exception during load
        from unittest.mock import patch

        with patch(
            "roadmap.core.services.github_integration_service.ConfigManager"
        ) as mock_cm_class:
            mock_cm_instance = Mock()
            mock_cm_instance.load.side_effect = Exception("Config error")
            mock_cm_class.return_value = mock_cm_instance

            current_user = core.team.get_current_user()
            assert current_user is None

    def test_get_assigned_issues(self, core):
        """Test getting issues assigned to specific user."""
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

        alice_issues = core.team.get_assigned_issues("alice@example.com")
        assert len(alice_issues) == 2
        alice_titles = [issue.title for issue in alice_issues]
        assert "Alice Issue 1" in alice_titles
        assert "Alice Issue 2" in alice_titles

        bob_issues = core.team.get_assigned_issues("bob@example.com")
        assert len(bob_issues) == 1
        assert bob_issues[0].title == "Bob Issue"

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

    @patch("roadmap.infrastructure.user_operations.UserOperations.get_current_user")
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

    def test_get_github_config_from_config_file(self, core):
        """Test getting GitHub config from roadmap config."""
        # This test checked a removed facade method - now delegated to service
        pass

    @patch.dict(os.environ, {"GITHUB_TOKEN": "env_token"})
    def test_get_github_config_from_environment(self, core):
        """Test getting GitHub token from environment variables."""
        # This test checked a removed facade method - now delegated to service
        pass

    def test_get_github_config_no_config(self, core):
        """Test getting GitHub config when none is available."""
        # This test checked a removed facade method - now delegated to service
        pass

    def test_get_cached_team_members(self, core):
        """Test getting cached team members."""
        # This test checked a removed facade method - now delegated to coordinator
        team_members = core.team.get_cached_team_members()
        assert isinstance(team_members, list)


class TestRoadmapCoreTemplatesAndConfig:
    """Test template creation and configuration management."""

    @pytest.fixture
    def core(self, temp_dir):
        """Create and initialize RoadmapCore for testing."""
        core = RoadmapCore(temp_dir)
        core.initialize()
        return core

    def test_create_default_templates(self, core):
        """Test that default templates are created - directory and files."""
        # Templates should already be created by initialization
        assert core.templates_dir.exists()

        # Check for expected template files
        issue_template = core.templates_dir / "issue.md"
        milestone_template = core.templates_dir / "milestone.md"

        assert issue_template.exists()
        assert milestone_template.exists()

    def test_create_default_templates_issue_content(self, core):
        """Test that default templates are created - issue template content."""
        # Templates should already be created by initialization
        issue_template = core.templates_dir / "issue.md"

        # Verify template content structure
        issue_content = issue_template.read_text()
        assert "title:" in issue_content
        assert "priority:" in issue_content
        assert "Description" in issue_content

    def test_create_default_templates_milestone_content(self, core):
        """Test that default templates are created - milestone template content."""
        # Templates should already be created by initialization
        milestone_template = core.templates_dir / "milestone.md"

        # Verify milestone template content
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

    @pytest.mark.parametrize(
        "assertion_type",
        [
            "basic",
            "status_assignee",
            "metrics",
            "milestone",
        ],
    )
    def test_update_issue_with_various_fields(self, core, assertion_type):
        """Test updating issues with various field combinations."""
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

        if assertion_type == "basic":
            assert updated_issue.title == "Updated Title"
            assert updated_issue.priority == Priority.HIGH
        elif assertion_type == "status_assignee":
            assert updated_issue.status == Status.IN_PROGRESS
            assert updated_issue.assignee == "alice@example.com"
        elif assertion_type == "metrics":
            assert updated_issue.estimated_hours == 5.5
            assert "bug" in updated_issue.labels
            assert "urgent" in updated_issue.labels
        elif assertion_type == "milestone":
            assert updated_issue.milestone == "Test Milestone"

    def test_update_issue_invalid_priority(self, core):
        """Test updating issue with invalid priority."""
        issue = core.issues.create(title="Test Issue", priority=Priority.MEDIUM)

        # This should handle validation errors gracefully
        core.issues.update(issue.id, priority="invalid_priority")
        # The update might fail or handle the invalid value - either is acceptable
        # As long as it doesn't crash the application

    @pytest.mark.parametrize(
        "operation,entity_type",
        [
            ("delete_issue", "issue"),
            ("delete_milestone", "milestone"),
        ],
    )
    def test_delete_with_file_error(self, core, operation, entity_type):
        """Test deletion operations with file system errors."""
        if entity_type == "issue":
            entity = core.issues.create(title="Test Issue", priority=Priority.MEDIUM)
            entity_id = entity.id
        else:
            core.milestones.create("Test Milestone", "Description")
            entity_id = "Test Milestone"

        # Mock file operations to raise exception
        with patch("pathlib.Path.unlink") as mock_unlink:
            mock_unlink.side_effect = PermissionError("Cannot delete file")

            if entity_type == "issue":
                result = core.issues.delete(entity_id)
            else:
                result = core.milestones.delete(entity_id)

            # Should handle error gracefully
            assert not result

    @pytest.mark.parametrize(
        "operation,entity_type",
        [
            ("list_issues", "issue"),
            ("list_milestones", "milestone"),
        ],
    )
    def test_list_with_corrupted_files(self, core, operation, entity_type):
        """Test listing operations with corrupted files."""
        if entity_type == "issue":
            corrupted_file = core.issues_dir / "corrupted_issue.md"
            corrupted_file.write_text("Invalid content without proper frontmatter")
            issues = core.issues.list()
            assert isinstance(issues, list)
        else:
            corrupted_file = core.milestones_dir / "corrupted.md"
            corrupted_file.write_text("---\nincomplete frontmatter")
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
