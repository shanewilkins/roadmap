"""Comprehensive tests for milestone movement operations.

These tests verify that moving issues between milestones doesn't create
duplicate files and that all file locations are correct throughout the
process. This is critical for maintaining data integrity.
"""

from pathlib import Path

import pytest

from roadmap.core.domain import Priority, Status
from roadmap.infrastructure.core import RoadmapCore


class TestIssueMilestoneMovement:
    """Test moving issues between milestones with file integrity checks."""

    @pytest.fixture
    def core_with_milestones(self, temp_dir):
        """Create initialized roadmap with multiple milestones."""
        core = RoadmapCore()
        core.initialize()
        core.milestones.create("Milestone 1", "First milestone")
        core.milestones.create("Milestone 2", "Second milestone")
        core.milestones.create("Milestone 3", "Third milestone")
        return core

    def get_issue_file_location(self, issue_path: str) -> str | None:
        """Extract directory name from issue file path."""
        parts = Path(issue_path).parts
        for i, part in enumerate(parts):
            if part == "issues" and i + 1 < len(parts):
                return parts[i + 1]
        return None

    def test_move_issue_between_milestones_no_stale_files(self, core_with_milestones):
        """Verify moving issue between milestones removes old file."""
        core = core_with_milestones

        # Create issue in Milestone 1
        issue = core.issues.create("Test Issue", milestone="Milestone 1")
        path1 = Path(issue.file_path)
        assert path1.exists()
        assert "Milestone 1" in path1.parts

        # Move to Milestone 2
        core.issues.move_to_milestone(issue.id, "Milestone 2")
        assert not path1.exists(), "Old file still exists after move"

        # Verify new location
        updated = core.issues.get(issue.id)
        path2 = Path(updated.file_path)
        assert path2.exists()
        assert "Milestone 2" in path2.parts
        assert updated.milestone == "Milestone 2"

    def test_move_issue_through_multiple_milestones_no_duplicates(
        self, core_with_milestones
    ):
        """Verify moving issue through multiple milestones leaves no duplicates."""
        core = core_with_milestones

        issue = core.issues.create("Test Issue", milestone="Milestone 1")
        milestones_to_visit = [
            "Milestone 1",
            "Milestone 2",
            "Milestone 3",
            "Milestone 1",
        ]

        for target_milestone in milestones_to_visit[1:]:  # Skip initial
            current_issue = core.issues.get(issue.id)
            old_path = Path(current_issue.file_path)

            # Move to next milestone
            core.issues.move_to_milestone(issue.id, target_milestone)

            # Old file must be gone
            assert not old_path.exists(), f"Stale file left behind: {old_path}"

            # New file must exist in correct location
            current_issue = core.issues.get(issue.id)
            new_path = Path(current_issue.file_path)
            assert new_path.exists()
            assert target_milestone in new_path.parts

    def test_move_issue_to_backlog_from_milestone(self, core_with_milestones):
        """Verify moving issue from milestone to backlog works correctly."""
        core = core_with_milestones

        issue = core.issues.create("Test Issue", milestone="Milestone 1")
        old_path = Path(issue.file_path)
        assert "Milestone 1" in old_path.parts

        # Move to backlog
        core.issues.move_to_milestone(issue.id, None)

        assert not old_path.exists(), "Old milestone file still exists"

        # Verify it's in backlog
        updated = core.issues.get(issue.id)
        new_path = Path(updated.file_path)
        assert new_path.exists()
        assert "backlog" in new_path.parts
        assert updated.milestone is None

    def test_move_backlog_issue_to_milestone(self, core_with_milestones):
        """Verify moving issue from backlog to milestone works correctly."""
        core = core_with_milestones

        # Create unassigned issue (in backlog)
        issue = core.issues.create("Test Issue")
        old_path = Path(issue.file_path)
        assert "backlog" in old_path.parts
        assert issue.milestone is None

        # Move to milestone
        core.issues.move_to_milestone(issue.id, "Milestone 1")

        assert not old_path.exists(), "Old backlog file still exists"

        # Verify it's in milestone directory
        updated = core.issues.get(issue.id)
        new_path = Path(updated.file_path)
        assert new_path.exists()
        assert "Milestone 1" in new_path.parts
        assert updated.milestone == "Milestone 1"

    def test_move_issue_with_other_updates_no_duplicates(self, core_with_milestones):
        """Verify moving issue while updating other fields doesn't create duplicates."""
        core = core_with_milestones

        issue = core.issues.create(
            "Test Issue", milestone="Milestone 1", priority=Priority.LOW
        )
        old_path = Path(issue.file_path)

        # Move milestone AND update other fields
        core.issues.update(
            issue.id,
            milestone="Milestone 2",
            title="Updated Title",
            status=Status.IN_PROGRESS,
            priority=Priority.HIGH,
        )

        # Old file should be gone
        assert not old_path.exists()

        # New file should exist with all updates
        updated = core.issues.get(issue.id)
        new_path = Path(updated.file_path)
        assert new_path.exists()
        assert "Milestone 2" in new_path.parts
        assert updated.title == "Updated Title"
        assert updated.status == Status.IN_PROGRESS
        assert updated.priority == Priority.HIGH

    def test_file_path_property_updated_after_move(self, core_with_milestones):
        """Verify issue.file_path is correctly updated after milestone move."""
        core = core_with_milestones

        issue = core.issues.create("Test Issue", milestone="Milestone 1")
        path1 = issue.file_path

        # Move directly via update
        core.issues.update(issue.id, milestone="Milestone 2")

        # Get fresh copy
        updated = core.issues.get(issue.id)
        path2 = updated.file_path

        assert path1 != path2, "file_path property not updated after move"
        assert "Milestone 1" in path1
        assert "Milestone 2" in path2
        assert Path(path2).exists()

    def test_batch_move_multiple_issues_no_duplicates(self, core_with_milestones):
        """Verify moving multiple issues simultaneously doesn't create duplicates."""
        core = core_with_milestones

        # Create multiple issues
        issues = [
            core.issues.create(f"Issue {i}", milestone="Milestone 1") for i in range(5)
        ]
        old_paths = [Path(issue.file_path) for issue in issues]

        # Move all to Milestone 2
        for issue in issues:
            core.issues.move_to_milestone(issue.id, "Milestone 2")

        # Verify all old files are gone
        for old_path in old_paths:
            assert not old_path.exists()

        # Verify all new files exist in correct location
        for issue in issues:
            updated = core.issues.get(issue.id)
            new_path = Path(updated.file_path)
            assert new_path.exists()
            assert "Milestone 2" in new_path.parts

    def test_moving_issue_preserves_data_integrity(self, core_with_milestones):
        """Verify all issue data is preserved when moving between milestones."""
        core = core_with_milestones

        # Create issue with all fields
        original_issue = core.issues.create(
            "Test Issue",
            milestone="Milestone 1",
            priority=Priority.HIGH,
            status=Status.TODO,
        )
        original_id = original_issue.id

        # Move to different milestone
        core.issues.move_to_milestone(original_id, "Milestone 2")

        # Retrieve and verify all data preserved
        moved_issue = core.issues.get(original_id)
        assert moved_issue.id == original_id
        assert moved_issue.title == "Test Issue"
        assert moved_issue.milestone == "Milestone 2"
        assert moved_issue.priority == Priority.HIGH
        assert moved_issue.status == Status.TODO
