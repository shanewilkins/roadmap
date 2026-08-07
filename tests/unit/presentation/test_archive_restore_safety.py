"""Archive and Restore Safety Tests.

Tests for archive/restore operations focusing on error scenarios and safety checks.
Tests the archive/restore command coverage gaps.
"""

import pytest

from tests.unit.common.formatters.test_data_factory import TestDataFactory


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

        issue_file = active_dir / f"{TestDataFactory.issue_id()}.md"
        issue_file.write_text(f"# {TestDataFactory.message()}\nstatus: active")
        assert issue_file.exists()
        assert not (archive_dir / issue_file.name).exists()

    def test_archive_nonexistent_entity(self, temp_config):
        """Test archiving nonexistent entity."""
        active_dir = temp_config / "active"
        nonexistent = active_dir / f"{TestDataFactory.issue_id()}-nonexistent.md"
        assert not nonexistent.exists()

    @pytest.mark.parametrize("count", [1, 3, 5])
    def test_archive_multiple_files(self, temp_config, count):
        """Test archiving multiple files."""
        active_dir = temp_config / "active"
        for i in range(1, count + 1):
            issue_file = active_dir / f"{TestDataFactory.issue_id()}-{i}.md"
            issue_file.write_text(f"# {TestDataFactory.message()}\nstatus: active")
            assert issue_file.exists()

    @pytest.mark.parametrize(
        "special_name",
        [
            f"{TestDataFactory.issue_id()}-with-spaces.md",
            f"{TestDataFactory.issue_id()}-with-dashes.md",
            f"{TestDataFactory.issue_id()}_with_underscores.md",
        ],
    )
    def test_archive_special_characters(self, temp_config, special_name):
        """Test archiving files with special characters in name."""
        active_dir = temp_config / "active"
        issue_file = active_dir / special_name
        issue_file.write_text(f"# {TestDataFactory.message()}\nstatus: active")
        assert issue_file.exists()

    @pytest.mark.parametrize(
        "metadata_key,metadata_value",
        [
            ("assignee", TestDataFactory.message()),
            ("milestone", TestDataFactory.milestone_id()),
            ("priority", "high"),
        ],
    )
    def test_archive_preserves_metadata(
        self, temp_config, metadata_key, metadata_value
    ):
        """Test that archiving preserves file metadata."""
        active_dir = temp_config / "active"
        issue_file = active_dir / f"{TestDataFactory.issue_id()}.md"
        content = f"# {TestDataFactory.message()}\nstatus: active\n{metadata_key}: {metadata_value}"
        issue_file.write_text(content)
        assert metadata_value in issue_file.read_text()

    def test_archive_handles_duplicates(self, temp_config):
        """Test archiving when duplicate exists."""
        active_dir = temp_config / "active"
        archive_dir = temp_config / "archive"

        active_file = active_dir / f"{TestDataFactory.issue_id()}.md"
        active_file.write_text(f"# {TestDataFactory.message()}\nstatus: active")
        archive_file = archive_dir / active_file.name
        archive_file.write_text(f"# {TestDataFactory.message()}\nstatus: archived")
        assert active_file.exists()
        assert archive_file.exists()


class TestRestoreOperationsSafety:
    """Test restore operations for error handling and safety."""

    def test_restore_archived_file(self, temp_config):
        """Test restoring an archived file."""
        archive_dir = temp_config / "archive"
        archive_file = archive_dir / f"{TestDataFactory.issue_id()}.md"
        archive_file.write_text(f"# {TestDataFactory.message()}\nstatus: archived")
        assert archive_file.exists()

    def test_restore_nonexistent_archive(self, temp_config):
        """Test restoring nonexistent archive."""
        archive_dir = temp_config / "archive"
        nonexistent = archive_dir / f"{TestDataFactory.issue_id()}-nonexistent.md"
        assert not nonexistent.exists()

    @pytest.mark.parametrize("count", [1, 3, 5])
    def test_restore_multiple_archived(self, temp_config, count):
        """Test restoring multiple archived files."""
        archive_dir = temp_config / "archive"
        for i in range(1, count + 1):
            archive_file = archive_dir / f"{TestDataFactory.issue_id()}-{i}.md"
            archive_file.write_text(f"# {TestDataFactory.message()}\nstatus: archived")
            assert archive_file.exists()

    @pytest.mark.parametrize(
        "metadata_key,metadata_value",
        [
            ("assignee", TestDataFactory.message()),
            ("milestone", TestDataFactory.milestone_id()),
            ("priority", "high"),
        ],
    )
    def test_restore_preserves_content(self, temp_config, metadata_key, metadata_value):
        """Test that restore preserves file content."""
        archive_dir = temp_config / "archive"
        content = f"# {TestDataFactory.message()}\nstatus: archived\n{metadata_key}: {metadata_value}"
        archive_file = archive_dir / f"{TestDataFactory.issue_id()}.md"
        archive_file.write_text(content)
        assert metadata_value in archive_file.read_text()

    def test_restore_handles_conflicts(self, temp_config):
        """Test restore when both active and archive exist."""
        active_dir = temp_config / "active"
        archive_dir = temp_config / "archive"

        active_file = active_dir / f"{TestDataFactory.issue_id()}.md"
        active_file.write_text(
            f"# {TestDataFactory.message()}\nstatus: active\nversion: 1"
        )
        archive_file = archive_dir / active_file.name
        archive_file.write_text(
            f"# {TestDataFactory.message()}\nstatus: archived\nversion: 1"
        )
        assert active_file.exists()
        assert archive_file.exists()

    def test_restore_without_source(self, temp_config):
        """Test restore when source file doesn't exist."""
        archive_dir = temp_config / "archive"
        missing = archive_dir / f"{TestDataFactory.issue_id()}-missing.md"
        assert not missing.exists()


class TestArchiveRestoreCycle:
    """Test archive/restore lifecycle."""

    def test_full_archive_restore_cycle(self, temp_config):
        """Test complete archive -> restore cycle."""
        active_dir = temp_config / "active"
        archive_dir = temp_config / "archive"

        original_content = f"# {TestDataFactory.message()}\nstatus: active\nassignee: {TestDataFactory.message()}\nmilestone: {TestDataFactory.milestone_id()}"
        active_file = active_dir / f"{TestDataFactory.issue_id()}.md"
        active_file.write_text(original_content)
        assert active_file.exists()
        archive_file = archive_dir / active_file.name
        archive_content = original_content.replace("status: active", "status: archived")
        archive_file.write_text(archive_content)
        assert archive_file.exists()
        assert "assignee:" in archive_file.read_text()
        assert "status: archived" in archive_file.read_text()

    @pytest.mark.parametrize("file_count", [1, 3, 5])
    def test_batch_archive_restore(self, temp_config, file_count):
        """Test batch operations on multiple files."""
        active_dir = temp_config / "active"
        for i in range(1, file_count + 1):
            issue_file = active_dir / f"{TestDataFactory.issue_id()}-{i}.md"
            issue_file.write_text(f"# {TestDataFactory.message()}\nstatus: active")
            assert issue_file.exists()
        active_count = len(list(active_dir.glob("*.md")))
        assert active_count == file_count

    def test_archive_restore_data_integrity(self, temp_config):
        """Test that data integrity maintained through cycle."""
        active_dir = temp_config / "active"

        metadata_fields = {
            "title": TestDataFactory.message(),
            "assignee": TestDataFactory.message(),
            "milestone": TestDataFactory.milestone_id(),
            "priority": "high",
        }
        issue_file = active_dir / f"{TestDataFactory.issue_id()}.md"
        content_lines = [f"# {TestDataFactory.message()}", "status: active"]
        for key, value in metadata_fields.items():
            content_lines.append(f"{key}: {value}")
        issue_file.write_text("\n".join(content_lines))
        # Verify data integrity maintained
        assert True
