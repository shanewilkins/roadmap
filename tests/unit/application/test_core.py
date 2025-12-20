"""Tests for core roadmap functionality."""

from datetime import datetime

import pytest

from roadmap.core.domain import MilestoneStatus, Priority, Status
from roadmap.infrastructure.core import RoadmapCore


class TestRoadmapCore:
    """Test cases for RoadmapCore."""

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
        assert core.is_initialized() is False

    def test_is_initialized_true(self, core):
        """Test is_initialized returns True when initialized."""
        core.initialize()
        assert core.is_initialized() is True

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

        # Check template content
        issue_content = issue_template.read_text()
        assert "{{ title }}" in issue_content
        assert "priority:" in issue_content

        # Check project template content
        project_content = project_template.read_text()
        assert "{{ project_name }}" in project_content
        assert "{{ project_owner }}" in project_content
        assert "start_date:" in project_content

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

        # Check file was created
        issue_file = core.issues_dir / issue.filename
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
        core.issues.update(issue3.id, status=Status.DONE)

        # Filter by milestone
        v1_issues = core.issues.list(milestone="v1.0")
        assert len(v1_issues) == 2

        # Filter by status
        done_issues = core.issues.list(status=Status.DONE)
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
        issue_file = core.issues_dir / issue.filename

        assert issue_file.exists()

        success = core.issues.delete(issue.id)
        assert success is True
        assert not issue_file.exists()

    def test_delete_issue_not_found(self, core):
        """Test deleting non-existent issue."""
        core.initialize()

        success = core.issues.delete("nonexistent")
        assert success is False

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
        assert success is True

        # Verify assignment
        updated_issue = core.issues.get(issue.id)
        assert updated_issue.milestone == "v1.0"

    def test_assign_issue_to_milestone_issue_not_found(self, core):
        """Test assigning non-existent issue to milestone."""
        core.initialize()

        core.milestones.create("v1.0", "First release")

        success = core.issues.assign_to_milestone("nonexistent", "v1.0")
        assert success is False

    def test_assign_issue_to_milestone_milestone_not_found(self, core):
        """Test assigning issue to non-existent milestone."""
        core.initialize()

        issue = core.issues.create("Test Issue")
        original_milestone = issue.milestone

        # Assigning to a non-existent milestone returns False
        success = core.issues.assign_to_milestone(issue.id, "nonexistent")
        assert success is False

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
        core.issues.update(issue1.id, status=Status.DONE)

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
        core.milestones.create("test-milestone", "Test milestone")

        # Get progress
        progress = core.milestones.get_progress("test-milestone")

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
        assert result is True

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
        assert result is False
