"""Comprehensive tests for core roadmap functionality - targeting 85%+ coverage."""

from unittest.mock import patch

import pytest

from roadmap.core.domain import (
    IssueType,
    Priority,
    Status,
)
from roadmap.infrastructure.core import RoadmapCore

pytestmark = pytest.mark.unit


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
        core = RoadmapCore(temp_dir)  # Not explicitly initialized

        # Note: Operations work without explicit initialization
        # The code auto-initializes as needed
        from roadmap.core.domain import Priority

        # These operations now work without explicit initialization
        issue = core.issues.create("Test", priority=Priority.HIGH)
        assert issue is not None
        assert issue.title == "Test"

        issues = core.issues.list()
        assert isinstance(issues, list)

        # Milestones also work without explicit initialization
        milestone = core.milestones.create("Test", "Description")
        assert milestone is not None

        milestones = core.milestones.list()
        assert isinstance(milestones, list)

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
        issues = core.issues.list()
        # The corrupted file should be ignored, empty list returned
        assert isinstance(issues, list)

    def test_list_milestones_with_file_errors(self, core):
        """Test milestone listing with file system errors."""
        # Create a corrupted milestone file
        corrupted_file = core.milestones_dir / "corrupted.md"
        corrupted_file.write_text("This is not valid milestone content")

        # Should handle gracefully
        milestones = core.milestones.list()
        assert isinstance(milestones, list)


class TestRoadmapCoreFilteringAndSearch:
    """Test advanced filtering and search capabilities."""

    @pytest.fixture
    def core_with_data(self, temp_dir):
        """Create core with sample data for testing."""
        core = RoadmapCore(temp_dir)
        core.initialize()

        # Create sample issues with various attributes
        issue1 = core.issues.create(
            title="Bug Fix",
            priority=Priority.HIGH,
            issue_type=IssueType.BUG,
            assignee="alice@example.com",
        )
        issue2 = core.issues.create(
            title="New Feature",
            priority=Priority.MEDIUM,
            issue_type=IssueType.FEATURE,
            assignee="bob@example.com",
        )
        issue3 = core.issues.create(
            title="Documentation Update",
            priority=Priority.LOW,
            issue_type=IssueType.OTHER,
            assignee="alice@example.com",
        )

        # Update statuses after creation
        core.issues.update(issue1.id, status=Status.IN_PROGRESS)
        core.issues.update(issue2.id, status=Status.TODO)
        core.issues.update(issue3.id, status=Status.CLOSED)

        return core

    def test_list_issues_filter_by_priority(self, core_with_data):
        """Test filtering issues by priority."""
        high_priority = core_with_data.issues.list(priority=Priority.HIGH)
        assert len(high_priority) == 1
        assert high_priority[0].title == "Bug Fix"

        medium_priority = core_with_data.issues.list(priority=Priority.MEDIUM)
        assert len(medium_priority) == 1
        assert medium_priority[0].title == "New Feature"

    def test_list_issues_filter_by_status(self, core_with_data):
        """Test filtering issues by status."""
        in_progress = core_with_data.issues.list(status=Status.IN_PROGRESS)
        assert len(in_progress) == 1
        assert in_progress[0].title == "Bug Fix"

        completed = core_with_data.issues.list(status=Status.CLOSED)
        assert len(completed) == 1
        assert completed[0].title == "Documentation Update"

    def test_list_issues_filter_by_assignee(self, core_with_data):
        """Test filtering issues by assignee."""
        alice_issues = core_with_data.issues.list(assignee="alice@example.com")
        assert len(alice_issues) == 2
        alice_titles = [issue.title for issue in alice_issues]
        assert "Bug Fix" in alice_titles
        assert "Documentation Update" in alice_titles

        bob_issues = core_with_data.issues.list(assignee="bob@example.com")
        assert len(bob_issues) == 1
        assert bob_issues[0].title == "New Feature"

    def test_list_issues_filter_by_type(self, core_with_data):
        """Test filtering issues by type."""
        bugs = core_with_data.issues.list(issue_type=IssueType.BUG)
        assert len(bugs) == 1
        assert bugs[0].title == "Bug Fix"

        features = core_with_data.issues.list(issue_type=IssueType.FEATURE)
        assert len(features) == 1
        assert features[0].title == "New Feature"

    def test_list_issues_multiple_filters(self, core_with_data):
        """Test filtering issues with multiple criteria."""
        # Filter by assignee and status
        alice_completed = core_with_data.issues.list(
            assignee="alice@example.com", status=Status.CLOSED
        )
        assert len(alice_completed) == 1
        assert alice_completed[0].title == "Documentation Update"

        # Filter with no matches
        no_matches = core_with_data.issues.list(
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

    @patch("roadmap.adapters.persistence.parser.IssueParser.save_issue_file")
    def test_security_integration(self, mock_save, core):
        """Test that security functions are used in operations."""
        # IssueParser.save_issue_file should be called during issue creation
        core.issues.create("Test Issue")

        # Verify parser save function was called (which uses security functions)
        mock_save.assert_called_once()
