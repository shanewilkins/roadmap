"""Tests to ensure update operations don't create duplicate files.

These tests verify that updating issues, milestones, and projects does not
result in duplicate files in the filesystem. This is critical for preventing
data corruption and maintaining a clean file structure.
"""

from pathlib import Path

import pytest

from roadmap.common.constants import MilestoneStatus, ProjectStatus, Status
from roadmap.core.domain import Priority
from roadmap.infrastructure.core import RoadmapCore


class TestIssueDuplicatePrevention:
    """Verify issue update operations don't create duplicates."""

    @pytest.fixture
    def core(self, temp_dir):
        """Create initialized roadmap core."""
        core = RoadmapCore()
        core.initialize()
        return core

    def count_issue_files(self, core) -> int:
        """Count all issue markdown files recursively."""
        return len(list(core.issues_dir.glob("**/*.md")))

    def test_update_issue_does_not_create_duplicates(self, core):
        """Ensure updating an issue doesn't create duplicate files."""
        # Create initial issue
        issue = core.issues.create("Test Issue", priority=Priority.MEDIUM)
        initial_count = self.count_issue_files(core)
        assert initial_count == 1, "Initial issue file not created"

        # Update multiple fields
        core.issues.update(
            issue.id,
            title="Updated Title",
            status=Status.IN_PROGRESS,
            priority=Priority.HIGH,
        )

        final_count = self.count_issue_files(core)
        assert (
            initial_count == final_count
        ), f"Update created duplicate files: {initial_count} → {final_count}"

    def test_update_description_no_duplicates(self, core):
        """Ensure updating description doesn't create duplicates."""
        issue = core.issues.create("Test", priority=Priority.MEDIUM)
        initial_count = self.count_issue_files(core)

        core.issues.update(issue.id, headline="New detailed description here")

        final_count = self.count_issue_files(core)
        assert (
            initial_count == final_count
        ), "Description update created duplicate files"

    def test_update_status_multiple_times_no_duplicates(self, core):
        """Ensure multiple status updates don't accumulate duplicates."""
        issue = core.issues.create("Test Issue")
        initial_count = self.count_issue_files(core)

        # Update status multiple times
        statuses = [Status.IN_PROGRESS, Status.CLOSED, Status.TODO]
        for status in statuses:
            core.issues.update(issue.id, status=status)

        final_count = self.count_issue_files(core)
        assert (
            initial_count == final_count
        ), f"Multiple updates created duplicates: {initial_count} → {final_count}"

    def test_update_priority_no_duplicates(self, core):
        """Ensure updating priority doesn't create duplicates."""
        issue = core.issues.create("Test", priority=Priority.LOW)
        initial_count = self.count_issue_files(core)

        core.issues.update(issue.id, priority=Priority.CRITICAL)

        final_count = self.count_issue_files(core)
        assert initial_count == final_count, "Priority update created duplicate files"

    def test_move_issue_to_milestone_no_duplicates(self, core):
        """Ensure moving issue to milestone doesn't leave old file."""
        # Create milestones and issue
        core.milestones.create("Milestone 1", "Description")
        issue = core.issues.create("Test Issue")
        initial_path = Path(issue.file_path)
        initial_count = self.count_issue_files(core)

        # Move to milestone
        core.issues.move_to_milestone(issue.id, "Milestone 1")

        # Old file should be gone
        assert not initial_path.exists(), f"Old file still exists at {initial_path}"

        # No extra files should exist
        final_count = self.count_issue_files(core)
        assert (
            initial_count == final_count
        ), "Milestone move created or left duplicate files"

        # Verify file is in correct location
        updated_issue = core.issues.get(issue.id)
        assert updated_issue is not None
        new_path = Path(updated_issue.file_path)
        assert new_path.exists(), "New file doesn't exist at expected location"
        assert (
            "Milestone 1" in new_path.parts
        ), "File not in correct milestone directory"

    def test_move_issue_back_to_backlog_no_duplicates(self, core):
        """Ensure moving issue to backlog doesn't leave stale files."""
        # Create milestone and assign issue to it
        core.milestones.create("Milestone 1", "Description")
        issue = core.issues.create("Test Issue", milestone="Milestone 1")
        old_path = Path(issue.file_path)
        assert old_path.exists()

        # Move back to backlog
        core.issues.move_to_milestone(issue.id, None)

        # Old file should be gone
        assert not old_path.exists(), "Old milestone file still exists"

        # Should be in backlog now
        updated_issue = core.issues.get(issue.id)
        new_path = Path(updated_issue.file_path)
        assert new_path.exists()
        assert "backlog" in new_path.parts


class TestMilestoneDuplicatePrevention:
    """Verify milestone update operations don't create duplicates."""

    @pytest.fixture
    def core(self, temp_dir):
        """Create initialized roadmap core."""
        core = RoadmapCore()
        core.initialize()
        return core

    def count_milestone_files(self, core) -> int:
        """Count all milestone markdown files."""
        return len(list(core.milestones_dir.glob("*.md")))

    def test_update_milestone_no_duplicates(self, core):
        """Ensure updating milestone doesn't create duplicates."""
        milestone = core.milestones.create("Test Milestone", "Original description")
        initial_count = self.count_milestone_files(core)

        # Update milestone
        core.milestones.update(
            milestone.name,
            headline="Updated description",
        )

        final_count = self.count_milestone_files(core)
        assert (
            initial_count == final_count
        ), f"Update created duplicate milestone files: {initial_count} → {final_count}"

    def test_update_milestone_status_no_duplicates(self, core):
        """Ensure updating milestone status doesn't create duplicates."""
        milestone = core.milestones.create("Test Milestone", "Description")
        initial_count = self.count_milestone_files(core)

        core.milestones.update(milestone.name, status=MilestoneStatus.CLOSED)

        final_count = self.count_milestone_files(core)
        assert (
            initial_count == final_count
        ), "Status update created duplicate milestone files"


class TestProjectDuplicatePrevention:
    """Verify project update operations don't create duplicates."""

    @pytest.fixture
    def core(self, temp_dir):
        """Create initialized roadmap core."""
        core = RoadmapCore()
        core.initialize()
        return core

    def count_project_files(self, core) -> int:
        """Count all project markdown files."""
        return len(list(core.projects_dir.glob("*.md")))

    def test_update_project_no_duplicates(self, core):
        """Ensure updating project doesn't create duplicates."""
        project = core.projects.create("Test Project", "Original description")
        initial_count = self.count_project_files(core)

        # Update project
        core.projects.update(project.id, headline="Updated description")

        final_count = self.count_project_files(core)
        assert (
            initial_count == final_count
        ), f"Update created duplicate project files: {initial_count} → {final_count}"

    def test_update_project_status_no_duplicates(self, core):
        """Ensure updating project status doesn't create duplicates."""
        project = core.projects.create("Test Project", "Description")
        initial_count = self.count_project_files(core)

        core.projects.update(project.id, status=ProjectStatus.COMPLETED)

        final_count = self.count_project_files(core)
        assert (
            initial_count == final_count
        ), "Status update created duplicate project files"
