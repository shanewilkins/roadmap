"""Tests for file synchronization operations."""

import hashlib
import tempfile
from datetime import UTC, datetime
from pathlib import Path

import pytest

from roadmap.adapters.persistence.database_manager import DatabaseManager
from roadmap.adapters.persistence.file_parser import FileParser
from roadmap.adapters.persistence.file_synchronizer import FileSynchronizer


class TestFileSynchronizer:
    """Test FileSynchronizer for file-to-database synchronization."""

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

    @pytest.fixture
    def db_manager(self, temp_db):
        """Create a DatabaseManager with temp database."""
        manager = DatabaseManager(db_path=temp_db)
        yield manager
        # Cleanup: close database connection
        try:
            manager.close()
        except Exception:
            pass

    @pytest.fixture
    def file_synchronizer(self, db_manager):
        """Create a FileSynchronizer with database manager."""
        return FileSynchronizer(db_manager._get_connection, db_manager.transaction)

    @pytest.fixture
    def temp_data_dir(self, temp_dir_context):
        """Create a temporary data directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield Path(tmpdir)

    def test_initialization(self, file_synchronizer):
        """FileSynchronizer should initialize with connection callbacks."""
        assert file_synchronizer is not None

    def test_calculate_file_hash(self, file_synchronizer, temp_data_dir):
        """_calculate_file_hash should compute SHA256 hash of file content."""
        test_file = temp_data_dir / "test.md"
        content = "Test content for hashing"
        test_file.write_text(content)

        parser = FileParser()
        hash_value = parser.calculate_file_hash(test_file)
        expected = hashlib.sha256(content.encode()).hexdigest()
        assert hash_value == expected

    def test_calculate_file_hash_different_content_different_hash(
        self, file_synchronizer, temp_data_dir
    ):
        """_calculate_file_hash should produce different hashes for different content."""
        file1 = temp_data_dir / "file1.md"
        file2 = temp_data_dir / "file2.md"

        file1.write_text("Content 1")
        file2.write_text("Content 2")

        parser = FileParser()
        hash1 = parser.calculate_file_hash(file1)
        hash2 = parser.calculate_file_hash(file2)

        assert hash1 != hash2

    def test_calculate_file_hash_identical_content_same_hash(
        self, file_synchronizer, temp_data_dir
    ):
        """_calculate_file_hash should produce same hash for identical content."""
        file1 = temp_data_dir / "file1.md"
        file2 = temp_data_dir / "file2.md"
        content = "Identical content"

        file1.write_text(content)
        file2.write_text(content)

        parser = FileParser()
        hash1 = parser.calculate_file_hash(file1)
        hash2 = parser.calculate_file_hash(file2)

        assert hash1 == hash2

    def test_parse_yaml_frontmatter_valid_frontmatter(
        self, file_synchronizer, temp_data_dir
    ):
        """_parse_yaml_frontmatter should extract YAML frontmatter."""
        test_file = temp_data_dir / "test.md"
        content = """---
title: Test Issue
status: open
priority: high
---
# Content here
"""
        test_file.write_text(content)

        parser = FileParser()
        frontmatter = parser.parse_yaml_frontmatter(test_file)
        assert frontmatter["title"] == "Test Issue"
        assert frontmatter["status"] == "open"
        assert frontmatter["priority"] == "high"

    def test_parse_yaml_frontmatter_no_frontmatter(
        self, file_synchronizer, temp_data_dir
    ):
        """_parse_yaml_frontmatter should return empty dict for file without frontmatter."""
        test_file = temp_data_dir / "test.md"
        content = "# Content without frontmatter"
        test_file.write_text(content)

        parser = FileParser()
        frontmatter = parser.parse_yaml_frontmatter(test_file)
        assert frontmatter == {}

    def test_parse_yaml_frontmatter_invalid_yaml(
        self, file_synchronizer, temp_data_dir
    ):
        """_parse_yaml_frontmatter should handle invalid YAML gracefully."""
        test_file = temp_data_dir / "test.md"
        content = """---
invalid: yaml: content: here
---
"""
        test_file.write_text(content)

        # Should not raise exception
        parser = FileParser()
        frontmatter = parser.parse_yaml_frontmatter(test_file)
        assert isinstance(frontmatter, dict)

    def test_get_file_sync_status_no_previous_sync(self, file_synchronizer, db_manager):
        """get_file_sync_status should return empty status for new files."""
        file_path = "test_issue.md"
        status = file_synchronizer.get_file_sync_status(file_path)
        assert status is None

    def test_update_file_sync_status_inserts_new_record(
        self, file_synchronizer, db_manager, temp_data_dir
    ):
        """update_file_sync_status should insert new sync record."""
        test_file = temp_data_dir / "test.md"
        test_file.write_text("content")
        parser = FileParser()
        file_hash = parser.calculate_file_hash(test_file)
        file_size = test_file.stat().st_size
        last_modified = datetime.now(UTC)

        file_synchronizer.update_file_sync_status(
            str(test_file), file_hash, file_size, last_modified
        )

        status = file_synchronizer.get_file_sync_status(str(test_file))
        assert status is not None
        assert status["content_hash"] == file_hash
        assert status["file_size"] == file_size

    def test_update_file_sync_status_updates_existing_record(
        self, file_synchronizer, db_manager, temp_data_dir
    ):
        """update_file_sync_status should update existing sync record."""
        test_file = temp_data_dir / "test.md"
        test_file.write_text("content")
        parser = FileParser()
        file_hash1 = parser.calculate_file_hash(test_file)
        file_size1 = test_file.stat().st_size
        last_modified1 = datetime.now(UTC)

        file_synchronizer.update_file_sync_status(
            str(test_file), file_hash1, file_size1, last_modified1
        )

        # Update with new hash
        test_file.write_text("updated content")
        file_hash2 = parser.calculate_file_hash(test_file)
        file_size2 = test_file.stat().st_size
        last_modified2 = datetime.now(UTC)

        file_synchronizer.update_file_sync_status(
            str(test_file), file_hash2, file_size2, last_modified2
        )

        status = file_synchronizer.get_file_sync_status(str(test_file))
        assert status["content_hash"] == file_hash2
        assert status["file_size"] == file_size2

    def test_has_file_changed_detects_modifications(
        self, file_synchronizer, db_manager, temp_data_dir
    ):
        """has_file_changed should detect file modifications."""
        test_file = temp_data_dir / "test.md"
        test_file.write_text("original content")
        parser = FileParser()
        file_hash1 = parser.calculate_file_hash(test_file)
        file_size1 = test_file.stat().st_size
        last_modified1 = datetime.now(UTC)

        file_synchronizer.update_file_sync_status(
            str(test_file), file_hash1, file_size1, last_modified1
        )

        # Modify file
        test_file.write_text("modified content")

        assert file_synchronizer.has_file_changed(test_file)

    def test_has_file_changed_detects_no_changes(
        self, file_synchronizer, db_manager, temp_data_dir
    ):
        """has_file_changed should return False when file unchanged."""
        test_file = temp_data_dir / "test.md"
        test_file.write_text("content")
        parser = FileParser()
        file_hash = parser.calculate_file_hash(test_file)
        file_size = test_file.stat().st_size
        last_modified = datetime.now(UTC)

        file_synchronizer.update_file_sync_status(
            str(test_file), file_hash, file_size, last_modified
        )

        # Don't modify file - check immediately
        assert not file_synchronizer.has_file_changed(test_file)

    def test_has_file_changed_unknown_file(self, file_synchronizer):
        """has_file_changed should return True for unknown files."""
        assert file_synchronizer.has_file_changed(Path("unknown_file.md"))

    def test_should_do_full_rebuild_method_exists(self, file_synchronizer):
        """should_do_full_rebuild method should exist."""
        # Verify method exists
        assert hasattr(file_synchronizer, "should_do_full_rebuild")
        assert callable(file_synchronizer.should_do_full_rebuild)

    def test_sync_directory_incremental_returns_dict_or_bool(
        self, file_synchronizer, temp_data_dir
    ):
        """sync_directory_incremental should return result."""
        result = file_synchronizer.sync_directory_incremental(temp_data_dir)
        assert result is not None

    def test_full_rebuild_from_git_returns_dict_or_bool(
        self, file_synchronizer, temp_data_dir
    ):
        """full_rebuild_from_git should return result."""
        result = file_synchronizer.full_rebuild_from_git(temp_data_dir)
        assert result is not None
