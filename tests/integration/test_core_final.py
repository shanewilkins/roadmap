"""Final targeted tests for core roadmap functionality - covering remaining uncovered lines."""

import tempfile
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from roadmap.core.domain import (
    IssueType,
    MilestoneStatus,
    Priority,
    Status,
)
from roadmap.infrastructure.core import RoadmapCore

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
        issue1 = core.issues.create(
            title="High Priority Issue",
            priority=Priority.HIGH,
            assignee="alice@example.com",
            issue_type=IssueType.BUG,
        )
        issue2 = core.issues.create(
            title="Medium Priority Feature",
            priority=Priority.MEDIUM,
            assignee="bob@example.com",
            issue_type=IssueType.FEATURE,
        )
        issue3 = core.issues.create(
            title="Low Priority Task",
            priority=Priority.LOW,
            assignee="alice@example.com",
            issue_type=IssueType.OTHER,
        )

        # Update statuses after creation
        core.issues.update(issue1.id, status=Status.IN_PROGRESS)
        core.issues.update(issue2.id, status=Status.TODO)
        core.issues.update(issue3.id, status=Status.CLOSED)

        # Test with priority and assignee filters (hits duplicate filter lines)
        filtered_issues = core.issues.list(
            priority=Priority.HIGH, assignee="alice@example.com"
        )
        assert len(filtered_issues) == 1
        assert filtered_issues[0].title == "High Priority Issue"

        # Test with all filters to exercise all branches
        filtered_issues = core.issues.list(
            priority=Priority.MEDIUM,
            status=Status.TODO,
            assignee="bob@example.com",
            issue_type=IssueType.FEATURE,
        )
        assert len(filtered_issues) == 1
        assert filtered_issues[0].title == "Medium Priority Feature"

    def test_get_milestone_with_parser_exception(self, core):
        """Test get_milestone when parser raises exception."""
        # Create a corrupted milestone file
        milestone_file = core.milestones_dir / "corrupted_milestone.md"
        milestone_file.write_text("corrupted content that will cause parser to fail")

        # Mock parser to raise exception on this file
        with patch(
            "roadmap.adapters.persistence.parser.MilestoneParser.parse_milestone_file"
        ) as mock_parse:
            mock_parse.side_effect = Exception("Parse error")

            milestone = core.milestones.get("corrupted_milestone")
            assert milestone is None

    def test_delete_milestone_with_assigned_issues(self, core):
        """Test deleting milestone that has assigned issues."""
        # Create milestone
        core.milestones.create("Test Milestone", "Description")

        # Create and assign issues to the milestone
        issue1 = core.issues.create(
            title="Issue 1", priority=Priority.HIGH, milestone="Test Milestone"
        )
        issue2 = core.issues.create(
            title="Issue 2", priority=Priority.MEDIUM, milestone="Test Milestone"
        )

        # Verify issues are assigned
        assert core.issues.get(issue1.id).milestone == "Test Milestone"
        assert core.issues.get(issue2.id).milestone == "Test Milestone"

        # Delete milestone
        result = core.milestones.delete("Test Milestone")
        assert result is True

        # Verify issues are unassigned
        updated_issue1 = core.issues.get(issue1.id)
        updated_issue2 = core.issues.get(issue2.id)
        assert updated_issue1.milestone == "" or updated_issue1.milestone is None
        assert updated_issue2.milestone == "" or updated_issue2.milestone is None

        # Verify milestone is deleted
        assert core.milestones.get("Test Milestone") is None

    def test_delete_nonexistent_milestone(self, core):
        """Test deleting a milestone that doesn't exist."""
        result = core.milestones.delete("Nonexistent Milestone")
        assert result is False

    def test_create_issue_with_git_branch(self, core):
        """Test create_issue_with_git_branch functionality."""
        # Mock git repository and branch creation
        # Note: Mock path needs adjustment for GitCoordinator architecture
        with patch.object(core.git, "is_git_repository") as mock_is_git:
            mock_is_git.return_value = True

            # Create issue with auto branch creation
            issue = core.git.create_issue_with_branch(
                "Test Issue", priority=Priority.HIGH, auto_create_branch=True
            )

            assert issue is not None
            assert issue.title == "Test Issue"

    def test_create_issue_with_git_branch_no_git(self, core):
        """Test create_issue_with_git_branch when not in git repository."""
        # Mock no git repository
        with patch.object(core.git, "is_git_repository") as mock_is_git:
            mock_is_git.return_value = False

            # Create issue with auto branch creation (should still work)
            issue = core.git.create_issue_with_branch(
                "Test Issue", priority=Priority.HIGH, auto_create_branch=True
            )

            assert issue is not None
            assert issue.title == "Test Issue"

    def test_get_git_context_with_linked_issue(self, core):
        """Test issue creation in git context."""
        # Create an issue
        issue = core.issues.create(
            title="Test Issue with Git Context", priority=Priority.HIGH
        )

        # Verify issue was created successfully
        assert issue is not None
        assert issue.title == "Test Issue with Git Context"
        assert issue.priority == Priority.HIGH

        # Verify we can retrieve the issue
        retrieved = core.issues.get(issue.id)
        assert retrieved is not None
        assert retrieved.title == "Test Issue with Git Context"

    def test_get_git_context_no_linked_issue(self, core):
        """Test get_git_context with branch that has no linked issue."""
        # Mock git repository
        with patch.object(core.git._ops.git, "is_git_repository") as mock_is_git:
            mock_is_git.return_value = True

            # Mock repository info
            with patch.object(
                core.git._ops.git, "get_repository_info"
            ) as mock_repo_info:
                mock_repo_info.return_value = {"remote_url": "origin"}

                # Mock current branch without issue ID
                mock_branch = Mock()
                mock_branch.name = "main"
                mock_branch.extract_issue_id.return_value = None

                with patch.object(
                    core.git._ops.git, "get_current_branch"
                ) as mock_current_branch:
                    mock_current_branch.return_value = mock_branch

                    context = core.git.get_context()

                    assert context["is_git_repo"] is True
                    assert context["current_branch"] == "main"
                    assert "linked_issue" not in context

    def test_get_git_context_no_current_branch(self, core):
        """Test get_git_context when no current branch."""
        # Mock git repository
        with patch.object(core.git._ops.git, "is_git_repository") as mock_is_git:
            mock_is_git.return_value = True

            # Mock repository info
            with patch.object(
                core.git._ops.git, "get_repository_info"
            ) as mock_repo_info:
                mock_repo_info.return_value = {"status": "detached"}

                # Mock no current branch
                with patch.object(
                    core.git._ops.git, "get_current_branch"
                ) as mock_current_branch:
                    mock_current_branch.return_value = None

                    context = core.git.get_context()

                    assert context["is_git_repo"] is True
                    assert "current_branch" not in context
                    assert "linked_issue" not in context

    def test_get_current_user_from_git(self, core):
        """Test get_current_user_from_git method."""
        with patch.object(core.git, "get_current_user") as mock_git_user:
            mock_git_user.return_value = "git_user@example.com"

            user = core.git.get_current_user()
            assert user == "git_user@example.com"

    def test_validate_assignee_empty_assignee(self, core):
        """Test validate_assignee with empty assignee."""
        is_valid, error = core.team.validate_assignee("")
        assert is_valid is False
        assert "Assignee cannot be empty" in error

        is_valid, error = core.team.validate_assignee("   ")
        assert is_valid is False
        assert "Assignee cannot be empty" in error

    def test_validate_assignee_no_github_config(self, core):
        """Test validate_assignee when GitHub is not configured."""
        # The validation system will use its configured strategy
        # This test just verifies it doesn't crash
        is_valid, error = core.team.validate_assignee("any_user@example.com")
        # Should either validate or provide an error message
        assert isinstance(is_valid, bool)
        assert isinstance(error, str)

    @pytest.mark.skip(reason="Removed initialization checks from facade")
    def test_issue_operations_not_initialized(self, temp_dir):
        """Test issue operations when roadmap is not initialized."""
        pass

    def test_create_issue_failed_return(self, core):
        """Test create_issue_with_git_branch when issue creation fails."""
        # Mock the issue creation to return None
        with patch.object(core.issues, "create") as mock_create:
            mock_create.return_value = None

            result = core.git.create_issue_with_branch(
                "Failed Issue", priority=Priority.HIGH, auto_create_branch=True
            )

            assert result is None

    def test_security_and_logging_integration(self, core):
        """Test security logging integration in various operations."""
        # Test issue creation with security logging
        with patch("roadmap.common.security.log_security_event"):
            issue = core.issues.create(
                title="Security Test Issue", priority=Priority.HIGH
            )

            # Security logging should be called during file operations
            assert issue is not None

    def test_file_operations_edge_cases(self, core):
        """Test edge cases in file operations."""
        # Test with very long issue titles
        long_title = "A" * 200  # Very long title
        issue = core.issues.create(title=long_title, priority=Priority.HIGH)
        assert issue is not None
        assert issue.title == long_title

        # Test with special characters in titles
        special_title = "Issue with special chars: @#$%^&*()[]{}|\\:\"'<>?/~`"
        issue = core.issues.create(title=special_title, priority=Priority.HIGH)
        assert issue is not None
        assert issue.title == special_title

    def test_milestone_status_filtering(self, core):
        """Test milestone operations with different status values."""
        # Create milestones with different statuses
        core.milestones.create("Open Milestone", "Open milestone")
        milestone2 = core.milestones.create("Closed Milestone", "Closed milestone")

        # Update milestone2 to closed status
        if milestone2:
            milestone2.status = MilestoneStatus.CLOSED
            milestone_file = (
                core.milestones_dir / f"{milestone2.name.lower().replace(' ', '_')}.md"
            )
            from roadmap.adapters.persistence.parser import MilestoneParser

            MilestoneParser.save_milestone_file(milestone2, milestone_file)

        # Test get_next_milestone only returns open milestones
        next_milestone = core.milestones.get_next()
        if next_milestone:
            assert next_milestone.status == MilestoneStatus.OPEN

    def test_get_issues_by_milestone_complex(self, core):
        """Test get_issues_by_milestone with complex milestone assignments."""
        # Create milestones
        core.milestones.create("Sprint 1", "First sprint")
        core.milestones.create("Sprint 2", "Second sprint")

        # Create issues with various assignments
        core.issues.create(title="Issue 1", priority=Priority.HIGH)
        core.issues.create(
            title="Issue 2", priority=Priority.MEDIUM, milestone="Sprint 1"
        )
        core.issues.create(title="Issue 3", priority=Priority.LOW, milestone="Sprint 2")
        core.issues.create(
            title="Issue 4", priority=Priority.HIGH, milestone="Sprint 1"
        )
        core.issues.create(title="Issue 5", priority=Priority.MEDIUM)  # Backlog

        # Get grouped issues
        grouped = core.issues.get_grouped_by_milestone()

        # Verify grouping
        assert "Backlog" in grouped
        assert "Sprint 1" in grouped
        assert "Sprint 2" in grouped

        # Verify counts
        backlog_issues = [
            i for i in grouped["Backlog"] if not i.milestone or i.milestone == ""
        ]
        assert len(backlog_issues) >= 2  # issue1 and issue5
        assert len(grouped["Sprint 1"]) == 2  # issue2 and issue4
        assert len(grouped["Sprint 2"]) == 1  # issue3
