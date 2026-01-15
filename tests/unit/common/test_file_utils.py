"""Unit tests for file utilities."""

from pathlib import Path

import pytest

from roadmap.common.utils.file_utils import (
    ensure_directory_exists,
    file_exists_check,
    safe_read_file,
    safe_write_file,
)


class TestFileOperations:
    """Test file operations."""

    def test_ensure_directory_exists(self, temp_dir):
        """Test ensuring directory exists."""
        test_dir = temp_dir / "test_dir"

        ensure_directory_exists(test_dir)

        assert test_dir.exists()

    def test_ensure_directory_exists_already_exists(self, temp_dir):
        """Test ensuring directory when it already exists."""
        ensure_directory_exists(temp_dir)

        assert temp_dir.exists()

    def test_safe_write_file(self, temp_dir):
        """Test writing a file safely."""
        test_file = temp_dir / "test.txt"
        content = "test content"

        safe_write_file(test_file, content)

        assert test_file.exists()
        assert test_file.read_text() == content

    def test_safe_read_file(self, temp_dir):
        """Test reading a file safely."""
        test_file = temp_dir / "test.txt"
        content = "test content"
        test_file.write_text(content)

        result = safe_read_file(test_file)

        assert result == content

    def test_safe_read_nonexistent_file(self):
        """Test reading nonexistent file."""
        nonexistent = Path("/nonexistent/path/file.txt")

        with pytest.raises(FileNotFoundError):
            safe_read_file(nonexistent)

    def test_file_exists_check_true(self, temp_dir):
        """Test file exists check when true."""
        test_file = temp_dir / "test.txt"
        test_file.write_text("content")

        result = file_exists_check(test_file)

        assert result is True

    def test_file_exists_check_false(self):
        """Test file exists check when false."""
        nonexistent = Path("/nonexistent/file.txt")

        result = file_exists_check(nonexistent)

        assert result is False

    def test_write_and_read_roundtrip(self, temp_dir):
        """Test write and read roundtrip."""
        test_file = temp_dir / "test.txt"
        original_content = "test content\nwith newlines"

        safe_write_file(test_file, original_content)
        read_content = safe_read_file(test_file)

        assert read_content == original_content

    def test_write_file_creates_parent_directories(self, temp_dir):
        """Test that write file creates parent directories."""
        test_file = temp_dir / "subdir" / "nested" / "test.txt"
        content = "test content"

        # Ensure parent doesn't exist yet
        assert not test_file.parent.exists()

        safe_write_file(test_file, content)

        assert test_file.exists()
        assert test_file.read_text() == content

    def test_safe_read_with_different_encodings(self, temp_dir):
        """Test reading file with different encoding."""
        test_file = temp_dir / "test.txt"
        content = "test content"
        test_file.write_text(content, encoding="utf-8")

        result = safe_read_file(test_file, encoding="utf-8")

        assert result == content
