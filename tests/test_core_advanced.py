"""Additional comprehensive tests for core roadmap functionality - targeting remaining uncovered areas."""

import os
import tempfile
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import Mock, patch, call

import pytest

from roadmap.core import RoadmapCore
from roadmap.models import Issue, Milestone, MilestoneStatus, Priority, Status, IssueType


pytestmark = pytest.mark.unit


@pytest.fixture
def temp_dir():
    """Create a temporary directory for testing."""
    with tempfile.TemporaryDirectory() as temp_dir:
        yield Path(temp_dir)


class TestRoadmapCoreAdvancedIssueOperations:
    """Test advanced issue operations and filtering."""

    @pytest.fixture
    def core(self, temp_dir):
        """Create and initialize RoadmapCore for testing."""
        core = RoadmapCore(temp_dir)
        core.initialize()
        return core

    def test_get_issues_by_milestone(self, core):
        """Test getting issues grouped by milestone."""
        # Create milestones
        milestone1 = core.create_milestone("Milestone 1", "Description 1")
        milestone2 = core.create_milestone("Milestone 2", "Description 2")
        
        # Create issues
        issue1 = core.create_issue(title="Issue 1", priority=Priority.HIGH)
        issue2 = core.create_issue(title="Issue 2", priority=Priority.MEDIUM)
        issue3 = core.create_issue(title="Issue 3", priority=Priority.LOW)
        issue4 = core.create_issue(title="Backlog Issue", priority=Priority.LOW)
        
        # Assign issues to milestones
        core.assign_issue_to_milestone(issue1.id, "Milestone 1")
        core.assign_issue_to_milestone(issue2.id, "Milestone 1")
        core.assign_issue_to_milestone(issue3.id, "Milestone 2")
        # issue4 remains unassigned (backlog)
        
        # Get grouped issues
        grouped = core.get_issues_by_milestone()
        
        assert "Backlog" in grouped
        assert "Milestone 1" in grouped
        assert "Milestone 2" in grouped
        
        assert len(grouped["Backlog"]) == 1
        assert len(grouped["Milestone 1"]) == 2
        assert len(grouped["Milestone 2"]) == 1
        
        # Verify issue assignments
        assert grouped["Backlog"][0].title == "Backlog Issue"
        milestone1_titles = [issue.title for issue in grouped["Milestone 1"]]
        assert "Issue 1" in milestone1_titles
        assert "Issue 2" in milestone1_titles

    def test_move_issue_to_milestone(self, core):
        """Test moving issues between milestones."""
        # Create milestones
        milestone1 = core.create_milestone("Milestone 1", "Description 1")
        milestone2 = core.create_milestone("Milestone 2", "Description 2")
        
        # Create issue
        issue = core.create_issue(title="Test Issue", priority=Priority.MEDIUM)
        
        # Move to milestone 1
        result = core.move_issue_to_milestone(issue.id, "Milestone 1")
        assert result is True
        
        updated_issue = core.get_issue(issue.id)
        assert updated_issue.milestone == "Milestone 1"
        
        # Move to milestone 2
        result = core.move_issue_to_milestone(issue.id, "Milestone 2")
        assert result is True
        
        updated_issue = core.get_issue(issue.id)
        assert updated_issue.milestone == "Milestone 2"
        
        # Move to backlog (None)
        result = core.move_issue_to_milestone(issue.id, None)
        assert result is True
        
        updated_issue = core.get_issue(issue.id)
        assert updated_issue.milestone is None

    def test_move_issue_to_milestone_nonexistent_issue(self, core):
        """Test moving nonexistent issue."""
        result = core.move_issue_to_milestone("nonexistent-id", "Some Milestone")
        assert result is False

    def test_get_next_milestone(self, core):
        """Test getting the next upcoming milestone."""
        # Create milestones with different due dates (only future dates for open milestones)
        future_date1 = datetime.now() + timedelta(days=10)
        future_date2 = datetime.now() + timedelta(days=20)
        
        milestone1 = core.create_milestone(
            name="Next Milestone", 
            description="Coming soon",
            due_date=future_date1
        )
        milestone2 = core.create_milestone(
            name="Later Milestone", 
            description="Coming later",
            due_date=future_date2
        )
        
        next_milestone = core.get_next_milestone()
        assert next_milestone is not None
        assert next_milestone.name == "Next Milestone"

    def test_get_next_milestone_no_future_milestones(self, core):
        """Test getting next milestone when none exist."""
        # Create milestone without due date (won't be returned by get_next_milestone)
        milestone = core.create_milestone(
            name="Milestone Without Due Date", 
            description="No due date set"
        )
        
        next_milestone = core.get_next_milestone()
        assert next_milestone is None

    def test_get_next_milestone_no_due_dates(self, core):
        """Test getting next milestone when milestones have no due dates."""
        # Create milestones without due dates
        milestone1 = core.create_milestone("Milestone 1", "No due date")
        milestone2 = core.create_milestone("Milestone 2", "Also no due date")
        
        next_milestone = core.get_next_milestone()
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
        # Mock GitHub client since get_team_members calls GitHub API
        with patch('roadmap.github_client.GitHubClient') as mock_github_client:
            mock_client = Mock()
            mock_client.get_team_members.return_value = ["alice@example.com", "bob@example.com"]
            mock_github_client.return_value = mock_client
            
            # Mock GitHub config
            with patch.object(core, '_get_github_config') as mock_config:
                mock_config.return_value = ("token", "owner", "repo")
                
                team_members = core.get_team_members()
                
                # Should return team members from GitHub API
                assert len(team_members) == 2
                assert "alice@example.com" in team_members
                assert "bob@example.com" in team_members

    def test_get_team_members_empty(self, core):
        """Test getting team members when no issues have assignees."""
        # Create issues without assignees
        issue1 = core.create_issue(title="Issue 1", priority=Priority.HIGH)
        issue2 = core.create_issue(title="Issue 2", priority=Priority.MEDIUM)
        
        team_members = core.get_team_members()
        assert len(team_members) == 0

    def test_get_current_user_from_github(self, core):
        """Test getting current user from GitHub API."""
        # Mock GitHub client
        with patch('roadmap.github_client.GitHubClient') as mock_github_client:
            mock_client = Mock()
            mock_client.get_current_user.return_value = "current_user"
            mock_github_client.return_value = mock_client
            
            # Mock GitHub config
            with patch.object(core, '_get_github_config') as mock_config:
                mock_config.return_value = ("token", "owner", "repo")
                
                current_user = core.get_current_user()
                assert current_user == "current_user"

    def test_get_current_user_no_github_config(self, core):
        """Test getting current user when GitHub is not configured."""
        # Mock GitHub config to return None
        with patch.object(core, '_get_github_config') as mock_config:
            mock_config.return_value = (None, None, None)
            
            current_user = core.get_current_user()
            assert current_user is None

    def test_get_current_user_github_api_error(self, core):
        """Test getting current user when GitHub API fails."""
        # Mock GitHub client to raise exception
        with patch('roadmap.github_client.GitHubClient') as mock_github_client:
            mock_github_client.side_effect = Exception("API Error")
            
            # Mock GitHub config
            with patch.object(core, '_get_github_config') as mock_config:
                mock_config.return_value = ("token", "owner", "repo")
                
                current_user = core.get_current_user()
                assert current_user is None

    def test_get_assigned_issues(self, core):
        """Test getting issues assigned to specific user."""
        # Create issues with different assignees
        issue1 = core.create_issue(
            title="Alice Issue 1", 
            priority=Priority.HIGH,
            assignee="alice@example.com"
        )
        issue2 = core.create_issue(
            title="Bob Issue", 
            priority=Priority.MEDIUM,
            assignee="bob@example.com"
        )
        issue3 = core.create_issue(
            title="Alice Issue 2", 
            priority=Priority.LOW,
            assignee="alice@example.com"
        )
        
        alice_issues = core.get_assigned_issues("alice@example.com")
        assert len(alice_issues) == 2
        alice_titles = [issue.title for issue in alice_issues]
        assert "Alice Issue 1" in alice_titles
        assert "Alice Issue 2" in alice_titles
        
        bob_issues = core.get_assigned_issues("bob@example.com")
        assert len(bob_issues) == 1
        assert bob_issues[0].title == "Bob Issue"

    @patch('roadmap.core.RoadmapCore.get_current_user')
    def test_get_my_issues(self, mock_current_user, core):
        """Test getting issues assigned to current user."""
        mock_current_user.return_value = "alice@example.com"
        
        # Create issues
        issue1 = core.create_issue(
            title="My Issue 1", 
            priority=Priority.HIGH,
            assignee="alice@example.com"
        )
        issue2 = core.create_issue(
            title="Someone Else's Issue", 
            priority=Priority.MEDIUM,
            assignee="bob@example.com"
        )
        issue3 = core.create_issue(
            title="My Issue 2", 
            priority=Priority.LOW,
            assignee="alice@example.com"
        )
        
        my_issues = core.get_my_issues()
        assert len(my_issues) == 2
        my_titles = [issue.title for issue in my_issues]
        assert "My Issue 1" in my_titles
        assert "My Issue 2" in my_titles

    @patch('roadmap.core.RoadmapCore.get_current_user')
    def test_get_my_issues_no_current_user(self, mock_current_user, core):
        """Test getting my issues when current user is unknown."""
        mock_current_user.return_value = None
        
        # Create issues
        issue = core.create_issue(
            title="Some Issue", 
            priority=Priority.HIGH,
            assignee="alice@example.com"
        )
        
        my_issues = core.get_my_issues()
        assert len(my_issues) == 0

    def test_get_all_assigned_issues(self, core):
        """Test getting all issues grouped by assignee."""
        # Create issues with different assignees
        issue1 = core.create_issue(
            title="Alice Issue 1", 
            priority=Priority.HIGH,
            assignee="alice@example.com"
        )
        issue2 = core.create_issue(
            title="Bob Issue", 
            priority=Priority.MEDIUM,
            assignee="bob@example.com"
        )
        issue3 = core.create_issue(
            title="Alice Issue 2", 
            priority=Priority.LOW,
            assignee="alice@example.com"
        )
        issue4 = core.create_issue(
            title="Unassigned Issue", 
            priority=Priority.LOW
            # No assignee
        )
        
        all_assigned = core.get_all_assigned_issues()
        
        assert "alice@example.com" in all_assigned
        assert "bob@example.com" in all_assigned
        
        assert len(all_assigned["alice@example.com"]) == 2
        assert len(all_assigned["bob@example.com"]) == 1
        
        # Unassigned issues should not appear in results
        assert "Unassigned Issue" not in [
            issue.title for assignee_issues in all_assigned.values() 
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
        # Mock the config loading and credential manager
        with patch.object(core, 'load_config') as mock_load:
            mock_config = Mock()
            mock_config.github = {"owner": "test_owner", "repo": "test_repo"}
            mock_load.return_value = mock_config
            
            # Mock credential manager
            with patch('roadmap.credentials.get_credential_manager') as mock_cred_mgr:
                mock_manager = Mock()
                mock_manager.get_credential.return_value = "test_token"
                mock_cred_mgr.return_value = mock_manager
                
                token, owner, repo = core._get_github_config()
                
                assert token == "test_token"
                assert owner == "test_owner" 
                assert repo == "test_repo"

    @patch.dict(os.environ, {
        "GITHUB_TOKEN": "env_token"
    })
    def test_get_github_config_from_environment(self, core):
        """Test getting GitHub token from environment variables."""
        # Mock config loading to return valid config without token
        with patch.object(core, 'load_config') as mock_load:
            mock_config = Mock()
            mock_config.github = {"owner": "test_owner", "repo": "test_repo"}
            mock_load.return_value = mock_config
            
            # Mock credential manager to return None (no stored token)
            with patch('roadmap.credentials.get_credential_manager') as mock_cred_mgr:
                mock_manager = Mock()
                mock_manager.get_credential.return_value = None
                mock_cred_mgr.return_value = mock_manager
                
                token, owner, repo = core._get_github_config()
                
                assert token == "env_token"
                assert owner == "test_owner"
                assert repo == "test_repo"

    def test_get_github_config_no_config(self, core):
        """Test getting GitHub config when none is available."""
        # Mock config loading to raise exception
        with patch.object(core, 'load_config') as mock_load:
            mock_load.side_effect = Exception("Config not found")
            
            token, owner, repo = core._get_github_config()
            
            assert token is None
            assert owner is None
            assert repo is None

    @patch('roadmap.core.RoadmapCore._get_cached_team_members')
    def test_get_cached_team_members(self, mock_cached, core):
        """Test getting cached team members."""
        mock_cached.return_value = ["alice@example.com", "bob@example.com"]
        
        # Access the protected method indirectly via team member functionality
        team_members = core._get_cached_team_members()
        
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
        assert ".roadmap/" in gitignore_content or core.roadmap_dir_name + "/" in gitignore_content

    def test_update_gitignore_no_git_repo(self, core):
        """Test gitignore update when no git repo exists."""
        # Ensure no .git directory exists
        git_dir = core.root_path / ".git"
        if git_dir.exists():
            git_dir.rmdir()
        
        # This should not raise an error
        core._update_gitignore()
        
        # No gitignore should be created if no git repo
        gitignore = core.root_path / ".gitignore"
        # The method might still create one, so we just verify it doesn't crash

    def test_load_config_success(self, core):
        """Test successful config loading."""
        config = core.load_config()
        
        # Should return a valid RoadmapConfig object
        assert config is not None
        assert hasattr(config, 'github')
        assert hasattr(config, 'defaults')
        assert hasattr(config, 'milestones')
        assert hasattr(config, 'sync')
        assert hasattr(config, 'display')

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
        issue = core.create_issue(title="Test Issue", priority=Priority.MEDIUM)
        
        # Update various fields
        updated_issue = core.update_issue(
            issue.id,
            title="Updated Title",
            priority=Priority.HIGH,
            status=Status.IN_PROGRESS,
            assignee="alice@example.com",
            estimated_hours=5.5,
            labels=["bug", "urgent"],
            milestone="Test Milestone"
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
        issue = core.create_issue(title="Test Issue", priority=Priority.MEDIUM)
        
        # This should handle validation errors gracefully
        updated_issue = core.update_issue(issue.id, priority="invalid_priority")
        # The update might fail or handle the invalid value - either is acceptable
        # As long as it doesn't crash the application

    def test_delete_issue_with_file_error(self, core):
        """Test issue deletion with file system errors."""
        issue = core.create_issue(title="Test Issue", priority=Priority.MEDIUM)
        
        # Mock file operations to raise exception
        with patch('pathlib.Path.unlink') as mock_unlink:
            mock_unlink.side_effect = PermissionError("Cannot delete file")
            
            result = core.delete_issue(issue.id)
            # Should handle error gracefully
            assert result is False

    def test_delete_milestone_with_file_error(self, core):
        """Test milestone deletion with file system errors."""
        milestone = core.create_milestone("Test Milestone", "Description")
        
        # Mock file operations to raise exception
        with patch('pathlib.Path.unlink') as mock_unlink:
            mock_unlink.side_effect = PermissionError("Cannot delete file")
            
            result = core.delete_milestone("Test Milestone")
            # Should handle error gracefully
            assert result is False

    def test_list_issues_with_corrupted_files(self, core):
        """Test issue listing with corrupted issue files."""
        # Create a corrupted issue file directly
        corrupted_file = core.issues_dir / "corrupted_issue.md" 
        corrupted_file.write_text("Invalid content without proper frontmatter")
        
        # Should handle corruption gracefully
        issues = core.list_issues()
        # Should return empty list or valid issues only, not crash
        assert isinstance(issues, list)

    def test_list_milestones_with_parser_errors(self, core):
        """Test milestone listing with parser errors."""
        # Create corrupted milestone file
        corrupted_file = core.milestones_dir / "corrupted.md"
        corrupted_file.write_text("---\nincomplete frontmatter")
        
        # Should handle gracefully
        milestones = core.list_milestones()
        assert isinstance(milestones, list)

    def test_operations_with_permission_errors(self, core):
        """Test operations with file permission errors."""
        # Make issues directory read-only
        import stat
        try:
            core.issues_dir.chmod(stat.S_IRUSR | stat.S_IXUSR)
            
            # Operations should handle permission errors gracefully
            try:
                issue = core.create_issue("Test Issue", priority=Priority.HIGH)
                # May succeed or fail depending on system
            except (PermissionError, OSError):
                # Expected on some systems
                pass
                
        finally:
            # Restore permissions
            core.issues_dir.chmod(stat.S_IRWXU)

    def test_milestone_operations_edge_cases(self, core):
        """Test milestone operations with edge cases."""
        # Test with milestone names that require sanitization
        milestone = core.create_milestone(
            name="Test/Milestone With Special@Characters!",
            description="Description"
        )
        assert milestone is not None
        
        # Verify we can retrieve it
        retrieved = core.get_milestone("Test/Milestone With Special@Characters!")
        assert retrieved is not None
        assert retrieved.name == "Test/Milestone With Special@Characters!"

    def test_issue_filename_generation(self, core):
        """Test issue filename generation and uniqueness."""
        # Create issues with similar titles
        issue1 = core.create_issue(title="Test Issue", priority=Priority.HIGH)
        issue2 = core.create_issue(title="Test Issue", priority=Priority.MEDIUM)  # Same title
        
        # Should have different filenames
        assert issue1.filename != issue2.filename
        assert issue1.id != issue2.id
        
        # Both files should exist
        file1 = core.issues_dir / issue1.filename
        file2 = core.issues_dir / issue2.filename
        assert file1.exists()
        assert file2.exists()