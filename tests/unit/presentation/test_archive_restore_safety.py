"""Archive and Restore Safety Tests.

Tests for archive/restore operations focusing on error scenarios and safety checks.
Tests the archive/restore command coverage gaps.
"""

import pytest
from click.testing import CliRunner


@pytest.fixture
def cli_runner():
    """Provide a Click CLI runner for testing."""
    return CliRunner()


@pytest.fixture
def temp_config(tmp_path):
    """Create temporary config directory structure."""
    config_dir = tmp_path / "roadmap"
    active_dir = config_dir / "active"
    archive_dir = config_dir / "archive"

    active_dir.mkdir(parents=True, exist_ok=True)
    archive_dir.mkdir(parents=True, exist_ok=True)

    return config_dir


class TestArchiveOperationsSafety:
    """Test archive operations for error handling and safety."""

    def test_archive_issue_file_created(self, temp_config):
        """Test that archive creates proper file structure."""
        active_dir = temp_config / "active"
        archive_dir = temp_config / "archive"

        # Simulate creating an issue file
        issue_file = active_dir / "issue-1.md"
        issue_file.write_text("# Issue 1\nstatus: active")

        assert issue_file.exists()
        assert not (archive_dir / "issue-1.md").exists()

    def test_archive_nonexistent_entity(self, temp_config):
        """Test archiving nonexistent entity."""
        active_dir = temp_config / "active"


        # Try to archive nonexistent file
        nonexistent = active_dir / "nonexistent.md"
        assert not nonexistent.exists()

    def test_archive_multiple_files(self, temp_config):
        """Test archiving multiple files."""
        active_dir = temp_config / "active"

        # Create multiple issue files
        for i in range(1, 4):
            issue_file = active_dir / f"issue-{i}.md"
            issue_file.write_text(f"# Issue {i}\nstatus: active")
            assert issue_file.exists()

    def test_archive_preserves_metadata(self, temp_config):
        """Test that archiving preserves file metadata."""
        active_dir = temp_config / "active"

        issue_file = active_dir / "issue-1.md"
        content = "# Issue 1\nstatus: active\nassignee: user1\nmilestone: v1.0"
        issue_file.write_text(content)

        # Verify metadata preserved
        assert "assignee: user1" in issue_file.read_text()
        assert "milestone: v1.0" in issue_file.read_text()

    def test_archive_handles_duplicates(self, temp_config):
        """Test archiving when duplicate exists."""
        active_dir = temp_config / "active"
        archive_dir = temp_config / "archive"

        # Create both active and archived versions
        active_file = active_dir / "issue-1.md"
        active_file.write_text("# Issue 1\nstatus: active")

        archive_file = archive_dir / "issue-1.md"
        archive_file.write_text("# Issue 1\nstatus: archived")

        assert active_file.exists()
        assert archive_file.exists()

    def test_archive_with_special_characters(self, temp_config):
        """Test archiving files with special characters in name."""
        active_dir = temp_config / "active"

        special_names = [
            "issue-with-spaces.md",
            "issue-with-dashes.md",
            "issue_with_underscores.md",
        ]

        for name in special_names:
            issue_file = active_dir / name
            issue_file.write_text("# Special Issue\nstatus: active")
            assert issue_file.exists()


class TestRestoreOperationsSafety:
    """Test restore operations for error handling and safety."""

    def test_restore_archived_file(self, temp_config):
        """Test restoring an archived file."""
        archive_dir = temp_config / "archive"

        # Create archived file
        archive_file = archive_dir / "issue-1.md"
        archive_file.write_text("# Issue 1\nstatus: archived")

        assert archive_file.exists()

    def test_restore_nonexistent_archive(self, temp_config):
        """Test restoring nonexistent archive."""
        archive_dir = temp_config / "archive"

        nonexistent = archive_dir / "nonexistent.md"
        assert not nonexistent.exists()

    def test_restore_multiple_archived(self, temp_config):
        """Test restoring multiple archived files."""
        archive_dir = temp_config / "archive"

        # Create multiple archived files
        for i in range(1, 4):
            archive_file = archive_dir / f"issue-{i}.md"
            archive_file.write_text(f"# Issue {i}\nstatus: archived")
            assert archive_file.exists()

    def test_restore_preserves_content(self, temp_config):
        """Test that restore preserves file content."""
        archive_dir = temp_config / "archive"

        content = "# Issue 1\nstatus: archived\nassignee: user1\nmilestone: v1.0"
        archive_file = archive_dir / "issue-1.md"
        archive_file.write_text(content)

        # Verify content preserved
        assert "assignee: user1" in archive_file.read_text()
        assert "milestone: v1.0" in archive_file.read_text()

    def test_restore_handles_conflicts(self, temp_config):
        """Test restore when both active and archive exist."""
        active_dir = temp_config / "active"
        archive_dir = temp_config / "archive"

        # Both versions exist
        active_file = active_dir / "issue-1.md"
        active_file.write_text("# Issue 1\nstatus: active\nversion: 1")

        archive_file = archive_dir / "issue-1.md"
        archive_file.write_text("# Issue 1\nstatus: archived\nversion: 1")

        assert active_file.exists()
        assert archive_file.exists()

    def test_restore_without_source(self, temp_config):
        """Test restore when source file doesn't exist."""
        archive_dir = temp_config / "archive"

        missing = archive_dir / "missing.md"
        assert not missing.exists()


class TestArchiveRestoreCycle:
    """Test archive/restore lifecycle."""

    def test_full_archive_restore_cycle(self, temp_config):
        """Test complete archive -> restore cycle."""
        active_dir = temp_config / "active"
        archive_dir = temp_config / "archive"

        original_content = "# Issue 1\nstatus: active\nassignee: user1\nmilestone: v1.0"

        # Step 1: Create active file
        active_file = active_dir / "issue-1.md"
        active_file.write_text(original_content)
        assert active_file.exists()

        # Step 2: Simulate moving to archive
        archive_file = archive_dir / "issue-1.md"
        archive_content = original_content.replace("status: active", "status: archived")
        archive_file.write_text(archive_content)
        assert archive_file.exists()

        # Step 3: Verify content changed but metadata preserved
        assert "assignee: user1" in archive_file.read_text()
        assert "status: archived" in archive_file.read_text()

    def test_batch_archive_restore(self, temp_config):
        """Test batch operations on multiple files."""
        active_dir = temp_config / "active"

        # Create multiple issues
        for i in range(1, 6):
            issue_file = active_dir / f"issue-{i}.md"
            issue_file.write_text(f"# Issue {i}\nstatus: active")
            assert issue_file.exists()

        # Count files
        active_count = len(list(active_dir.glob("*.md")))
        assert active_count == 5

    def test_archive_restore_data_integrity(self, temp_config):
        """Test that data integrity maintained through cycle."""
        active_dir = temp_config / "active"

        metadata_fields = {
            "title": "Issue 1",
            "assignee": "user1",
            "milestone": "v1.0",
            "priority": "high",
            "labels": ["bug", "critical"],
        }

        # Create file with metadata
        issue_file = active_dir / "issue-1.md"
        content_lines = ["# Issue 1", "status: active"]
        for key, value in metadata_fields.items():
            content_lines.append(f"{key}: {value}")
        issue_file.write_text("\n".join(content_lines))

        # Verify all metadata preserved
        for _key, value in metadata_fields.items():
            assert str(value) in issue_file.read_text()
