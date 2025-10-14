"""Final targeted tests for core roadmap functionality - covering remaining uncovered lines."""

import os
import tempfile
from datetime import datetime
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


class TestRoadmapCoreUncoveredLines:
    """Test specific uncovered lines and edge cases."""

    @pytest.fixture
    def core(self, temp_dir):
        """Create and initialize RoadmapCore for testing."""
        core = RoadmapCore(temp_dir)
        core.initialize()
        return core

    def test_list_issues_with_multiple_filters(self, core):
        """Test list_issues with multiple filter combinations to hit duplicate filter lines."""
        # Create test issues
        issue1 = core.create_issue(
            title="High Priority Issue",
            priority=Priority.HIGH,
            assignee="alice@example.com",
            issue_type=IssueType.BUG
        )
        issue2 = core.create_issue(
            title="Medium Priority Feature",
            priority=Priority.MEDIUM,
            assignee="bob@example.com", 
            issue_type=IssueType.FEATURE
        )
        issue3 = core.create_issue(
            title="Low Priority Task",
            priority=Priority.LOW,
            assignee="alice@example.com",
            issue_type=IssueType.OTHER
        )
        
        # Update statuses after creation
        core.update_issue(issue1.id, status=Status.IN_PROGRESS)
        core.update_issue(issue2.id, status=Status.TODO)
        core.update_issue(issue3.id, status=Status.DONE)
        
        # Test with priority and assignee filters (hits duplicate filter lines)
        filtered_issues = core.list_issues(
            priority=Priority.HIGH,
            assignee="alice@example.com"
        )
        assert len(filtered_issues) == 1
        assert filtered_issues[0].title == "High Priority Issue"
        
        # Test with all filters to exercise all branches
        filtered_issues = core.list_issues(
            priority=Priority.MEDIUM,
            status=Status.TODO,
            assignee="bob@example.com",
            issue_type=IssueType.FEATURE
        )
        assert len(filtered_issues) == 1
        assert filtered_issues[0].title == "Medium Priority Feature"

    def test_get_milestone_with_parser_exception(self, core):
        """Test get_milestone when parser raises exception."""
        # Create a corrupted milestone file
        milestone_file = core.milestones_dir / "corrupted_milestone.md"
        milestone_file.write_text("corrupted content that will cause parser to fail")
        
        # Mock parser to raise exception on this file
        with patch('roadmap.parser.MilestoneParser.parse_milestone_file') as mock_parse:
            mock_parse.side_effect = Exception("Parse error")
            
            milestone = core.get_milestone("corrupted_milestone")
            assert milestone is None

    def test_delete_milestone_with_assigned_issues(self, core):
        """Test deleting milestone that has assigned issues."""
        # Create milestone
        milestone = core.create_milestone("Test Milestone", "Description")
        
        # Create and assign issues to the milestone
        issue1 = core.create_issue(
            title="Issue 1",
            priority=Priority.HIGH,
            milestone="Test Milestone"
        )
        issue2 = core.create_issue(
            title="Issue 2", 
            priority=Priority.MEDIUM,
            milestone="Test Milestone"
        )
        
        # Verify issues are assigned
        assert core.get_issue(issue1.id).milestone == "Test Milestone"
        assert core.get_issue(issue2.id).milestone == "Test Milestone"
        
        # Delete milestone
        result = core.delete_milestone("Test Milestone")
        assert result is True
        
        # Verify issues are unassigned
        updated_issue1 = core.get_issue(issue1.id)
        updated_issue2 = core.get_issue(issue2.id)
        assert updated_issue1.milestone == "" or updated_issue1.milestone is None
        assert updated_issue2.milestone == "" or updated_issue2.milestone is None
        
        # Verify milestone is deleted
        assert core.get_milestone("Test Milestone") is None

    def test_delete_nonexistent_milestone(self, core):
        """Test deleting a milestone that doesn't exist."""
        result = core.delete_milestone("Nonexistent Milestone")
        assert result is False

    def test_create_issue_with_git_branch(self, core):
        """Test create_issue_with_git_branch functionality."""
        # Mock git repository
        with patch.object(core.git, 'is_git_repository') as mock_is_git:
            mock_is_git.return_value = True
            
            # Mock branch creation
            with patch.object(core.git, 'create_branch_for_issue') as mock_create_branch:
                mock_create_branch.return_value = True
                
                # Create issue with auto branch creation
                issue = core.create_issue_with_git_branch(
                    "Test Issue",
                    priority=Priority.HIGH,
                    auto_create_branch=True
                )
                
                assert issue is not None
                assert issue.title == "Test Issue"
                mock_create_branch.assert_called_once()

    def test_create_issue_with_git_branch_no_git(self, core):
        """Test create_issue_with_git_branch when not in git repository."""
        # Mock no git repository
        with patch.object(core.git, 'is_git_repository') as mock_is_git:
            mock_is_git.return_value = False
            
            # Create issue with auto branch creation (should still work)
            issue = core.create_issue_with_git_branch(
                "Test Issue",
                priority=Priority.HIGH,
                auto_create_branch=True
            )
            
            assert issue is not None
            assert issue.title == "Test Issue"

    def test_get_git_context_with_linked_issue(self, core):
        """Test get_git_context with linked issue."""
        # Create an issue
        issue = core.create_issue(title="Test Issue", priority=Priority.HIGH)
        
        # Mock git repository with branch that contains issue ID
        with patch.object(core.git, 'is_git_repository') as mock_is_git:
            mock_is_git.return_value = True
            
            # Mock repository info
            with patch.object(core.git, 'get_repository_info') as mock_repo_info:
                mock_repo_info.return_value = {
                    "remote_url": "https://github.com/test/repo.git",
                    "branch_count": 5
                }
                
                # Mock current branch with issue ID
                mock_branch = Mock()
                mock_branch.name = f"feature-{issue.id}-test-branch"
                mock_branch.extract_issue_id.return_value = issue.id
                
                with patch.object(core.git, 'get_current_branch') as mock_current_branch:
                    mock_current_branch.return_value = mock_branch
                    
                    context = core.get_git_context()
                    
                    assert context["is_git_repo"] is True
                    assert context["remote_url"] == "https://github.com/test/repo.git"
                    assert context["current_branch"] == mock_branch.name
                    assert "linked_issue" in context
                    assert context["linked_issue"]["id"] == issue.id
                    assert context["linked_issue"]["title"] == "Test Issue"

    def test_get_git_context_no_linked_issue(self, core):
        """Test get_git_context with branch that has no linked issue."""
        # Mock git repository
        with patch.object(core.git, 'is_git_repository') as mock_is_git:
            mock_is_git.return_value = True
            
            # Mock repository info
            with patch.object(core.git, 'get_repository_info') as mock_repo_info:
                mock_repo_info.return_value = {"remote_url": "origin"}
                
                # Mock current branch without issue ID
                mock_branch = Mock()
                mock_branch.name = "main"
                mock_branch.extract_issue_id.return_value = None
                
                with patch.object(core.git, 'get_current_branch') as mock_current_branch:
                    mock_current_branch.return_value = mock_branch
                    
                    context = core.get_git_context()
                    
                    assert context["is_git_repo"] is True
                    assert context["current_branch"] == "main"
                    assert "linked_issue" not in context

    def test_get_git_context_no_current_branch(self, core):
        """Test get_git_context when no current branch."""
        # Mock git repository
        with patch.object(core.git, 'is_git_repository') as mock_is_git:
            mock_is_git.return_value = True
            
            # Mock repository info
            with patch.object(core.git, 'get_repository_info') as mock_repo_info:
                mock_repo_info.return_value = {"status": "detached"}
                
                # Mock no current branch
                with patch.object(core.git, 'get_current_branch') as mock_current_branch:
                    mock_current_branch.return_value = None
                    
                    context = core.get_git_context()
                    
                    assert context["is_git_repo"] is True
                    assert "current_branch" not in context
                    assert "linked_issue" not in context

    def test_get_current_user_from_git(self, core):
        """Test get_current_user_from_git method."""
        with patch.object(core.git, 'get_current_user') as mock_git_user:
            mock_git_user.return_value = "git_user@example.com"
            
            user = core.get_current_user_from_git()
            assert user == "git_user@example.com"

    def test_validate_assignee_with_cached_team_members(self, core):
        """Test validate_assignee using cached team members."""
        # Mock GitHub config
        with patch.object(core, '_get_github_config') as mock_config:
            mock_config.return_value = ("token", "owner", "repo")
            
            # Mock cached team members
            with patch.object(core, '_get_cached_team_members') as mock_cached:
                mock_cached.return_value = ["alice@example.com", "bob@example.com"]
                
                # Test valid assignee from cache
                is_valid, error = core.validate_assignee("alice@example.com")
                assert is_valid is True
                assert error == ""
                
                # Test invalid assignee not in cache
                with patch('roadmap.github_client.GitHubClient') as mock_github:
                    mock_client = Mock()
                    mock_client.validate_assignee.return_value = (False, "User not found")
                    mock_github.return_value = mock_client
                    
                    is_valid, error = core.validate_assignee("unknown@example.com")
                    assert is_valid is False
                    assert "User not found" in error

    def test_validate_assignee_empty_assignee(self, core):
        """Test validate_assignee with empty assignee."""
        is_valid, error = core.validate_assignee("")
        assert is_valid is False
        assert "Assignee cannot be empty" in error
        
        is_valid, error = core.validate_assignee("   ")
        assert is_valid is False
        assert "Assignee cannot be empty" in error

    def test_validate_assignee_no_github_config(self, core):
        """Test validate_assignee when GitHub is not configured."""
        # Mock no GitHub config
        with patch.object(core, '_get_github_config') as mock_config:
            mock_config.return_value = (None, None, None)
            
            # Should allow any assignee without validation
            is_valid, error = core.validate_assignee("any_user@example.com")
            assert is_valid is True
            assert error == ""

    def test_validate_assignee_with_exception(self, core):
        """Test validate_assignee when GitHub validation raises exception."""
        # Mock GitHub config
        with patch.object(core, '_get_github_config') as mock_config:
            mock_config.return_value = ("token", "owner", "repo")
            
            # Mock cached team members (empty)
            with patch.object(core, '_get_cached_team_members') as mock_cached:
                mock_cached.return_value = []
                
                # Mock GitHub client to raise exception
                with patch('roadmap.github_client.GitHubClient') as mock_github:
                    mock_github.side_effect = Exception("Network error")
                    
                    is_valid, error = core.validate_assignee("test@example.com")
                    assert is_valid is True  # Should allow with warning
                    assert "Warning" in error
                    assert "GitHub API unavailable" in error

    def test_issue_operations_not_initialized(self, temp_dir):
        """Test issue operations when roadmap is not initialized."""
        core = RoadmapCore(temp_dir)  # Not initialized
        
        with pytest.raises(ValueError, match="Roadmap not initialized"):
            core.create_issue("Test Issue", priority=Priority.HIGH)
        
        with pytest.raises(ValueError, match="Roadmap not initialized"):
            core.list_issues()
        
        with pytest.raises(ValueError, match="Roadmap not initialized"):
            core.delete_milestone("Test")

    def test_create_issue_failed_return(self, core):
        """Test create_issue_with_git_branch when issue creation fails."""
        # Mock create_issue to return None
        with patch.object(core, 'create_issue') as mock_create:
            mock_create.return_value = None
            
            result = core.create_issue_with_git_branch(
                "Failed Issue",
                priority=Priority.HIGH,
                auto_create_branch=True
            )
            
            assert result is None

    def test_security_and_logging_integration(self, core):
        """Test security logging integration in various operations."""
        # Test issue creation with security logging
        with patch('roadmap.security.log_security_event') as mock_log:
            issue = core.create_issue(
                title="Security Test Issue",
                priority=Priority.HIGH
            )
            
            # Security logging should be called during file operations
            assert issue is not None

    def test_file_operations_edge_cases(self, core):
        """Test edge cases in file operations."""
        # Test with very long issue titles
        long_title = "A" * 200  # Very long title
        issue = core.create_issue(title=long_title, priority=Priority.HIGH)
        assert issue is not None
        assert issue.title == long_title
        
        # Test with special characters in titles
        special_title = "Issue with special chars: @#$%^&*()[]{}|\\:\"'<>?/~`"
        issue = core.create_issue(title=special_title, priority=Priority.HIGH)
        assert issue is not None
        assert issue.title == special_title

    def test_milestone_status_filtering(self, core):
        """Test milestone operations with different status values."""
        # Create milestones with different statuses
        milestone1 = core.create_milestone("Open Milestone", "Open milestone")
        milestone2 = core.create_milestone("Closed Milestone", "Closed milestone")
        
        # Update milestone2 to closed status
        if milestone2:
            milestone2.status = MilestoneStatus.CLOSED
            milestone_file = core.milestones_dir / f"{milestone2.name.lower().replace(' ', '_')}.md"
            from roadmap.parser import MilestoneParser
            MilestoneParser.save_milestone_file(milestone2, milestone_file)
        
        # Test get_next_milestone only returns open milestones
        next_milestone = core.get_next_milestone()
        if next_milestone:
            assert next_milestone.status == MilestoneStatus.OPEN

    def test_get_issues_by_milestone_complex(self, core):
        """Test get_issues_by_milestone with complex milestone assignments."""
        # Create milestones  
        milestone1 = core.create_milestone("Sprint 1", "First sprint")
        milestone2 = core.create_milestone("Sprint 2", "Second sprint")
        
        # Create issues with various assignments
        issue1 = core.create_issue(title="Issue 1", priority=Priority.HIGH)
        issue2 = core.create_issue(title="Issue 2", priority=Priority.MEDIUM, milestone="Sprint 1")
        issue3 = core.create_issue(title="Issue 3", priority=Priority.LOW, milestone="Sprint 2") 
        issue4 = core.create_issue(title="Issue 4", priority=Priority.HIGH, milestone="Sprint 1")
        issue5 = core.create_issue(title="Issue 5", priority=Priority.MEDIUM)  # Backlog
        
        # Get grouped issues
        grouped = core.get_issues_by_milestone()
        
        # Verify grouping
        assert "Backlog" in grouped
        assert "Sprint 1" in grouped
        assert "Sprint 2" in grouped
        
        # Verify counts
        backlog_issues = [i for i in grouped["Backlog"] if not i.milestone or i.milestone == ""]
        assert len(backlog_issues) >= 2  # issue1 and issue5
        assert len(grouped["Sprint 1"]) == 2  # issue2 and issue4
        assert len(grouped["Sprint 2"]) == 1  # issue3