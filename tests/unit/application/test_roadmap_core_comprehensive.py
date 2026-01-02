"""Comprehensive tests for RoadmapCore - basic, edge cases, and uncovered lines.

Tests cover:
- Core initialization and setup
- CRUD operations for issues and milestones
- Edge cases and error handling
- Uncovered code paths and special scenarios
"""

import os
from datetime import datetime
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
from tests.unit.application.test_data_factory import TestDataFactory


class TestRoadmapCore:
    """Test cases for RoadmapCore basic functionality."""

    @pytest.fixture
    def core(self, temp_dir):
        """Create RoadmapCore instance for testing."""
        return RoadmapCore(temp_dir)

    def test_initialization(self, temp_dir):
        """Test core initialization."""
        core = RoadmapCore(temp_dir)
        assert core.root_path == temp_dir
        assert core.roadmap_dir == temp_dir / ".roadmap"
        assert core.issues_dir == temp_dir / ".roadmap" / "issues"
        assert core.milestones_dir == temp_dir / ".roadmap" / "milestones"
        assert core.templates_dir == temp_dir / ".roadmap" / "templates"
        assert core.config_file == temp_dir / ".roadmap" / "config.yaml"

    def test_is_initialized_false(self, core):
        """Test is_initialized returns False when not initialized."""
        assert not core.is_initialized()

    def test_is_initialized_true(self, core):
        """Test is_initialized returns True when initialized."""
        core.initialize()
        assert core.is_initialized()

    def test_initialize_creates_directories(self, core):
        """Test initialization creates required directories."""
        core.initialize()

        assert core.roadmap_dir.exists()
        assert core.issues_dir.exists()
        assert core.milestones_dir.exists()
        assert core.templates_dir.exists()
        assert core.config_file.exists()

    def test_initialize_creates_templates(self, core):
        """Test initialization creates template files."""
        core.initialize()

        issue_template = core.templates_dir / "issue.md"
        milestone_template = core.templates_dir / "milestone.md"
        project_template = core.templates_dir / "project.md"

        assert issue_template.exists()
        assert milestone_template.exists()
        assert project_template.exists()

    def test_initialize_creates_issue_template_content(self, core):
        """Test issue template contains required placeholders."""
        core.initialize()

        issue_template = core.templates_dir / "issue.md"
        issue_content = issue_template.read_text()

        assert "{{ title }}" in issue_content
        assert "priority:" in issue_content

    def test_initialize_creates_project_template_content(self, core):
        """Test project template contains required placeholders."""
        core.initialize()

        project_template = core.templates_dir / "project.md"
        project_content = project_template.read_text()

        assert "{{ project_name }}" in project_content
        assert "{{ project_owner }}" in project_content
        assert "start_date:" in project_content

    def test_initialize_creates_milestone_template_content(self, core):
        """Test milestone template contains required placeholders."""
        core.initialize()

        milestone_template = core.templates_dir / "milestone.md"
        milestone_content = milestone_template.read_text()

        assert "{{ milestone_name }}" in milestone_content

    def test_initialize_already_initialized_raises_error(self, core):
        """Test initializing already initialized roadmap raises error."""
        core.initialize()

        with pytest.raises(ValueError, match="already initialized"):
            core.initialize()

    def test_load_config(self, core):
        """Test loading configuration."""
        core.initialize()
        config = core.load_config()
        assert config is not None
        assert hasattr(config, "github")
        assert hasattr(config, "defaults")

    def test_load_config_not_initialized_raises_error(self, core):
        """Test loading config when not initialized raises error."""
        with pytest.raises(ValueError, match="not initialized"):
            core.load_config()

    def test_create_issue(self, core):
        """Test creating an issue."""
        core.initialize()

        issue = core.issues.create(
            title="Test Issue",
            priority=Priority.HIGH,
            milestone="v1.0",
            labels=["bug", "urgent"],
        )

        assert issue.title == "Test Issue"
        assert issue.priority == Priority.HIGH
        assert issue.milestone == "v1.0"
        assert issue.labels == ["bug", "urgent"]
        assert len(issue.id) == 8  # UUID prefix

        # Check file was created in the milestone directory
        issue_file = core.issues_dir / "v1.0" / issue.filename
        assert issue_file.exists()

    def test_list_issues_empty(self, core):
        """Test listing issues when none exist."""
        core.initialize()
        issues = core.issues.list()
        assert issues == []

    def test_list_issues_with_issues(self, core):
        """Test listing issues."""
        core.initialize()

        # Create test issues
        core.issues.create("Issue 1", Priority.HIGH)
        core.issues.create("Issue 2", Priority.LOW)
        core.issues.create("Issue 3", Priority.CRITICAL)

        issues = core.issues.list()

        # Should be sorted by priority
        assert len(issues) == 3
        assert issues[0].priority == Priority.CRITICAL
        assert issues[1].priority == Priority.HIGH
        assert issues[2].priority == Priority.LOW

    def test_list_issues_with_filters(self, core):
        """Test listing issues with filters."""
        core.initialize()

        # Create test issues
        core.issues.create("Issue 1", Priority.HIGH, milestone="v1.0")
        core.issues.create("Issue 2", Priority.LOW, milestone="v2.0")
        issue3 = core.issues.create("Issue 3", Priority.HIGH, milestone="v1.0")
        core.issues.update(issue3.id, status=Status.CLOSED)

        # Filter by milestone
        v1_issues = core.issues.list(milestone="v1.0")
        assert len(v1_issues) == 2

        # Filter by status
        done_issues = core.issues.list(status=Status.CLOSED)
        assert len(done_issues) == 1

        # Filter by priority
        high_issues = core.issues.list(priority=Priority.HIGH)
        assert len(high_issues) == 2

    def test_get_issue(self, core):
        """Test getting specific issue."""
        core.initialize()

        created_issue = core.issues.create("Test Issue")
        retrieved_issue = core.issues.get(created_issue.id)

        assert retrieved_issue is not None
        assert retrieved_issue.id == created_issue.id
        assert retrieved_issue.title == "Test Issue"

    def test_get_issue_not_found(self, core):
        """Test getting non-existent issue."""
        core.initialize()

        issue = core.issues.get("nonexistent")
        assert issue is None

    def test_update_issue(self, core):
        """Test updating an issue."""
        core.initialize()

        issue = core.issues.create("Test Issue", Priority.LOW)
        original_updated = issue.updated

        # Small delay to ensure timestamp difference
        import time

        time.sleep(0.01)

        updated_issue = core.issues.update(
            issue.id,
            priority=Priority.HIGH,
            status=Status.IN_PROGRESS,
            milestone="v1.0",
        )

        assert updated_issue is not None
        assert updated_issue.priority == Priority.HIGH
        assert updated_issue.status == Status.IN_PROGRESS
        assert updated_issue.milestone == "v1.0"
        assert updated_issue.updated > original_updated

    def test_update_issue_not_found(self, core):
        """Test updating non-existent issue."""
        core.initialize()

        result = core.issues.update("nonexistent", priority=Priority.HIGH)
        assert result is None

    def test_delete_issue(self, core):
        """Test deleting an issue."""
        core.initialize()

        issue = core.issues.create("Test Issue")
        # Issues without milestone go to backlog
        issue_file = core.issues_dir / "backlog" / issue.filename

        assert issue_file.exists()

        success = core.issues.delete(issue.id)
        assert success
        assert not issue_file.exists()

    def test_delete_issue_not_found(self, core):
        """Test deleting non-existent issue."""
        core.initialize()

        success = core.issues.delete("nonexistent")
        assert not success

    def test_create_milestone(self, core):
        """Test creating a milestone."""
        core.initialize()

        due_date = datetime(2025, 12, 31)
        milestone = core.milestones.create(
            name="v1.0", description="First release", due_date=due_date
        )

        assert milestone.name == "v1.0"
        assert milestone.description == "First release"
        assert milestone.due_date == due_date
        assert milestone.status == MilestoneStatus.OPEN

        # Check file was created
        milestone_file = core.milestones_dir / milestone.filename
        assert milestone_file.exists()

    def test_list_milestones(self, core):
        """Test listing milestones."""
        core.initialize()

        core.milestones.create("v1.0", "First release")
        core.milestones.create("v2.0", "Second release")

        milestones = core.milestones.list()

        assert len(milestones) == 2
        # Should be sorted by creation date
        assert milestones[0].created <= milestones[1].created

    def test_get_milestone(self, core):
        """Test getting specific milestone."""
        core.initialize()

        core.milestones.create("v1.0", "First release")
        retrieved_milestone = core.milestones.get("v1.0")

        assert retrieved_milestone is not None
        assert retrieved_milestone.name == "v1.0"
        assert retrieved_milestone.description == "First release"

    def test_get_milestone_not_found(self, core):
        """Test getting non-existent milestone."""
        core.initialize()

        milestone = core.milestones.get("nonexistent")
        assert milestone is None

    def test_assign_issue_to_milestone(self, core):
        """Test assigning issue to milestone."""
        core.initialize()

        issue = core.issues.create("Test Issue")
        core.milestones.create("v1.0", "First release")

        success = core.issues.assign_to_milestone(issue.id, "v1.0")
        assert success

        # Verify assignment
        updated_issue = core.issues.get(issue.id)
        assert updated_issue.milestone == "v1.0"

    def test_assign_issue_to_milestone_issue_not_found(self, core):
        """Test assigning non-existent issue to milestone."""
        core.initialize()

        core.milestones.create("v1.0", "First release")

        success = core.issues.assign_to_milestone("nonexistent", "v1.0")
        assert not success

    def test_assign_issue_to_milestone_milestone_not_found(self, core):
        """Test assigning issue to non-existent milestone."""
        core.initialize()

        issue = core.issues.create("Test Issue")
        original_milestone = issue.milestone

        # Assigning to a non-existent milestone returns False
        success = core.issues.assign_to_milestone(issue.id, "nonexistent")
        assert not success

        # Verify the assignment was NOT made (milestone should remain unchanged)
        updated_issue = core.issues.get(issue.id)
        assert updated_issue.milestone == original_milestone

    def test_get_milestone_progress(self, core):
        """Test getting milestone progress."""
        core.initialize()

        # Create milestone and issues
        core.milestones.create("v1.0", "First release")

        issue1 = core.issues.create("Issue 1")
        issue2 = core.issues.create("Issue 2")
        issue3 = core.issues.create("Issue 3")

        # Assign issues to milestone
        core.issues.assign_to_milestone(issue1.id, "v1.0")
        core.issues.assign_to_milestone(issue2.id, "v1.0")
        core.issues.assign_to_milestone(issue3.id, "v1.0")

        # Complete one issue
        core.issues.update(issue1.id, status=Status.CLOSED)

        progress = core.milestones.get_progress("v1.0")

        assert progress["completed"] == 1
        assert progress["completed"] == 1
        assert (
            abs(progress["progress"] - 33.333333333333336) < 0.000001
        )  # Allow for floating point precision
        assert progress["by_status"]["closed"] == 1
        assert progress["by_status"]["todo"] == 2

    def test_get_milestone_progress_no_issues(self, core):
        """Test milestone progress with no issues."""
        core.initialize()

        # Create milestone
        milestone_name = TestDataFactory.milestone_id()
        milestone_desc = TestDataFactory.message()
        core.milestones.create(milestone_name, milestone_desc)

        # Get progress
        progress = core.milestones.get_progress(milestone_name)

        assert progress["total"] == 0
        assert progress["completed"] == 0
        assert progress["progress"] == 0.0
        assert progress["by_status"] == {}

    def test_delete_milestone(self, core):
        """Test deleting a milestone."""

        # Create milestone and issue
        core.initialize()
        core.milestones.create("test-milestone", "Test milestone")
        issue = core.issues.create("Test issue")
        core.issues.assign_to_milestone(issue.id, "test-milestone")

        # Verify setup
        milestone = core.milestones.get("test-milestone")
        assert milestone is not None
        updated_issue = core.issues.get(issue.id)
        assert updated_issue.milestone == "test-milestone"

        # Delete milestone
        result = core.milestones.delete("test-milestone")
        assert result

        # Verify deletion
        deleted_milestone = core.milestones.get("test-milestone")
        assert deleted_milestone is None

        # Verify issue was unassigned
        unassigned_issue = core.issues.get(issue.id)
        assert unassigned_issue.milestone is None

    def test_delete_milestone_not_found(self, core):
        """Test deleting a non-existent milestone."""
        core.initialize()

        result = core.milestones.delete("non-existent")
        assert not result


class TestCoreEdgeCases:
    """Test edge cases and error handling in RoadmapCore."""

    @pytest.fixture
    def initialized_core(self, temp_dir):
        """Create an initialized roadmap core."""
        core = RoadmapCore(temp_dir)
        core.initialize()
        return core

    def test_list_issues_with_malformed_files(self, initialized_core):
        """Test listing issues when some files are malformed."""
        # Create a valid issue
        initialized_core.issues.create("Valid Issue")

        # Create a malformed file in the issues directory
        malformed_file = initialized_core.issues_dir / "backlog" / "malformed.md"
        malformed_file.write_text(
            "This is not a valid issue file\nwithout proper frontmatter"
        )

        # List issues should skip the malformed file and return only valid ones
        issues = initialized_core.issues.list()
        assert len(issues) == 1
        assert issues[0].title == "Valid Issue"

    def test_issue_file_permissions(self, initialized_core):
        """Test issue file is created with correct permissions."""
        issue = initialized_core.issues.create("Test Issue")
        issue_file = initialized_core.issues_dir / "backlog" / issue.filename

        # Check file is readable
        assert os.access(issue_file, os.R_OK)
        assert os.access(issue_file, os.W_OK)

    def test_concurrent_issue_creation(self, initialized_core):
        """Test creating multiple issues in quick succession."""
        issues = [initialized_core.issues.create(f"Issue {i}") for i in range(5)]

        # Verify all issues were created
        assert len(issues) == 5
        for i, issue in enumerate(issues):
            assert issue.title == f"Issue {i}"

    def test_milestone_with_special_characters(self, initialized_core):
        """Test creating milestone with special characters."""
        special_name = "v1.0-alpha+build.123"
        milestone = initialized_core.milestones.create(special_name, "Test")

        # Should be able to retrieve it
        retrieved = initialized_core.milestones.get(special_name)
        assert retrieved is not None
        assert retrieved.name == special_name

    def test_issue_title_with_unicode(self, initialized_core):
        """Test issue with unicode characters in title."""
        issue = initialized_core.issues.create("Fix: 🐛 在线编辑器")

        retrieved = initialized_core.issues.get(issue.id)
        assert retrieved is not None
        assert "🐛" in retrieved.title


class TestRoadmapCoreUncoveredLines:
    """Test specific uncovered lines and edge cases - coverage targeting."""

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

        # Test with status and assignee filters
        filtered_issues = core.issues.list(
            status=Status.IN_PROGRESS, assignee="alice@example.com"
        )
        assert len(filtered_issues) == 1

        # Test with issue_type filter
        feature_issues = core.issues.list(issue_type=IssueType.FEATURE)
        assert len(feature_issues) == 1
        assert feature_issues[0].id == issue2.id

    def test_milestone_operations_with_complex_names(self, core):
        """Test milestone operations with various name formats."""
        milestone_names = ["v1.0", "v2.0-beta", "release-2025-01-15", "2025.Q1.alpha"]

        for name in milestone_names:
            milestone = core.milestones.create(name, f"Milestone {name}")
            retrieved = core.milestones.get(name)
            assert retrieved is not None
            assert retrieved.name == name

        # List all milestones
        all_milestones = core.milestones.list()
        assert len(all_milestones) == len(milestone_names)

    def test_issue_lifecycle_full_workflow(self, core):
        """Test complete issue lifecycle from creation to closure."""
        # Create issue
        issue = core.issues.create(
            title="Complete Workflow Issue",
            priority=Priority.MEDIUM,
            issue_type=IssueType.FEATURE,
        )
        assert issue.status == Status.TODO

        # Assign to milestone
        core.milestones.create("v1.0", "First Release")
        core.issues.assign_to_milestone(issue.id, "v1.0")

        # Update status to in progress
        issue = core.issues.update(issue.id, status=Status.IN_PROGRESS)
        assert issue.status == Status.IN_PROGRESS

        # Mark as closed
        issue = core.issues.update(issue.id, status=Status.CLOSED)
        assert issue.status == Status.CLOSED

        # Verify final state
        final = core.issues.get(issue.id)
        assert final.status == Status.CLOSED
        assert final.milestone == "v1.0"

    def test_empty_repository_operations(self, core):
        """Test operations on empty repository."""
        assert core.issues.list() == []
        assert core.milestones.list() == []

        progress = core.milestones.get_progress("nonexistent")
        assert progress.get("total", 0) == 0

    def test_issue_with_all_optional_fields(self, core):
        """Test issue creation with all optional fields populated."""
        issue = core.issues.create(
            title="Full Featured Issue",
            priority=Priority.CRITICAL,
            assignee="dev@example.com",
            labels=["urgent", "blocker", "fix"],
            estimated_hours=16,
            issue_type=IssueType.BUG,
            milestone="v1.0",
        )

        # Update status after creation
        issue = core.issues.update(issue.id, status=Status.IN_PROGRESS)

        retrieved = core.issues.get(issue.id)
        assert retrieved.title == "Full Featured Issue"
        assert retrieved.priority == Priority.CRITICAL
        assert retrieved.status == Status.IN_PROGRESS
        assert retrieved.assignee == "dev@example.com"
        assert "urgent" in retrieved.labels
        assert retrieved.estimated_hours == 16
        assert retrieved.issue_type == IssueType.BUG
        assert retrieved.milestone == "v1.0"

    def test_multiple_issues_per_milestone(self, core):
        """Test milestone with multiple issues in various states."""
        core.milestones.create("v2.0", "Second Release")

        # Create issues in different states
        issue1 = core.issues.create("Feature 1")
        issue2 = core.issues.create("Feature 2")
        issue3 = core.issues.create("Bug Fix")

        # Assign all to milestone
        for issue_id in [issue1.id, issue2.id, issue3.id]:
            core.issues.assign_to_milestone(issue_id, "v2.0")

        # Set different statuses
        core.issues.update(issue1.id, status=Status.CLOSED)
        core.issues.update(issue2.id, status=Status.IN_PROGRESS)
        # issue3 stays TODO

        # Check progress
        progress = core.milestones.get_progress("v2.0")
        assert progress["total"] == 3
        assert progress["completed"] == 1
        assert abs(progress["progress"] - 33.333) < 0.01

    def test_filter_by_multiple_criteria(self, core):
        """Test complex filtering with multiple criteria."""
        # Setup: Create various issues
        issue1 = core.issues.create("Bug 1", Priority.HIGH, issue_type=IssueType.BUG)
        issue2 = core.issues.create("Feature 1", Priority.LOW, issue_type=IssueType.FEATURE)
        issue3 = core.issues.create("Bug 2", Priority.HIGH, issue_type=IssueType.BUG)

        # Update some to different statuses
        core.issues.update(issue1.id, status=Status.CLOSED)

        # Complex filter: HIGH priority BUG that's not closed
        bugs_high = core.issues.list(priority=Priority.HIGH, issue_type=IssueType.BUG)
        assert len(bugs_high) == 2

        # All closed items
        closed = core.issues.list(status=Status.CLOSED)
        assert len(closed) == 1
        assert closed[0].id == issue1.id
