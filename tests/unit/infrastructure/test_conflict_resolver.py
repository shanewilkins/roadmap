"""
Tests for conflict detection and resolution.
"""

import tempfile
from pathlib import Path

import pytest

from roadmap.adapters.persistence.conflict_resolver import ConflictResolver
from roadmap.adapters.persistence.database_manager import DatabaseManager
from roadmap.adapters.persistence.sync_state_tracker import SyncStateTracker


class TestConflictResolver:
    """Test ConflictResolver for detecting and resolving conflicts."""

    @pytest.fixture
    def temp_dir(self, temp_dir_context):
        """Create a temporary directory for test files."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield Path(tmpdir)

    @pytest.fixture
    def conflict_resolver(self, temp_dir):
        """Create a ConflictResolver with temp directory."""
        return ConflictResolver(temp_dir)

    def test_initialization(self, temp_dir):
        """ConflictResolver should initialize with data_dir."""
        resolver = ConflictResolver(temp_dir)
        assert resolver.data_dir == temp_dir

    def test_no_conflicts_detected_in_empty_directory(self, conflict_resolver):
        """detect_conflicts should return empty list for directory with no conflicts."""
        conflicts = conflict_resolver.detect_conflicts()
        assert conflicts == []

    def test_no_conflicts_in_file_without_markers(self, conflict_resolver, temp_dir):
        """detect_conflicts should not detect files without conflict markers."""
        test_file = temp_dir / "test.md"
        test_file.write_text("# Title\n\nNo conflicts here.\n")

        conflicts = conflict_resolver.detect_conflicts()
        assert conflicts == []

    def test_detects_conflict_with_head_marker(self, conflict_resolver, temp_dir):
        """detect_conflicts should detect files with HEAD conflict markers."""
        test_file = temp_dir / "conflict.md"
        test_file.write_text(
            "<<<<<<< HEAD\nOur content\n=======\nTheir content\n>>>>>>> branch\n"
        )

        conflicts = conflict_resolver.detect_conflicts()
        assert len(conflicts) == 1
        assert str(test_file) in conflicts[0]

    def test_detects_multiple_conflict_files(self, conflict_resolver, temp_dir):
        """detect_conflicts should detect multiple files with conflicts."""
        file1 = temp_dir / "conflict1.md"
        file2 = temp_dir / "conflict2.md"
        file3 = temp_dir / "clean.md"

        file1.write_text("<<<<<<< HEAD\nConflict 1\n=======\n=======\n>>>>>>> branch\n")
        file2.write_text(
            "Some content\n<<<<<<< HEAD\nConflict 2\n=======\n=======\n>>>>>>> branch\n"
        )
        file3.write_text("No conflicts\n")

        conflicts = conflict_resolver.detect_conflicts()
        assert len(conflicts) == 2

    def test_detects_conflicts_in_nested_directories(self, conflict_resolver, temp_dir):
        """detect_conflicts should detect conflicts in nested directories."""
        subdir = temp_dir / "subdir"
        subdir.mkdir()
        test_file = subdir / "conflict.md"
        test_file.write_text(
            "<<<<<<< HEAD\nConflict\n=======\n=======\n>>>>>>> branch\n"
        )

        conflicts = conflict_resolver.detect_conflicts()
        assert len(conflicts) == 1

    def test_resolve_conflict_keeps_ours(self, conflict_resolver, temp_dir):
        """resolve_conflict with 'ours' should keep our version."""
        test_file = temp_dir / "conflict.md"
        test_file.write_text(
            "<<<<<<< HEAD\nOur content\n=======\nTheir content\n>>>>>>> branch\n"
        )

        result = conflict_resolver.resolve_conflict(test_file, "ours")
        assert result
        assert "Our content" in test_file.read_text()
        assert "Their content" not in test_file.read_text()
        assert "<<<<<<<" not in test_file.read_text()

    def test_resolve_conflict_keeps_theirs(self, conflict_resolver, temp_dir):
        """resolve_conflict with 'theirs' should keep their version."""
        test_file = temp_dir / "conflict.md"
        test_file.write_text(
            "<<<<<<< HEAD\nOur content\n=======\nTheir content\n>>>>>>> branch\n"
        )

        result = conflict_resolver.resolve_conflict(test_file, "theirs")
        assert result
        assert "Their content" in test_file.read_text()
        assert "Our content" not in test_file.read_text()
        assert "<<<<<<<" not in test_file.read_text()

    def test_resolve_conflict_removes_markers(self, conflict_resolver, temp_dir):
        """resolve_conflict should remove all conflict markers."""
        test_file = temp_dir / "conflict.md"
        test_file.write_text("<<<<<<< HEAD\nOur\n=======\nTheir\n>>>>>>> branch\n")

        conflict_resolver.resolve_conflict(test_file, "ours")
        content = test_file.read_text()

        assert "<<<<<<< HEAD" not in content
        assert "=======" not in content
        assert ">>>>>>>" not in content

    def test_resolve_conflict_handles_missing_file(self, conflict_resolver, temp_dir):
        """resolve_conflict should handle missing files gracefully."""
        missing_file = temp_dir / "missing.md"
        result = conflict_resolver.resolve_conflict(missing_file, "ours")
        assert not result

    def test_resolve_conflict_handles_permission_error(
        self, conflict_resolver, temp_dir
    ):
        """resolve_conflict should handle permission errors gracefully."""
        test_file = temp_dir / "conflict.md"
        test_file.write_text("<<<<<<< HEAD\nOur\n=======\nTheir\n>>>>>>> branch\n")
        test_file.chmod(0o444)  # Read-only

        result = conflict_resolver.resolve_conflict(test_file, "ours")
        assert not result

        # Restore permissions for cleanup
        test_file.chmod(0o644)

    def test_auto_resolve_conflicts_ours(self, conflict_resolver, temp_dir, temp_db):
        """auto_resolve_conflicts should resolve all conflicts with 'ours'."""
        file1 = temp_dir / "conflict1.md"
        file2 = temp_dir / "conflict2.md"
        file1.write_text("<<<<<<< HEAD\nOur1\n=======\nTheir1\n>>>>>>> branch\n")
        file2.write_text("<<<<<<< HEAD\nOur2\n=======\nTheir2\n>>>>>>> branch\n")

        db_manager = DatabaseManager(db_path=temp_db)
        sync_tracker = SyncStateTracker(db_manager._get_connection)

        result = conflict_resolver.auto_resolve_conflicts(sync_tracker, "ours")
        assert result
        assert "<<<<<<< HEAD" not in file1.read_text()
        assert "<<<<<<< HEAD" not in file2.read_text()

    def test_auto_resolve_conflicts_updates_sync_state(
        self, conflict_resolver, temp_dir, temp_db
    ):
        """auto_resolve_conflicts should update sync state when successful."""
        test_file = temp_dir / "conflict.md"
        test_file.write_text("<<<<<<< HEAD\nOur\n=======\nTheir\n>>>>>>> branch\n")

        db_manager = DatabaseManager(db_path=temp_db)
        sync_tracker = SyncStateTracker(db_manager._get_connection)

        conflict_resolver.auto_resolve_conflicts(sync_tracker, "ours")
        assert not sync_tracker.has_git_conflicts()

    def test_auto_resolve_conflicts_no_conflicts_found(
        self, conflict_resolver, temp_dir, temp_db
    ):
        """auto_resolve_conflicts should return True when no conflicts found."""
        db_manager = DatabaseManager(db_path=temp_db)
        sync_tracker = SyncStateTracker(db_manager._get_connection)

        result = conflict_resolver.auto_resolve_conflicts(sync_tracker)
        assert result

    def test_get_conflict_summary_no_conflicts(self, conflict_resolver):
        """get_conflict_summary should return empty summary when no conflicts."""
        summary = conflict_resolver.get_conflict_summary()
        assert not summary["has_conflicts"]
        assert summary["conflict_count"] == 0
        assert summary["files"] == []

    def test_get_conflict_summary_with_conflicts(self, conflict_resolver, temp_dir):
        """get_conflict_summary should return conflict information."""
        file1 = temp_dir / "conflict1.md"
        file2 = temp_dir / "conflict2.md"
        file1.write_text("<<<<<<< HEAD\nOur1\n=======\nTheir1\n>>>>>>> branch\n")
        file2.write_text("<<<<<<< HEAD\nOur2\n=======\nTheir2\n>>>>>>> branch\n")

        summary = conflict_resolver.get_conflict_summary()
        assert summary["has_conflicts"]
        assert summary["conflict_count"] == 2
        assert len(summary["files"]) == 2

    def test_conflict_markers_case_sensitivity(self, conflict_resolver, temp_dir):
        """detect_conflicts should detect conflict markers regardless of case."""
        test_file = temp_dir / "conflict.md"
        # Standard markers should be detected
        test_file.write_text(
            "Some content\n<<<<<<< HEAD\nOur\n=======\nTheir\n>>>>>>> branch\n"
        )
        conflicts = conflict_resolver.detect_conflicts()
        assert len(conflicts) == 1

    def test_has_conflict_markers_with_incomplete_markers(
        self, conflict_resolver, temp_dir
    ):
        """_has_conflict_markers should detect incomplete marker patterns."""
        test_file = temp_dir / "conflict.md"
        test_file.write_text("Content with <<<<<<<\n")
        # Even incomplete markers should be detected
        conflicts = conflict_resolver.detect_conflicts()
        assert len(conflicts) == 1

    @pytest.fixture
    def temp_db(self):
        """Create a temporary database."""
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            db_path = Path(f.name)
        yield db_path
        try:
            db_path.unlink()
            wal_path = Path(str(db_path) + "-wal")
            shm_path = Path(str(db_path) + "-shm")
            if wal_path.exists():
                wal_path.unlink()
            if shm_path.exists():
                shm_path.unlink()
        except Exception:
            pass
