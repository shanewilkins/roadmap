"""Unit tests for sync_metadata in YAML frontmatter.

Tests cover:
- Parsing sync_metadata from issue files
- Saving sync_metadata to issue files
- Updating sync_metadata without modifying the issue
- Round-trip serialization/deserialization
"""

import tempfile
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from roadmap.adapters.persistence.parser.frontmatter import FrontmatterParser
from roadmap.adapters.persistence.parser.issue import IssueParser
from roadmap.core.domain import Issue, IssueType, Priority, Status


class TestFrontmatterSyncMetadata:
    """Test sync_metadata handling in FrontmatterParser."""

    def test_extract_sync_metadata_present(self):
        """Test extracting sync_metadata when present."""
        frontmatter: dict[str, Any] = {
            "id": "issue1",
            "title": "Test Issue",
            "sync_metadata": {
                "last_synced": "2026-01-03T10:00:00+00:00",
                "last_updated": "2026-01-03T11:00:00+00:00",
                "remote_state": {"status": "open"},
            },
        }

        result = FrontmatterParser.extract_sync_metadata(frontmatter)

        assert result is not None
        assert isinstance(result, dict)
        assert result.get("last_synced") == "2026-01-03T10:00:00+00:00"
        remote_state = result.get("remote_state")
        assert isinstance(remote_state, dict)
        assert remote_state.get("status") == "open"

    def test_extract_sync_metadata_absent(self):
        """Test extracting sync_metadata when absent."""
        frontmatter: dict[str, Any] = {
            "id": "issue1",
            "title": "Test Issue",
        }

        result = FrontmatterParser.extract_sync_metadata(frontmatter)

        assert result is None

    def test_update_sync_metadata_add_new(self):
        """Test adding sync_metadata to frontmatter."""
        frontmatter: dict[str, Any] = {"id": "issue1", "title": "Test Issue"}

        sync_metadata = {
            "last_synced": "2026-01-03T10:00:00+00:00",
            "remote_state": {"status": "open"},
        }
        FrontmatterParser.update_sync_metadata(frontmatter, sync_metadata)

        sync_meta = frontmatter.get("sync_metadata")
        assert sync_meta is not None
        assert isinstance(sync_meta, dict)
        assert sync_meta.get("last_synced") == "2026-01-03T10:00:00+00:00"

    def test_update_sync_metadata_replace_existing(self):
        """Test updating existing sync_metadata."""
        frontmatter = {
            "id": "issue1",
            "sync_metadata": {
                "last_synced": "2026-01-01T10:00:00+00:00",
            },
        }

        new_metadata = {"last_synced": "2026-01-03T10:00:00+00:00"}
        FrontmatterParser.update_sync_metadata(frontmatter, new_metadata)

        assert (
            frontmatter["sync_metadata"]["last_synced"] == "2026-01-03T10:00:00+00:00"
        )

    def test_update_sync_metadata_remove_none(self):
        """Test removing sync_metadata when None."""
        frontmatter: dict[str, dict | str] = {
            "id": "issue1",
            "sync_metadata": {"last_synced": "2026-01-03T10:00:00+00:00"},
        }

        FrontmatterParser.update_sync_metadata(frontmatter, None)  # type: ignore

        assert "sync_metadata" not in frontmatter

    def test_update_sync_metadata_datetime_conversion(self):
        """Test that datetime objects are converted to ISO strings."""
        frontmatter = {"id": "issue1"}

        sync_metadata = {
            "last_synced": datetime(2026, 1, 3, 10, 0, 0, tzinfo=UTC),
            "remote_state": {"updated_at": datetime(2026, 1, 3, 11, 0, 0, tzinfo=UTC)},
        }
        FrontmatterParser.update_sync_metadata(frontmatter, sync_metadata)

        sync_meta = frontmatter.get("sync_metadata")
        assert sync_meta is not None
        assert isinstance(sync_meta, dict)
        last_synced = sync_meta.get("last_synced")
        assert isinstance(last_synced, str)
        assert "2026-01-03T10:00:00" in last_synced
        remote_state = sync_meta.get("remote_state")
        assert isinstance(remote_state, dict)
        updated_at = remote_state.get("updated_at")
        assert isinstance(updated_at, str)


class TestIssueSyncMetadata:
    """Test sync_metadata handling in IssueParser."""

    def test_load_sync_metadata_from_file(self, temp_dir_context):
        """Test loading sync_metadata from an issue file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            file_path = Path(tmpdir) / "issue.md"

            # Create a file with sync_metadata
            frontmatter_dict: dict[str, Any] = {
                "id": "issue1",
                "title": "Test Issue",
                "sync_metadata": {
                    "last_synced": "2026-01-03T10:00:00+00:00",
                    "remote_state": {"status": "open"},
                },
            }

            FrontmatterParser.serialize_file(
                frontmatter_dict, "Content here", file_path
            )

            # Load only sync_metadata
            result = IssueParser.load_sync_metadata(file_path)

            assert result is not None
            assert isinstance(result, dict)
            assert result.get("last_synced") == "2026-01-03T10:00:00+00:00"
            remote_state = result.get("remote_state")
            assert isinstance(remote_state, dict)
            assert remote_state.get("status") == "open"

    def test_load_sync_metadata_not_present(self, temp_dir_context):
        """Test loading sync_metadata when not present."""
        with tempfile.TemporaryDirectory() as tmpdir:
            file_path = Path(tmpdir) / "issue.md"

            # Create a file without sync_metadata
            frontmatter_dict = {
                "id": "issue1",
                "title": "Test Issue",
            }

            FrontmatterParser.serialize_file(frontmatter_dict, "Content", file_path)

            result = IssueParser.load_sync_metadata(file_path)

            assert result is None

    def test_save_issue_with_sync_metadata(self, temp_dir_context):
        """Test saving an issue with sync_metadata."""
        with tempfile.TemporaryDirectory() as tmpdir:
            file_path = Path(tmpdir) / "issue.md"

            issue = Issue(
                id="issue1",
                title="Test Issue",
                priority=Priority.MEDIUM,
                status=Status.TODO,
                issue_type=IssueType.FEATURE,
            )

            sync_metadata = {
                "last_synced": "2026-01-03T10:00:00+00:00",
                "remote_state": {"status": "open"},
            }

            IssueParser.save_issue_file(issue, file_path, sync_metadata=sync_metadata)

            # Verify file contains sync_metadata
            loaded_metadata = IssueParser.load_sync_metadata(file_path)
            assert loaded_metadata is not None
            assert loaded_metadata["last_synced"] == "2026-01-03T10:00:00+00:00"

    def test_update_issue_sync_metadata_only(self, temp_dir_context):
        """Test updating only sync_metadata without modifying the issue."""
        with tempfile.TemporaryDirectory() as tmpdir:
            file_path = Path(tmpdir) / "issue.md"

            # Create initial issue with content
            issue = Issue(
                id="issue1",
                title="Original Title",
                priority=Priority.HIGH,
                status=Status.IN_PROGRESS,
                issue_type=IssueType.BUG,
                content="Original content",
            )

            IssueParser.save_issue_file(issue, file_path)

            # Update only sync_metadata
            new_metadata = {
                "last_synced": "2026-01-03T10:00:00+00:00",
                "remote_state": {"status": "closed"},
            }
            IssueParser.update_issue_sync_metadata(file_path, new_metadata)

            # Verify sync_metadata updated
            loaded_metadata = IssueParser.load_sync_metadata(file_path)
            assert loaded_metadata is not None
            assert isinstance(loaded_metadata, dict)
            assert loaded_metadata.get("last_synced") == "2026-01-03T10:00:00+00:00"  # type: ignore

            # Verify issue content unchanged
            loaded_issue = IssueParser.parse_issue_file(file_path)
            assert loaded_issue.title == "Original Title"
            assert loaded_issue.priority == Priority.HIGH
            assert loaded_issue.content == "Original content"

    def test_roundtrip_sync_metadata(self, temp_dir_context):
        """Test round-trip serialization and deserialization of sync_metadata."""
        with tempfile.TemporaryDirectory() as tmpdir:
            file_path = Path(tmpdir) / "issue.md"

            original_metadata = {
                "last_synced": "2026-01-03T10:00:00+00:00",
                "last_updated": "2026-01-03T11:00:00+00:00",
                "remote_state": {
                    "status": "open",
                    "assignee": "user@example.com",
                    "updated_at": "2026-01-03T11:00:00+00:00",
                },
            }

            issue = Issue(
                id="issue1",
                title="Test Issue",
                priority=Priority.MEDIUM,
                status=Status.TODO,
                issue_type=IssueType.FEATURE,
            )

            # Save with sync_metadata
            IssueParser.save_issue_file(
                issue, file_path, sync_metadata=original_metadata
            )

            # Load back
            loaded_metadata = IssueParser.load_sync_metadata(file_path)

            assert loaded_metadata == original_metadata

    def test_sync_metadata_with_complex_remote_state(self, temp_dir_context):
        """Test sync_metadata with nested remote_state structure."""
        with tempfile.TemporaryDirectory() as tmpdir:
            file_path = Path(tmpdir) / "issue.md"

            metadata = {
                "last_synced": "2026-01-03T10:00:00+00:00",
                "remote_state": {
                    "id": "gh-12345",
                    "status": "open",
                    "assignees": ["user1", "user2"],
                    "labels": ["bug", "urgent"],
                    "updated_at": "2026-01-03T11:00:00+00:00",
                    "nested": {
                        "deeply": {
                            "nested": "value",
                        }
                    },
                },
            }

            issue = Issue(
                id="issue1",
                title="Test Issue",
                priority=Priority.MEDIUM,
                status=Status.TODO,
                issue_type=IssueType.FEATURE,
            )

            IssueParser.save_issue_file(issue, file_path, sync_metadata=metadata)

            loaded_metadata = IssueParser.load_sync_metadata(file_path)

            assert loaded_metadata is not None
            assert isinstance(loaded_metadata, dict)
            remote_state = loaded_metadata.get("remote_state")
            assert isinstance(remote_state, dict)
            assert remote_state.get("assignees") == ["user1", "user2"]  # type: ignore
            assert remote_state.get("labels") == ["bug", "urgent"]  # type: ignore
            nested = remote_state.get("nested")
            assert isinstance(nested, dict)
            deeply = nested.get("deeply")
            assert isinstance(deeply, dict)
            assert deeply.get("nested") == "value"
