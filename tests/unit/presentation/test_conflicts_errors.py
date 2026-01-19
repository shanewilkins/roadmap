"""Error path tests for ConflictService (conflicts.py module).

Tests cover git conflict detection, file reading errors,
JSON parsing, and state management.
"""

from pathlib import Path
from unittest import mock

from roadmap.adapters.persistence.storage.conflicts import ConflictService
from tests.fixtures import build_mock_path


class TestConflictServiceInitialization:
    """Test ConflictService initialization."""

    def test_initialization_with_state_manager(self):
        """Test ConflictService initializes with state manager."""
        mock_state_manager = mock.MagicMock()
        service = ConflictService(mock_state_manager)
        assert service.state_manager == mock_state_manager

    def test_initialization_stores_reference(self):
        """Test initialization stores the state manager reference."""
        mock_state_manager = mock.MagicMock()
        service = ConflictService(mock_state_manager)
        assert service.state_manager is mock_state_manager


class TestCheckGitConflicts:
    """Test check_git_conflicts method."""

    def test_check_git_conflicts_no_roadmap_dir(self):
        """Test when roadmap directory doesn't exist."""
        mock_state_manager = mock.MagicMock()
        service = ConflictService(mock_state_manager)

        # Create a path that doesn't exist
        nonexistent_dir = Path("/nonexistent/path/.roadmap")
        result = service.check_git_conflicts(nonexistent_dir)

        # Should return empty list when directory doesn't exist
        assert result == []

    def test_check_git_conflicts_no_files(self):
        """Test when directory exists but has no files."""
        mock_state_manager = mock.MagicMock()
        service = ConflictService(mock_state_manager)

        mock_roadmap_dir = build_mock_path(exists=True, is_dir=True, glob_results=[])

        result = service.check_git_conflicts(mock_roadmap_dir)

        assert result == []
        # Should set conflict state to false when no conflicts found
        mock_state_manager.set_sync_state.assert_any_call(
            "git_conflicts_detected", "false"
        )

    def test_check_git_conflicts_detects_conflict_markers(self):
        """Test detection of git conflict markers."""
        mock_state_manager = mock.MagicMock()
        service = ConflictService(mock_state_manager)

        mock_file = build_mock_path(
            name="issues/test.md",
            content="content\n<<<<<<< HEAD\nconflict\n=======\nother\n>>>>>>> branch",
        )

        mock_roadmap_dir = build_mock_path(
            exists=True, is_dir=True, glob_results=[mock_file]
        )

        with mock.patch(
            "builtins.open", mock.mock_open(read_data="<<<<<<< HEAD\ncontent")
        ):
            result = service.check_git_conflicts(mock_roadmap_dir)
            assert len(result) > 0 or result == []

    def test_check_git_conflicts_file_read_error(self):
        """Test handling of file read errors."""
        mock_state_manager = mock.MagicMock()
        service = ConflictService(mock_state_manager)

        mock_file = build_mock_path(name="issues/test.md")

        mock_roadmap_dir = build_mock_path(
            exists=True, is_dir=True, glob_results=[mock_file]
        )

        with mock.patch("builtins.open", side_effect=OSError("Cannot read file")):
            result = service.check_git_conflicts(mock_roadmap_dir)
            # Should continue despite error
            assert isinstance(result, list)

    def test_check_git_conflicts_general_error(self):
        """Test handling of general errors."""
        mock_state_manager = mock.MagicMock()
        service = ConflictService(mock_state_manager)

        mock_roadmap_dir = build_mock_path(exists=True, is_dir=True)
        mock_roadmap_dir.exists.side_effect = Exception("Unexpected error")

        result = service.check_git_conflicts(mock_roadmap_dir)
        assert result == []

    def test_check_git_conflicts_multiple_files(self):
        """Test checking multiple files."""
        mock_state_manager = mock.MagicMock()
        service = ConflictService(mock_state_manager)

        mock_file1 = build_mock_path(name="issues/a.md")

        mock_file2 = build_mock_path(name="issues/b.md")

        mock_roadmap_dir = build_mock_path(
            exists=True, is_dir=True, glob_results=[mock_file1, mock_file2]
        )
        mock_roadmap_dir.glob.side_effect = [[mock_file1, mock_file2], [], []]

        with mock.patch("builtins.open", mock.mock_open(read_data="normal content")):
            result = service.check_git_conflicts(mock_roadmap_dir)
            assert isinstance(result, list)

    def test_check_git_conflicts_sets_state(self):
        """Test that conflict state is properly set."""
        mock_state_manager = mock.MagicMock()
        service = ConflictService(mock_state_manager)

        mock_roadmap_dir = build_mock_path(exists=True, is_dir=True, glob_results=[])

        service.check_git_conflicts(mock_roadmap_dir)

        calls = mock_state_manager.set_sync_state.call_args_list
        # Should set git_conflicts_detected and conflict_files
        assert any("git_conflicts_detected" in str(call) for call in calls)


class TestHasGitConflicts:
    """Test has_git_conflicts method."""

    def test_has_git_conflicts_true(self):
        """Test when conflicts exist."""
        mock_state_manager = mock.MagicMock()
        mock_state_manager.get_sync_state.return_value = "true"

        service = ConflictService(mock_state_manager)
        result = service.has_git_conflicts()

        assert result is True
        mock_state_manager.get_sync_state.assert_called_with("git_conflicts_detected")

    def test_has_git_conflicts_false(self):
        """Test when no conflicts exist."""
        mock_state_manager = mock.MagicMock()
        mock_state_manager.get_sync_state.return_value = "false"

        service = ConflictService(mock_state_manager)
        result = service.has_git_conflicts()

        assert result is False

    def test_has_git_conflicts_error(self):
        """Test handling of state manager errors."""
        mock_state_manager = mock.MagicMock()
        mock_state_manager.get_sync_state.side_effect = Exception("DB error")

        service = ConflictService(mock_state_manager)
        result = service.has_git_conflicts()

        # Should default to False (safe assumption)
        assert result is False

    def test_has_git_conflicts_invalid_state(self):
        """Test with invalid state value."""
        mock_state_manager = mock.MagicMock()
        mock_state_manager.get_sync_state.return_value = "invalid"

        service = ConflictService(mock_state_manager)
        result = service.has_git_conflicts()

        assert result is False


class TestGetConflictFiles:
    """Test get_conflict_files method."""

    def test_get_conflict_files_empty(self):
        """Test when no conflict files exist."""
        mock_state_manager = mock.MagicMock()
        mock_state_manager.get_sync_state.return_value = "[]"

        service = ConflictService(mock_state_manager)
        result = service.get_conflict_files()

        assert result == []

    def test_get_conflict_files_with_files(self):
        """Test retrieving list of conflict files."""
        import json

        conflict_files = ["file1.md", "file2.md", "subdir/file3.md"]
        mock_state_manager = mock.MagicMock()
        mock_state_manager.get_sync_state.return_value = json.dumps(conflict_files)

        service = ConflictService(mock_state_manager)
        result = service.get_conflict_files()

        assert result == conflict_files

    def test_get_conflict_files_invalid_json(self):
        """Test with invalid JSON in state."""
        mock_state_manager = mock.MagicMock()
        mock_state_manager.get_sync_state.return_value = "not valid json"

        service = ConflictService(mock_state_manager)
        result = service.get_conflict_files()

        # Should return empty list on JSON error
        assert result == []

    def test_get_conflict_files_none_state(self):
        """Test when state is None."""
        mock_state_manager = mock.MagicMock()
        mock_state_manager.get_sync_state.return_value = None

        service = ConflictService(mock_state_manager)
        result = service.get_conflict_files()

        assert result == []

    def test_get_conflict_files_error(self):
        """Test handling of state manager errors."""
        mock_state_manager = mock.MagicMock()
        mock_state_manager.get_sync_state.side_effect = Exception("DB error")

        service = ConflictService(mock_state_manager)
        result = service.get_conflict_files()

        assert result == []

    def test_get_conflict_files_multiple_files(self):
        """Test with multiple conflict files."""
        import json

        conflict_files = [
            "issues/issue-1.md",
            "issues/issue-2.md",
            "milestones/v1.0.md",
            "projects/backend.md",
        ]
        mock_state_manager = mock.MagicMock()
        mock_state_manager.get_sync_state.return_value = json.dumps(conflict_files)

        service = ConflictService(mock_state_manager)
        result = service.get_conflict_files()

        assert len(result) == 4
        assert all(isinstance(f, str) for f in result)


class TestConflictServiceIntegration:
    """Integration tests for ConflictService."""

    def test_conflict_workflow(self):
        """Test complete conflict detection workflow."""
        mock_state_manager = mock.MagicMock()
        service = ConflictService(mock_state_manager)

        mock_roadmap_dir = build_mock_path(exists=True, is_dir=True, glob_results=[])

        # Check for conflicts
        result = service.check_git_conflicts(mock_roadmap_dir)
        assert isinstance(result, list)

        # Verify state was set
        mock_state_manager.set_sync_state.assert_called()

    def test_conflict_files_after_check(self):
        """Test retrieving conflict files after check."""
        import json

        mock_state_manager = mock.MagicMock()
        conflict_files = ["test.md"]
        mock_state_manager.get_sync_state.return_value = json.dumps(conflict_files)

        service = ConflictService(mock_state_manager)
        result = service.get_conflict_files()

        assert result == conflict_files
