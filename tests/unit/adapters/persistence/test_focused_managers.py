"""Tests for focused state manager adapters."""

from unittest.mock import Mock

import pytest

from roadmap.adapters.persistence.focused_managers import (
    FocusedIssueStateManager,
    FocusedMilestoneStateManager,
    FocusedProjectStateManager,
    FocusedQueryStateManager,
    FocusedSyncStateManager,
)


@pytest.fixture
def mock_state_manager():
    """Create a mock StateManager."""
    return Mock()


class TestFocusedProjectStateManager:
    """Test FocusedProjectStateManager adapter."""

    def test_create_project(self, mock_state_manager):
        """Test creating a project."""
        manager = FocusedProjectStateManager(mock_state_manager)
        project_data = {"name": "Test Project", "description": "A test project"}
        mock_state_manager.create_project.return_value = "proj-1"

        result = manager.create_project(project_data)

        assert result == "proj-1"
        mock_state_manager.create_project.assert_called_once_with(project_data)

    def test_get_project(self, mock_state_manager):
        """Test getting a project."""
        manager = FocusedProjectStateManager(mock_state_manager)
        project_data = {"id": "proj-1", "name": "Test Project"}
        mock_state_manager.get_project.return_value = project_data

        result = manager.get_project("proj-1")

        assert result == project_data
        mock_state_manager.get_project.assert_called_once_with("proj-1")

    def test_get_project_not_found(self, mock_state_manager):
        """Test getting a non-existent project."""
        manager = FocusedProjectStateManager(mock_state_manager)
        mock_state_manager.get_project.return_value = None

        result = manager.get_project("nonexistent")

        assert result is None
        mock_state_manager.get_project.assert_called_once_with("nonexistent")

    def test_list_projects(self, mock_state_manager):
        """Test listing all projects."""
        manager = FocusedProjectStateManager(mock_state_manager)
        projects = [
            {"id": "proj-1", "name": "Project 1"},
            {"id": "proj-2", "name": "Project 2"},
        ]
        mock_state_manager.list_projects.return_value = projects

        result = manager.list_projects()

        assert result == projects
        mock_state_manager.list_projects.assert_called_once()

    def test_update_project(self, mock_state_manager):
        """Test updating a project."""
        manager = FocusedProjectStateManager(mock_state_manager)
        updates = {"name": "Updated Project"}
        mock_state_manager.update_project.return_value = True

        result = manager.update_project("proj-1", updates)

        assert result
        mock_state_manager.update_project.assert_called_once_with("proj-1", updates)

    def test_delete_project(self, mock_state_manager):
        """Test deleting a project."""
        manager = FocusedProjectStateManager(mock_state_manager)
        mock_state_manager.delete_project.return_value = True

        result = manager.delete_project("proj-1")

        assert result
        mock_state_manager.delete_project.assert_called_once_with("proj-1")

    def test_mark_project_archived_true(self, mock_state_manager):
        """Test marking a project as archived."""
        manager = FocusedProjectStateManager(mock_state_manager)
        mock_state_manager.mark_project_archived.return_value = True

        result = manager.mark_project_archived("proj-1", archived=True)

        assert result
        mock_state_manager.mark_project_archived.assert_called_once_with("proj-1", True)

    def test_mark_project_archived_false(self, mock_state_manager):
        """Test marking a project as unarchived."""
        manager = FocusedProjectStateManager(mock_state_manager)
        mock_state_manager.mark_project_archived.return_value = True

        result = manager.mark_project_archived("proj-1", archived=False)

        assert result
        mock_state_manager.mark_project_archived.assert_called_once_with(
            "proj-1", False
        )


class TestFocusedIssueStateManager:
    """Test FocusedIssueStateManager adapter."""

    def test_create_issue(self, mock_state_manager):
        """Test creating an issue."""
        manager = FocusedIssueStateManager(mock_state_manager)
        issue_data = {"title": "Test Issue", "priority": "high"}
        mock_state_manager.create_issue.return_value = "issue-1"

        result = manager.create_issue(issue_data)

        assert result == "issue-1"
        mock_state_manager.create_issue.assert_called_once_with(issue_data)

    def test_get_issue(self, mock_state_manager):
        """Test getting an issue."""
        manager = FocusedIssueStateManager(mock_state_manager)
        issue_data = {"id": "issue-1", "title": "Test Issue"}
        mock_state_manager.get_issue.return_value = issue_data

        result = manager.get_issue("issue-1")

        assert result == issue_data

    def test_mark_issue_archived(self, mock_state_manager):
        """Test marking an issue as archived."""
        manager = FocusedIssueStateManager(mock_state_manager)
        mock_state_manager.mark_issue_archived.return_value = True

        result = manager.mark_issue_archived("issue-1", archived=True)

        assert result

    def test_update_issue(self, mock_state_manager):
        """Test updating an issue."""
        manager = FocusedIssueStateManager(mock_state_manager)
        updates = {"status": "done"}
        mock_state_manager.update_issue.return_value = True

        result = manager.update_issue("issue-1", updates)

        assert result

    def test_delete_issue(self, mock_state_manager):
        """Test deleting an issue."""
        manager = FocusedIssueStateManager(mock_state_manager)
        mock_state_manager.delete_issue.return_value = True

        result = manager.delete_issue("issue-1")

        assert result


class TestFocusedMilestoneStateManager:
    """Test FocusedMilestoneStateManager adapter."""

    def test_create_milestone(self, mock_state_manager):
        """Test creating a milestone."""
        manager = FocusedMilestoneStateManager(mock_state_manager)
        milestone_data = {"name": "v1.0"}
        mock_state_manager.create_milestone.return_value = "milestone-1"

        result = manager.create_milestone(milestone_data)

        assert result == "milestone-1"

    def test_get_milestone(self, mock_state_manager):
        """Test getting a milestone."""
        manager = FocusedMilestoneStateManager(mock_state_manager)
        milestone_data = {"id": "milestone-1", "name": "v1.0"}
        mock_state_manager.get_milestone.return_value = milestone_data

        result = manager.get_milestone("milestone-1")

        assert result == milestone_data

    def test_update_milestone(self, mock_state_manager):
        """Test updating a milestone."""
        manager = FocusedMilestoneStateManager(mock_state_manager)
        updates = {"status": "completed"}
        mock_state_manager.update_milestone.return_value = True

        result = manager.update_milestone("milestone-1", updates)

        assert result

    def test_mark_milestone_archived(self, mock_state_manager):
        """Test marking a milestone as archived."""
        manager = FocusedMilestoneStateManager(mock_state_manager)
        mock_state_manager.mark_milestone_archived.return_value = True

        result = manager.mark_milestone_archived("milestone-1", archived=True)

        assert result


class TestFocusedQueryStateManager:
    """Test FocusedQueryStateManager adapter."""

    def test_get_all_issues(self, mock_state_manager):
        """Test getting all issues."""
        manager = FocusedQueryStateManager(mock_state_manager)
        issues = [{"id": "issue-1"}, {"id": "issue-2"}]
        mock_state_manager.get_all_issues.return_value = issues

        result = manager.get_all_issues()

        assert result == issues

    def test_get_all_milestones(self, mock_state_manager):
        """Test getting all milestones."""
        manager = FocusedQueryStateManager(mock_state_manager)
        milestones = [{"id": "m1"}, {"id": "m2"}]
        mock_state_manager.get_all_milestones.return_value = milestones

        result = manager.get_all_milestones()

        assert result == milestones

    def test_get_milestone_progress(self, mock_state_manager):
        """Test getting milestone progress."""
        manager = FocusedQueryStateManager(mock_state_manager)
        progress = {"total": 10, "completed": 5}
        mock_state_manager.get_milestone_progress.return_value = progress

        result = manager.get_milestone_progress("v1.0")

        assert result == progress

    def test_get_issues_by_status(self, mock_state_manager):
        """Test getting issue counts by status."""
        manager = FocusedQueryStateManager(mock_state_manager)
        status_counts = {"open": 5, "closed": 3}
        mock_state_manager.get_issues_by_status.return_value = status_counts

        result = manager.get_issues_by_status()

        assert result == status_counts


class TestFocusedSyncStateManager:
    """Test FocusedSyncStateManager adapter."""

    def test_set_sync_state(self, mock_state_manager):
        """Test setting sync state."""
        manager = FocusedSyncStateManager(mock_state_manager)
        mock_state_manager.set_sync_state.return_value = None

        manager.set_sync_state("last_sync", "2025-12-22T00:00:00Z")

        mock_state_manager.set_sync_state.assert_called_once_with(
            "last_sync", "2025-12-22T00:00:00Z"
        )

    def test_get_sync_state(self, mock_state_manager):
        """Test getting sync state."""
        manager = FocusedSyncStateManager(mock_state_manager)
        mock_state_manager.get_sync_state.return_value = "2025-12-22T00:00:00Z"

        result = manager.get_sync_state("last_sync")

        assert result == "2025-12-22T00:00:00Z"
        mock_state_manager.get_sync_state.assert_called_once_with("last_sync")

    def test_get_sync_state_not_found(self, mock_state_manager):
        """Test getting non-existent sync state."""
        manager = FocusedSyncStateManager(mock_state_manager)
        mock_state_manager.get_sync_state.return_value = None

        result = manager.get_sync_state("nonexistent")

        assert result is None
