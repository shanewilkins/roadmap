"""Comprehensive tests for core roadmap functionality - targeting 85%+ coverage."""

import os
import tempfile
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import patch

import pytest

from roadmap.application.core import RoadmapCore
from roadmap.domain import (
    IssueType,
    MilestoneStatus,
    Priority,
    Status,
)

pytestmark = pytest.mark.unit


@pytest.fixture
def temp_dir():
    """Create a temporary directory for testing."""
    with tempfile.TemporaryDirectory() as temp_dir:
        yield Path(temp_dir)


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
        milestone = core.create_milestone(
            name="Test Milestone",
            description="Original description",
            due_date=datetime.now() + timedelta(days=30),
        )
        assert milestone is not None

        # Update milestone
        result = core.update_milestone(
            name="Test Milestone",
            description="Updated description",
            status=MilestoneStatus.OPEN,
        )
        assert result is True

        # Verify updates
        updated_milestone = core.get_milestone("Test Milestone")
        assert updated_milestone.description == "Updated description"
        assert updated_milestone.status == MilestoneStatus.OPEN

    def test_update_milestone_clear_due_date(self, core):
        """Test clearing due date from milestone."""
        # Create milestone with due date
        milestone = core.create_milestone(
            name="Test Milestone",
            description="Description",
            due_date=datetime.now() + timedelta(days=30),
        )
        assert milestone.due_date is not None

        # Clear due date
        result = core.update_milestone(name="Test Milestone", clear_due_date=True)
        assert result is True

        # Verify due date is cleared
        updated_milestone = core.get_milestone("Test Milestone")
        assert updated_milestone.due_date is None

    def test_update_milestone_nonexistent(self, core):
        """Test updating nonexistent milestone."""
        result = core.update_milestone(
            name="Nonexistent Milestone", description="New description"
        )
        assert result is False

    def test_update_milestone_not_initialized(self, temp_dir):
        """Test updating milestone on uninitialized roadmap."""
        core = RoadmapCore(temp_dir)  # Not initialized

        with pytest.raises(ValueError, match="Roadmap not initialized"):
            core.update_milestone(name="Test Milestone", description="Description")

    def test_update_milestone_save_error(self, core):
        """Test milestone update with save error."""
        # Create milestone first
        milestone = core.create_milestone(
            name="Test Milestone", description="Original description"
        )
        assert milestone is not None

        # Mock parser to raise exception
        with patch("roadmap.parser.MilestoneParser.save_milestone_file") as mock_save:
            mock_save.side_effect = Exception("Save failed")

            result = core.update_milestone(
                name="Test Milestone", description="Updated description"
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
        issue = core.create_issue(title="Test Issue", priority=Priority.MEDIUM)
        core.create_milestone(
            name="Test Milestone", description="Milestone description"
        )

        # Assign issue to milestone
        result = core.assign_issue_to_milestone(issue.id, "Test Milestone")
        assert result is True

        # Verify assignment
        updated_issue = core.get_issue(issue.id)
        assert updated_issue.milestone == "Test Milestone"

    def test_assign_issue_to_milestone_issue_not_found(self, core):
        """Test assigning nonexistent issue to milestone."""
        # Create milestone
        core.create_milestone(
            name="Test Milestone", description="Milestone description"
        )

        result = core.assign_issue_to_milestone("nonexistent-id", "Test Milestone")
        assert result is False

    def test_assign_issue_to_milestone_milestone_not_found(self, core):
        """Test assigning issue to nonexistent milestone."""
        # Create issue
        issue = core.create_issue(title="Test Issue", priority=Priority.MEDIUM)

        result = core.assign_issue_to_milestone(issue.id, "Nonexistent Milestone")
        assert result is False

    def test_assign_issue_to_milestone_both_not_found(self, core):
        """Test assigning nonexistent issue to nonexistent milestone."""
        result = core.assign_issue_to_milestone(
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
        core.create_milestone(
            name="Test Milestone", description="Milestone description"
        )

        # Create issues with different statuses
        issue1 = core.create_issue(title="Issue 1", priority=Priority.HIGH)
        issue2 = core.create_issue(title="Issue 2", priority=Priority.MEDIUM)
        issue3 = core.create_issue(title="Issue 3", priority=Priority.LOW)

        # Update their statuses after creation
        core.update_issue(issue1.id, status=Status.DONE)
        core.update_issue(issue2.id, status=Status.IN_PROGRESS)
        core.update_issue(issue3.id, status=Status.TODO)

        # Assign all issues to milestone
        core.assign_issue_to_milestone(issue1.id, "Test Milestone")
        core.assign_issue_to_milestone(issue2.id, "Test Milestone")
        core.assign_issue_to_milestone(issue3.id, "Test Milestone")

        # Get progress
        progress = core.get_milestone_progress("Test Milestone")

        assert progress["total"] == 3
        assert progress["completed"] == 1
        assert (
            abs(progress["progress"] - (100.0 / 3)) < 0.01
        )  # 1/3 * 100, approximately
        assert progress["by_status"]["done"] == 1
        assert progress["by_status"]["in-progress"] == 1
        assert progress["by_status"]["todo"] == 1

    def test_get_milestone_progress_no_issues(self, core):
        """Test milestone progress with no assigned issues."""
        # Create milestone with no issues
        core.create_milestone(name="Empty Milestone", description="No issues assigned")

        progress = core.get_milestone_progress("Empty Milestone")

        assert progress["total"] == 0
        assert progress["completed"] == 0
        assert progress["progress"] == 0.0
        assert progress["by_status"] == {}

    def test_get_milestone_progress_nonexistent_milestone(self, core):
        """Test progress for nonexistent milestone."""
        progress = core.get_milestone_progress("Nonexistent Milestone")

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
        core.create_milestone(
            name="Test Milestone", description="Milestone description"
        )

        # Create issues - some assigned, some not
        issue1 = core.create_issue(title="Assigned Issue", priority=Priority.HIGH)
        core.create_issue(title="Backlog Issue 1", priority=Priority.MEDIUM)
        core.create_issue(title="Backlog Issue 2", priority=Priority.LOW)

        # Assign one issue to milestone
        core.assign_issue_to_milestone(issue1.id, "Test Milestone")

        # Get backlog
        backlog = core.get_backlog_issues()

        # Should only contain unassigned issues
        assert len(backlog) == 2
        backlog_titles = [issue.title for issue in backlog]
        assert "Backlog Issue 1" in backlog_titles
        assert "Backlog Issue 2" in backlog_titles
        assert "Assigned Issue" not in backlog_titles

    def test_get_backlog_issues_empty(self, core):
        """Test getting backlog when all issues are assigned."""
        # Create milestone
        core.create_milestone(
            name="Test Milestone", description="Milestone description"
        )

        # Create issue and assign it
        issue = core.create_issue(title="Assigned Issue", priority=Priority.HIGH)
        core.assign_issue_to_milestone(issue.id, "Test Milestone")

        # Backlog should be empty
        backlog = core.get_backlog_issues()
        assert len(backlog) == 0

    def test_get_milestone_issues(self, core):
        """Test getting issues for specific milestone."""
        # Create milestones
        core.create_milestone(name="Milestone 1", description="First milestone")
        core.create_milestone(name="Milestone 2", description="Second milestone")

        # Create issues
        issue1 = core.create_issue(title="Issue for M1", priority=Priority.HIGH)
        issue2 = core.create_issue(title="Issue for M2", priority=Priority.MEDIUM)
        issue3 = core.create_issue(title="Another for M1", priority=Priority.LOW)

        # Assign issues to milestones
        core.assign_issue_to_milestone(issue1.id, "Milestone 1")
        core.assign_issue_to_milestone(issue2.id, "Milestone 2")
        core.assign_issue_to_milestone(issue3.id, "Milestone 1")

        # Get milestone 1 issues
        m1_issues = core.get_milestone_issues("Milestone 1")
        assert len(m1_issues) == 2
        m1_titles = [issue.title for issue in m1_issues]
        assert "Issue for M1" in m1_titles
        assert "Another for M1" in m1_titles

        # Get milestone 2 issues
        m2_issues = core.get_milestone_issues("Milestone 2")
        assert len(m2_issues) == 1
        assert m2_issues[0].title == "Issue for M2"

    def test_get_milestone_issues_empty(self, core):
        """Test getting issues for milestone with no assignments."""
        # Create milestone
        core.create_milestone(name="Empty Milestone", description="No issues assigned")

        # Create unassigned issue
        core.create_issue(title="Unassigned Issue", priority=Priority.MEDIUM)

        # Should return empty list
        issues = core.get_milestone_issues("Empty Milestone")
        assert len(issues) == 0

    def test_get_milestone_issues_nonexistent_milestone(self, core):
        """Test getting issues for nonexistent milestone."""
        issues = core.get_milestone_issues("Nonexistent Milestone")
        assert len(issues) == 0


class TestRoadmapCoreErrorHandling:
    """Test error handling and edge cases."""

    @pytest.fixture
    def core(self, temp_dir):
        """Create and initialize RoadmapCore for testing."""
        core = RoadmapCore(temp_dir)
        core.initialize()
        return core

    def test_operations_on_uninitialized_roadmap(self, temp_dir):
        """Test various operations on uninitialized roadmap."""
        core = RoadmapCore(temp_dir)  # Not initialized

        # All these should raise ValueError
        with pytest.raises(ValueError, match="Roadmap not initialized"):
            core.create_issue("Test", "Description")

        with pytest.raises(ValueError, match="Roadmap not initialized"):
            core.list_issues()

        with pytest.raises(ValueError, match="Roadmap not initialized"):
            core.create_milestone("Test", "Description")

        with pytest.raises(ValueError, match="Roadmap not initialized"):
            core.list_milestones()

    def test_find_existing_roadmap_permission_error(self, temp_dir):
        """Test find_existing_roadmap with permission errors."""
        # Create a directory we can't read
        restricted_dir = temp_dir / "restricted"
        restricted_dir.mkdir()

        # Make it unreadable (on systems that support it)
        try:
            restricted_dir.chmod(0o000)

            # Should handle permission error gracefully
            result = RoadmapCore.find_existing_roadmap(temp_dir)
            assert result is None  # Should not crash

        except (OSError, PermissionError):
            # Some systems don't support chmod restrictions
            pass
        finally:
            # Restore permissions for cleanup
            try:
                restricted_dir.chmod(0o755)
            except (OSError, PermissionError):
                pass

    def test_list_issues_with_file_errors(self, core):
        """Test issue listing with file system errors."""
        # Create a corrupted issue file
        corrupted_file = core.issues_dir / "corrupted.md"
        corrupted_file.write_text(
            "This is not valid issue content\nNo frontmatter here"
        )

        # Should handle gracefully and return valid issues only
        issues = core.list_issues()
        # The corrupted file should be ignored, empty list returned
        assert isinstance(issues, list)

    def test_list_milestones_with_file_errors(self, core):
        """Test milestone listing with file system errors."""
        # Create a corrupted milestone file
        corrupted_file = core.milestones_dir / "corrupted.md"
        corrupted_file.write_text("This is not valid milestone content")

        # Should handle gracefully
        milestones = core.list_milestones()
        assert isinstance(milestones, list)


class TestRoadmapCoreFilteringAndSearch:
    """Test advanced filtering and search capabilities."""

    @pytest.fixture
    def core_with_data(self, temp_dir):
        """Create core with sample data for testing."""
        core = RoadmapCore(temp_dir)
        core.initialize()

        # Create sample issues with various attributes
        issue1 = core.create_issue(
            title="Bug Fix",
            priority=Priority.HIGH,
            issue_type=IssueType.BUG,
            assignee="alice@example.com",
        )
        issue2 = core.create_issue(
            title="New Feature",
            priority=Priority.MEDIUM,
            issue_type=IssueType.FEATURE,
            assignee="bob@example.com",
        )
        issue3 = core.create_issue(
            title="Documentation Update",
            priority=Priority.LOW,
            issue_type=IssueType.OTHER,
            assignee="alice@example.com",
        )

        # Update statuses after creation
        core.update_issue(issue1.id, status=Status.IN_PROGRESS)
        core.update_issue(issue2.id, status=Status.TODO)
        core.update_issue(issue3.id, status=Status.DONE)

        return core

    def test_list_issues_filter_by_priority(self, core_with_data):
        """Test filtering issues by priority."""
        high_priority = core_with_data.list_issues(priority=Priority.HIGH)
        assert len(high_priority) == 1
        assert high_priority[0].title == "Bug Fix"

        medium_priority = core_with_data.list_issues(priority=Priority.MEDIUM)
        assert len(medium_priority) == 1
        assert medium_priority[0].title == "New Feature"

    def test_list_issues_filter_by_status(self, core_with_data):
        """Test filtering issues by status."""
        in_progress = core_with_data.list_issues(status=Status.IN_PROGRESS)
        assert len(in_progress) == 1
        assert in_progress[0].title == "Bug Fix"

        completed = core_with_data.list_issues(status=Status.DONE)
        assert len(completed) == 1
        assert completed[0].title == "Documentation Update"

    def test_list_issues_filter_by_assignee(self, core_with_data):
        """Test filtering issues by assignee."""
        alice_issues = core_with_data.list_issues(assignee="alice@example.com")
        assert len(alice_issues) == 2
        alice_titles = [issue.title for issue in alice_issues]
        assert "Bug Fix" in alice_titles
        assert "Documentation Update" in alice_titles

        bob_issues = core_with_data.list_issues(assignee="bob@example.com")
        assert len(bob_issues) == 1
        assert bob_issues[0].title == "New Feature"

    def test_list_issues_filter_by_type(self, core_with_data):
        """Test filtering issues by type."""
        bugs = core_with_data.list_issues(issue_type=IssueType.BUG)
        assert len(bugs) == 1
        assert bugs[0].title == "Bug Fix"

        features = core_with_data.list_issues(issue_type=IssueType.FEATURE)
        assert len(features) == 1
        assert features[0].title == "New Feature"

    def test_list_issues_multiple_filters(self, core_with_data):
        """Test filtering issues with multiple criteria."""
        # Filter by assignee and status
        alice_completed = core_with_data.list_issues(
            assignee="alice@example.com", status=Status.DONE
        )
        assert len(alice_completed) == 1
        assert alice_completed[0].title == "Documentation Update"

        # Filter with no matches
        no_matches = core_with_data.list_issues(
            assignee="alice@example.com", priority=Priority.MEDIUM
        )
        assert len(no_matches) == 0


class TestRoadmapCoreAdvancedOperations:
    """Test advanced roadmap operations and integrations."""

    @pytest.fixture
    def core(self, temp_dir):
        """Create and initialize RoadmapCore for testing."""
        core = RoadmapCore(temp_dir)
        core.initialize()
        return core

    def test_initialize_already_initialized(self, core):
        """Test initializing already initialized roadmap."""
        # Should raise error on re-initialization
        with pytest.raises(ValueError, match="Roadmap already initialized"):
            core.initialize()

    def test_custom_roadmap_directory_name(self, temp_dir):
        """Test using custom roadmap directory name."""
        custom_name = "my-custom-roadmap"
        core = RoadmapCore(temp_dir, roadmap_dir_name=custom_name)
        core.initialize()

        assert core.roadmap_dir.name == custom_name
        assert core.roadmap_dir.exists()
        assert core.is_initialized()

    def test_roadmap_structure_validation(self, core):
        """Test that roadmap creates proper directory structure."""
        assert core.roadmap_dir.exists()
        assert core.issues_dir.exists()
        assert core.milestones_dir.exists()
        assert core.projects_dir.exists()
        assert core.templates_dir.exists()
        assert core.artifacts_dir.exists()
        assert core.config_file.exists()

    def test_git_integration_initialization(self, core):
        """Test that git integration is properly initialized."""
        assert core.git is not None
        # Check if git integration has the repository path
        assert hasattr(core.git, "repo_path")
        assert core.git.repo_path == core.root_path

    @patch("roadmap.parser.IssueParser.save_issue_file")
    def test_security_integration(self, mock_save, core):
        """Test that security functions are used in operations."""
        # IssueParser.save_issue_file should be called during issue creation
        core.create_issue("Test Issue")

        # Verify parser save function was called (which uses security functions)
        mock_save.assert_called_once()
