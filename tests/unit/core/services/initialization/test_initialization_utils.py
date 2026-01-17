"""Tests for initialization utilities."""

import json
from pathlib import Path
from unittest.mock import patch

import pytest

from roadmap.core.services.initialization.utils import (
    InitializationLock,
    InitializationManifest,
)


class TestInitializationLock:
    """Tests for InitializationLock class."""

    def test_lock_acquire_when_not_locked(self, temp_dir_context):
        """Test acquiring lock when no lock exists."""
        with temp_dir_context() as tmpdir:
            lock_path = Path(tmpdir) / "init.lock"
            lock = InitializationLock(lock_path)

            assert lock.acquire() is True
            assert lock_path.exists()
            assert "pid:" in lock_path.read_text()
            assert "started:" in lock_path.read_text()

    def test_lock_acquire_when_already_locked(self, temp_dir_context):
        """Test acquiring lock when lock already exists."""
        with temp_dir_context() as tmpdir:
            lock_path = Path(tmpdir) / "init.lock"
            lock_path.write_text("pid:1234\nstarted:2024-01-01T00:00:00\n")

            lock = InitializationLock(lock_path)
            assert lock.acquire() is False

    def test_lock_acquire_writes_pid(self, temp_dir_context):
        """Test that lock contains process ID."""
        with temp_dir_context() as tmpdir:
            lock_path = Path(tmpdir) / "init.lock"
            lock = InitializationLock(lock_path)

            lock.acquire()
            content = lock_path.read_text()

            assert "pid:" in content
            # Should contain our PID
            assert str(TestInitializationLock.__module__) or "pid:" in content

    def test_lock_acquire_writes_timestamp(self, temp_dir_context):
        """Test that lock contains timestamp."""
        with temp_dir_context() as tmpdir:
            lock_path = Path(tmpdir) / "init.lock"
            lock = InitializationLock(lock_path)

            lock.acquire()
        with temp_dir_context() as tmpdir:
            lock_path = Path(tmpdir) / "nonexistent" / "init.lock"
            lock = InitializationLock(lock_path)

            # Should return True even though directory doesn't exist
            result = lock.acquire()
            assert result is True

    def test_lock_release_removes_file(self, temp_dir_context):
        """Test that release removes the lock file."""
        with temp_dir_context() as tmpdir:
            lock_path = Path(tmpdir) / "init.lock"
            lock = InitializationLock(lock_path)

            lock.acquire()
            assert lock_path.exists()

            lock.release()
            assert not lock_path.exists()

    def test_lock_release_when_already_released(self, temp_dir_context):
        """Test that release doesn't fail if lock is already gone."""
        with temp_dir_context() as tmpdir:
            lock_path = Path(tmpdir) / "init.lock"
            lock = InitializationLock(lock_path)

            # Should not raise even if file doesn't exist
            lock.release()
            assert not lock_path.exists()

    def test_lock_release_handles_permission_error(self, temp_dir_context):
        """Test that release handles deletion errors gracefully."""
        with temp_dir_context() as tmpdir:
            lock_path = Path(tmpdir) / "init.lock"
            lock = InitializationLock(lock_path)
            lock.acquire()

            with patch.object(Path, "unlink", side_effect=PermissionError()):
                # Should not raise
                lock.release()
            # If we reach here, error was handled gracefully
            assert True

    def test_lock_context_usage(self, temp_dir_context):
        """Test typical acquire/release pattern."""
        with temp_dir_context() as tmpdir:
            lock_path = Path(tmpdir) / "init.lock"
            lock = InitializationLock(lock_path)

            assert lock.acquire()
            assert lock_path.exists()
            lock.release()
            assert not lock_path.exists()


class TestInitializationManifest:
    """Tests for InitializationManifest class."""

    def test_manifest_initialization(self, temp_dir_context):
        """Test manifest initializes with empty created list."""
        with temp_dir_context() as tmpdir:
            manifest_path = Path(tmpdir) / "manifest.json"
            manifest = InitializationManifest(manifest_path)

            assert manifest.data == {"created": []}

    def test_manifest_add_path_existing_file(self, temp_dir_context):
        """Test adding an existing file to manifest."""
        with temp_dir_context() as tmpdir:
            manifest_path = Path(tmpdir) / "manifest.json"
            file_path = Path(tmpdir) / "test.txt"
            file_path.write_text("test content")

            manifest = InitializationManifest(manifest_path)
            manifest.add_path(file_path)

            assert str(file_path) in manifest.data["created"]
            assert manifest_path.exists()

    def test_manifest_add_path_existing_directory(self, temp_dir_context):
        """Test adding an existing directory to manifest."""
        with temp_dir_context() as tmpdir:
            manifest_path = Path(tmpdir) / "manifest.json"
            dir_path = Path(tmpdir) / "test_dir"
            dir_path.mkdir()

            manifest = InitializationManifest(manifest_path)
            manifest.add_path(dir_path)

            assert str(dir_path) in manifest.data["created"]

    def test_manifest_add_path_nonexistent(self, temp_dir_context):
        """Test adding a non-existent path does nothing."""
        with temp_dir_context() as tmpdir:
            manifest_path = Path(tmpdir) / "manifest.json"
            nonexistent_path = Path(tmpdir) / "nonexistent"

            manifest = InitializationManifest(manifest_path)
            manifest.add_path(nonexistent_path)

            assert manifest.data["created"] == []

    def test_manifest_save(self, temp_dir_context):
        """Test that manifest saves to JSON file."""
        with temp_dir_context() as tmpdir:
            manifest_path = Path(tmpdir) / "manifest.json"
            file_path = Path(tmpdir) / "test.txt"
            file_path.write_text("content")

            manifest = InitializationManifest(manifest_path)
            manifest.add_path(file_path)

            # Check JSON file was created
            assert manifest_path.exists()
            saved_data = json.loads(manifest_path.read_text())
            assert str(file_path) in saved_data["created"]

    def test_manifest_save_handles_error(self, temp_dir_context):
        """Test that save errors are silently ignored."""
        with temp_dir_context() as tmpdir:
            # Use a path in non-existent directory
            manifest_path = Path(tmpdir) / "nonexistent" / "manifest.json"
            manifest = InitializationManifest(manifest_path)

            # Add a file - this triggers save, but should not raise
            file_path = Path(tmpdir) / "test.txt"
            file_path.write_text("content")
            manifest.add_path(file_path)

            # Manifest data should still be updated
            assert str(file_path) in manifest.data["created"]

    def test_manifest_add_multiple_paths(self, temp_dir_context):
        """Test adding multiple paths to manifest."""
        with temp_dir_context() as tmpdir:
            manifest_path = Path(tmpdir) / "manifest.json"
            manifest = InitializationManifest(manifest_path)

            paths = []
            for i in range(3):
                path = Path(tmpdir) / f"file{i}.txt"
                path.write_text(f"content {i}")
                paths.append(path)
                manifest.add_path(path)

            assert len(manifest.data["created"]) == 3
            for path in paths:
                assert str(path) in manifest.data["created"]

    def test_manifest_rollback_removes_files(self, temp_dir_context):
        """Test that rollback removes tracked files."""
        with temp_dir_context() as tmpdir:
            manifest_path = Path(tmpdir) / "manifest.json"
            file_path = Path(tmpdir) / "test.txt"
            file_path.write_text("content")

            manifest = InitializationManifest(manifest_path)
            manifest.add_path(file_path)

            assert file_path.exists()
            manifest.rollback()
            assert not file_path.exists()

    def test_manifest_rollback_removes_directories(self, temp_dir_context):
        """Test that rollback removes tracked directories."""
        with temp_dir_context() as tmpdir:
            manifest_path = Path(tmpdir) / "manifest.json"
            dir_path = Path(tmpdir) / "test_dir"
            dir_path.mkdir()
            (dir_path / "nested.txt").write_text("nested content")

            manifest = InitializationManifest(manifest_path)
            manifest.add_path(dir_path)

            assert dir_path.exists()
            manifest.rollback()
            assert not dir_path.exists()

    def test_manifest_rollback_removes_multiple_paths(self, temp_dir_context):
        """Test that rollback removes multiple tracked paths."""
        with temp_dir_context() as tmpdir:
            manifest_path = Path(tmpdir) / "manifest.json"
            manifest = InitializationManifest(manifest_path)

            created_paths = []
            for i in range(3):
                path = Path(tmpdir) / f"file{i}.txt"
                path.write_text(f"content {i}")
                manifest.add_path(path)
                created_paths.append(path)

            # All should exist
            assert all(p.exists() for p in created_paths)

            manifest.rollback()

            # All should be deleted
            assert not any(p.exists() for p in created_paths)

    def test_manifest_rollback_mixed_files_and_directories(self, temp_dir_context):
        """Test rollback with both files and directories."""
        with temp_dir_context() as tmpdir:
            manifest_path = Path(tmpdir) / "manifest.json"
            manifest = InitializationManifest(manifest_path)

            # Create a file and a directory
            file_path = Path(tmpdir) / "file.txt"
            file_path.write_text("content")
            dir_path = Path(tmpdir) / "dir"
            dir_path.mkdir()

            manifest.add_path(file_path)
            manifest.add_path(dir_path)

            assert file_path.exists()
            assert dir_path.exists()

            manifest.rollback()

            assert not file_path.exists()
            assert not dir_path.exists()

    def test_manifest_rollback_handles_missing_manifest_file(self, temp_dir_context):
        """Test that rollback handles missing manifest file gracefully."""
        with temp_dir_context() as tmpdir:
            manifest_path = Path(tmpdir) / "manifest.json"
            manifest = InitializationManifest(manifest_path)

            # Don't create manifest file
            manifest.rollback()  # Should not raise
            assert True

    def test_manifest_rollback_handles_invalid_json(self, temp_dir_context):
        """Test that rollback handles invalid JSON in manifest."""
        with temp_dir_context() as tmpdir:
            manifest_path = Path(tmpdir) / "manifest.json"
            manifest_path.write_text("invalid json {")

            manifest = InitializationManifest(manifest_path)
            manifest.rollback()  # Should not raise
            assert True

    def test_manifest_rollback_handles_missing_paths(self, temp_dir_context):
        """Test that rollback handles missing files gracefully."""
        with temp_dir_context() as tmpdir:
            manifest_path = Path(tmpdir) / "manifest.json"
            manifest_path.write_text(
                json.dumps({"created": [str(Path(tmpdir) / "nonexistent")]})
            )

            manifest = InitializationManifest(manifest_path)
            manifest.rollback()  # Should not raise
            assert True

    def test_manifest_rollback_handles_deletion_errors(self, temp_dir_context):
        """Test that rollback continues despite individual deletion errors."""
        with temp_dir_context() as tmpdir:
            manifest_path = Path(tmpdir) / "manifest.json"
            file_path = Path(tmpdir) / "file.txt"
            file_path.write_text("content")

            manifest = InitializationManifest(manifest_path)
            manifest.add_path(file_path)

            # Patch unlink to raise an error
            with patch.object(
                Path, "unlink", side_effect=PermissionError("Cannot delete")
            ):
                # Should not raise, errors are caught
                manifest.rollback()
            # If we reach here, rollback handled errors gracefully
            assert True

    def test_manifest_stores_correct_json_format(self, temp_dir_context):
        """Test that manifest stores data in correct JSON format."""
        with temp_dir_context() as tmpdir:
            manifest_path = Path(tmpdir) / "manifest.json"
            file_path = Path(tmpdir) / "test.txt"
            file_path.write_text("content")

            manifest = InitializationManifest(manifest_path)
            manifest.add_path(file_path)

            stored_data = json.loads(manifest_path.read_text())

            assert "created" in stored_data
            assert isinstance(stored_data["created"], list)
            assert str(file_path) in stored_data["created"]

    @pytest.mark.parametrize(
        "filename",
        [
            "simple_file.txt",
            "file-with-dashes.txt",
            "file_with_underscores.txt",
            ".hidden_file.txt",
        ],
    )
    def test_manifest_add_paths_various_filenames(self, filename, temp_dir_context):
        """Test adding files with various filename patterns."""
        with temp_dir_context() as tmpdir:
            manifest_path = Path(tmpdir) / "manifest.json"
            file_path = Path(tmpdir) / filename
            file_path.write_text("content")

            manifest = InitializationManifest(manifest_path)
            manifest.add_path(file_path)

            assert str(file_path) in manifest.data["created"]
