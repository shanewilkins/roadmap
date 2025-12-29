"""Tests for archive and restore base and concrete classes."""

import tempfile
from pathlib import Path
from unittest.mock import MagicMock, Mock, patch

import pytest

from roadmap.adapters.cli.crud import BaseArchive, BaseRestore, EntityType
from roadmap.adapters.cli.issues.archive_class import IssueArchive
from roadmap.adapters.cli.issues.restore_class import IssueRestore
from roadmap.adapters.cli.milestones.archive_class import MilestoneArchive
from roadmap.adapters.cli.milestones.restore_class import MilestoneRestore
from roadmap.adapters.cli.projects.archive_class import ProjectArchive
from roadmap.adapters.cli.projects.restore_class import ProjectRestore


class MockEntity:
    """Mock entity for testing."""

    def __init__(self, entity_id, name="Test", status="open"):
        self.id = entity_id
        self.name = name
        self.title = f"Test {name}"
        self.milestone: str | None = "v1.0"
        self.status = Mock(value=status)


class TestIssueArchive:
    """Test IssueArchive class."""

    def setup_method(self):
        """Set up test fixtures."""
        self.mock_core = Mock()
        self.mock_console = Mock()
        self.archive = IssueArchive(self.mock_core, self.mock_console)

    def test_issue_archive_initialization(self):
        """Test IssueArchive initializes with correct entity type."""
        assert self.archive.entity_type == EntityType.ISSUE
        assert self.archive.core == self.mock_core
        assert self.archive.console == self.mock_console

    def test_get_entities_to_archive_by_id(self):
        """Test getting a single entity by ID."""
        entity = MockEntity("issue-123")
        self.mock_core.issues.get.return_value = entity

        result = self.archive.get_entities_to_archive("issue-123")

        assert result == [entity]
        self.mock_core.issues.get.assert_called_once_with("issue-123")

    def test_get_entities_to_archive_all_closed(self):
        """Test getting all closed issues."""
        closed_issue = MockEntity("closed-1", status="closed")
        open_issue = MockEntity("open-1", status="open")
        self.mock_core.issues.list.return_value = [closed_issue, open_issue]

        result = self.archive.get_entities_to_archive(all_closed=True)

        assert result == [closed_issue]

    def test_get_entities_to_archive_orphaned(self):
        """Test getting orphaned issues."""
        orphaned = MockEntity("orphan-1")
        orphaned.milestone = None
        with_milestone = MockEntity("milestone-1")
        self.mock_core.issues.list.return_value = [orphaned, with_milestone]

        result = self.archive.get_entities_to_archive(orphaned=True)

        assert result == [orphaned]

    def test_validate_entity_before_archive_closed(self):
        """Test validation of closed issues."""
        entity = MockEntity("issue-1", status="closed")

        is_valid, error = self.archive.validate_entity_before_archive(entity)

        assert is_valid is True
        assert error is None

    def test_validate_entity_before_archive_open(self):
        """Test validation rejects open issues."""
        entity = MockEntity("issue-1", status="open")

        is_valid, error = self.archive.validate_entity_before_archive(entity)

        assert is_valid is False
        assert error is not None
        assert "not closed" in error


class TestIssueRestore:
    """Test IssueRestore class."""

    def setup_method(self):
        """Set up test fixtures."""
        self.mock_core = Mock()
        self.mock_console = Mock()
        self.restore = IssueRestore(self.mock_core, self.mock_console)

    def test_issue_restore_initialization(self):
        """Test IssueRestore initializes with correct entity type."""
        assert self.restore.entity_type == EntityType.ISSUE
        assert self.restore.core == self.mock_core

    @patch("roadmap.adapters.cli.crud.crud_helpers.get_archive_dir")
    def test_get_archived_files_to_restore_no_archive(self, mock_get_archive_dir):
        """Test when archive directory doesn't exist."""
        mock_archive_dir = MagicMock()
        mock_archive_dir.exists.return_value = False
        mock_get_archive_dir.return_value = mock_archive_dir

        result = self.restore.get_archived_files_to_restore()

        assert result == []

    @patch("roadmap.adapters.cli.crud.crud_helpers.get_archive_dir")
    def test_get_archived_files_to_restore_all(self, mock_get_archive_dir):
        """Test getting all archived files."""
        with tempfile.TemporaryDirectory() as tmpdir:
            archive_dir = Path(tmpdir)
            archive_dir.mkdir(exist_ok=True)
            (archive_dir / "issue1.md").write_text("test")
            (archive_dir / "issue2.md").write_text("test")

            mock_get_archive_dir.return_value = archive_dir

            result = self.restore.get_archived_files_to_restore()

            assert len(result) == 2


class TestMilestoneArchive:
    """Test MilestoneArchive class."""

    def setup_method(self):
        """Set up test fixtures."""
        self.mock_core = Mock()
        self.mock_console = Mock()
        self.archive = MilestoneArchive(self.mock_core, self.mock_console)

    def test_milestone_archive_initialization(self):
        """Test MilestoneArchive initializes with correct entity type."""
        assert self.archive.entity_type == EntityType.MILESTONE

    def test_get_entities_to_archive_all_closed_milestones(self):
        """Test getting all closed milestones."""
        closed = MockEntity("m1", "v1.0", "closed")
        open_m = MockEntity("m2", "v2.0", "open")
        self.mock_core.milestones.list.return_value = [closed, open_m]

        result = self.archive.get_entities_to_archive(all_closed=True)

        assert result == [closed]

    def test_validate_milestone_before_archive(self):
        """Test milestone validation."""
        entity = MockEntity("m1", "v1.0", "closed")

        is_valid, error = self.archive.validate_entity_before_archive(entity)

        assert is_valid is True


class TestMilestoneRestore:
    """Test MilestoneRestore class."""

    def setup_method(self):
        """Set up test fixtures."""
        self.mock_core = Mock()
        self.mock_console = Mock()
        self.restore = MilestoneRestore(self.mock_core, self.mock_console)

    def test_milestone_restore_initialization(self):
        """Test MilestoneRestore initializes with correct entity type."""
        assert self.restore.entity_type == EntityType.MILESTONE


class TestProjectArchive:
    """Test ProjectArchive class."""

    def setup_method(self):
        """Set up test fixtures."""
        self.mock_core = Mock()
        self.mock_console = Mock()
        self.archive = ProjectArchive(self.mock_core, self.mock_console)

    def test_project_archive_initialization(self):
        """Test ProjectArchive initializes with correct entity type."""
        assert self.archive.entity_type == EntityType.PROJECT

    def test_get_entities_to_archive_by_id(self):
        """Test getting a project by ID."""
        entity = MockEntity("proj-1")
        self.mock_core.projects.get.return_value = entity

        result = self.archive.get_entities_to_archive("proj-1")

        assert result == [entity]


class TestProjectRestore:
    """Test ProjectRestore class."""

    def setup_method(self):
        """Set up test fixtures."""
        self.mock_core = Mock()
        self.mock_console = Mock()
        self.restore = ProjectRestore(self.mock_core, self.mock_console)

    def test_project_restore_initialization(self):
        """Test ProjectRestore initializes with correct entity type."""
        assert self.restore.entity_type == EntityType.PROJECT


class TestBaseArchiveTemplateMethod:
    """Test BaseArchive template method pattern."""

    def test_base_archive_requires_get_entities_to_archive(self):
        """Test BaseArchive requires subclass to implement get_entities_to_archive."""
        with pytest.raises(TypeError):
            BaseArchive(Mock())  # type: ignore  # noqa: F841


class TestBaseRestoreTemplateMethod:
    """Test BaseRestore template method pattern."""

    def test_base_restore_requires_get_archived_files_to_restore(self):
        """Test BaseRestore requires subclass to implement get_archived_files_to_restore."""
        with pytest.raises(TypeError):
            BaseRestore(Mock())  # type: ignore  # noqa: F841
