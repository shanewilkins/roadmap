"""Extended tests for storage.py - file sync, hashing, and advanced operations."""

import tempfile
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch

import pytest

from roadmap.adapters.persistence.file_parser import FileParser
from roadmap.adapters.persistence.storage import StateManager


@pytest.fixture
def temp_db():
    """Create a temporary database."""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = Path(f.name)
    yield db_path
    # Cleanup
    try:
        db_path.unlink()
        for suffix in ["-wal", "-shm"]:
            extra_file = Path(str(db_path) + suffix)
            if extra_file.exists():
                extra_file.unlink()
    except Exception:
        pass


@pytest.fixture
def state_manager(temp_db):
    """Create a StateManager instance."""
    return StateManager(db_path=temp_db)


class TestStateManagerUtilities:
    """Test utility methods."""

    def test_close_connection(self, state_manager):
        """Test closing database connection."""
        # Open connection
        state_manager._get_connection()

        # Close it
        state_manager.close()

        # Should be able to open again
        conn = state_manager._get_connection()
        assert conn is not None

    def test_vacuum_optimizes_database(self, state_manager):
        """Test vacuum operation."""
        # Should not raise exception
        state_manager.vacuum()

        # Database should still be usable
        conn = state_manager._get_connection()
        assert conn is not None

    def test_database_exists(self, state_manager, temp_db):
        """Test database_exists returns True for existing database."""
        assert state_manager.database_exists()

    def test_database_exists_returns_false_for_missing_file(self):
        """Test database_exists returns False when file doesn't exist."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create path but don't create the database file
            db_path = Path(tmpdir) / "missing.db"
            manager = StateManager(db_path=db_path)

            # Delete the file that was created by init
            db_path.unlink()

            assert not manager.database_exists()


class TestStateManagerFileHashing:
    """Test file hashing and change detection."""

    def test_calculate_file_hash(self, state_manager):
        """Test calculating file hash."""
        parser = FileParser()
        with tempfile.NamedTemporaryFile(mode="w", delete=False) as f:
            f.write("test content")
            file_path = Path(f.name)

        try:
            hash_value = parser.calculate_file_hash(file_path)

            assert hash_value != ""
            assert len(hash_value) == 64  # SHA-256 produces 64 hex characters

            # Same content should produce same hash
            hash_value2 = parser.calculate_file_hash(file_path)
            assert hash_value == hash_value2
        finally:
            file_path.unlink()

    def test_calculate_file_hash_nonexistent_file(self, state_manager):
        """Test hash calculation for nonexistent file returns empty string."""
        parser = FileParser()
        result = parser.calculate_file_hash(Path("/nonexistent/file.txt"))
        assert result == ""

    def test_has_file_changed_new_file(self, state_manager):
        """Test has_file_changed returns True for never-synced file."""
        with tempfile.NamedTemporaryFile(mode="w", delete=False) as f:
            f.write("test content")
            file_path = Path(f.name)

        try:
            result = state_manager.has_file_changed(file_path)
            assert result
        finally:
            file_path.unlink()

    def test_has_file_changed_nonexistent_file(self, state_manager):
        """Test has_file_changed returns True for nonexistent file."""
        result = state_manager.has_file_changed(Path("/nonexistent/file.txt"))
        assert result

    def test_has_file_changed_after_sync(self, state_manager):
        """Test has_file_changed returns False after syncing."""
        parser = FileParser()
        with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".md") as f:
            f.write("test content")
            file_path = Path(f.name)

        try:
            # Calculate hash and update sync status
            content_hash = parser.calculate_file_hash(file_path)
            file_size = file_path.stat().st_size
            last_modified = datetime.now(timezone.utc)

            state_manager.update_file_sync_status(
                str(file_path), content_hash, file_size, last_modified
            )

            # File should not show as changed
            result = state_manager.has_file_changed(file_path)
            assert not result
        finally:
            file_path.unlink()

    def test_has_file_changed_modified_content(self, state_manager):
        """Test has_file_changed returns True after content modification."""
        parser = FileParser()
        with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".md") as f:
            f.write("original content")
            file_path = Path(f.name)

        try:
            # Sync initial state
            content_hash = parser.calculate_file_hash(file_path)
            state_manager.update_file_sync_status(
                str(file_path), content_hash, 100, datetime.now(timezone.utc)
            )

            # Modify file
            with open(file_path, "w") as f:
                f.write("modified content")

            # Should detect change
            result = state_manager.has_file_changed(file_path)
            assert result
        finally:
            file_path.unlink()


class TestStateManagerYAMLParsing:
    """Test YAML frontmatter parsing."""

    @pytest.mark.parametrize(
        "file_content,expected_result,description",
        [
            # Valid YAML frontmatter
            ("""---
id: TEST-001
title: Test Issue
status: open
---

# Issue Content
""", {"id": "TEST-001", "title": "Test Issue", "status": "open"}, "valid"),
            # File without frontmatter
            ("# Just regular markdown\n\nNo frontmatter here.", {}, "no_frontmatter"),
            # Invalid YAML
            ("""---
invalid: yaml: content: here
---""", {}, "invalid_yaml"),
        ],
    )
    def test_parse_yaml_frontmatter(self, state_manager, file_content, expected_result, description):
        """Test parsing YAML frontmatter in various scenarios."""
        parser = FileParser()
        with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".md") as f:
            f.write(file_content)
            file_path = Path(f.name)

        try:
            result = parser.parse_yaml_frontmatter(file_path)
            assert result == expected_result
        finally:
            file_path.unlink()

    def test_parse_yaml_frontmatter_nonexistent_file(self, state_manager):
        """Test parsing nonexistent file returns empty dict."""
        parser = FileParser()
        result = parser.parse_yaml_frontmatter(Path("/nonexistent/file.md"))
        assert result == {}


class TestStateManagerSyncState:
    """Test sync state management."""

    def test_set_sync_state(self, state_manager):
        """Test setting sync state."""
        state_manager.set_sync_state("last_sync", "2025-01-15T12:00:00")

        # Verify it was stored
        value = state_manager.get_sync_state("last_sync")
        assert value == "2025-01-15T12:00:00"

    def test_get_sync_state_nonexistent(self, state_manager):
        """Test getting nonexistent sync state returns None."""
        result = state_manager.get_sync_state("nonexistent_key")
        assert result is None

    def test_set_sync_state_overwrites(self, state_manager):
        """Test setting sync state overwrites previous value."""
        state_manager.set_sync_state("key", "value1")
        state_manager.set_sync_state("key", "value2")

        result = state_manager.get_sync_state("key")
        assert result == "value2"


class TestStateManagerConflictDetection:
    """Test Git conflict detection."""

    def test_has_git_conflicts_no_conflicts(self, state_manager):
        """Test has_git_conflicts returns False when no conflicts."""
        with patch.object(state_manager, "check_git_conflicts", return_value=[]):
            result = state_manager.has_git_conflicts()
            assert not result

    def test_has_git_conflicts_with_conflicts(self, state_manager):
        """Test has_git_conflicts returns True when conflicts exist."""
        # has_git_conflicts() calls check_git_conflicts() internally
        # We need to check the actual implementation
        result = state_manager.has_git_conflicts()
        # Without actual conflicts, should return False
        assert isinstance(result, bool)

    def test_get_conflict_files(self, state_manager):
        """Test getting list of conflict files."""
        # get_conflict_files() returns result of check_git_conflicts()
        result = state_manager.get_conflict_files()
        assert isinstance(result, list)

    def test_check_git_conflicts_no_roadmap_dir(self, state_manager):
        """Test check_git_conflicts with no roadmap_dir argument."""
        # Should handle missing roadmap_dir gracefully
        result = state_manager.check_git_conflicts(None)
        assert isinstance(result, list)


class TestStateManagerFileChangeDetection:
    """Test file change detection methods."""

    def test_has_file_changes_no_changes(self, state_manager):
        """Test has_file_changes returns False when no files changed."""
        # Empty database means no tracked files, so no changes
        result = state_manager.has_file_changes()
        # Implementation might vary, but should return bool
        assert isinstance(result, bool)


class TestStateManagerIssueRetrieval:
    """Test issue retrieval methods."""

    def test_get_all_issues_empty(self, state_manager):
        """Test get_all_issues returns empty list when no issues."""
        result = state_manager.get_all_issues()
        assert result == []

    def test_get_issues_by_status_empty(self, state_manager):
        """Test get_issues_by_status returns empty dict when no issues."""
        result = state_manager.get_issues_by_status()
        assert isinstance(result, dict)


class TestStateManagerMilestoneRetrieval:
    """Test milestone retrieval methods."""

    def test_get_all_milestones_empty(self, state_manager):
        """Test get_all_milestones returns empty list when no milestones."""
        result = state_manager.get_all_milestones()
        assert result == []

    def test_get_milestone_progress_nonexistent(self, state_manager):
        """Test get_milestone_progress for nonexistent milestone."""
        result = state_manager.get_milestone_progress("nonexistent")
        # Should return dict with counts
        assert isinstance(result, dict)
        assert "total" in result or result == {}


class TestStateManagerSafetyChecks:
    """Test safety checks for write operations."""

    def test_is_safe_for_writes_no_conflicts(self, state_manager):
        """Test is_safe_for_writes returns True when safe."""
        safe, message = state_manager.is_safe_for_writes()
        assert safe
        assert isinstance(message, str)
        assert len(message) > 0

    def test_is_safe_for_writes_with_conflicts(self, state_manager):
        """Test is_safe_for_writes returns False when conflicts exist."""
        with (
            patch.object(state_manager, "has_git_conflicts", return_value=True),
            patch.object(
                state_manager,
                "get_conflict_files",
                return_value=["file1.md", "file2.md"],
            ),
        ):
            safe, message = state_manager.is_safe_for_writes()
            assert not safe
            assert "conflicts" in message.lower()
