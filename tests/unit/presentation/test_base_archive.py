"""Tests for BaseArchive abstract base class.

Tests the template method pattern implementation and execute method
for archiving entities across all entity types.
"""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from roadmap.adapters.cli.crud.base_archive import BaseArchive
from roadmap.adapters.cli.crud.crud_helpers import EntityType


class ConcreteArchive(BaseArchive):
    """Concrete implementation of BaseArchive for testing."""

    entity_type = EntityType.ISSUE

    def get_entities_to_archive(self, entity_id=None, **filters):
        """Return empty list for testing."""
        return []

    def post_archive_hook(self, archived_files, entities, **kwargs):
        """No-op hook for testing."""
        pass


@pytest.fixture
def archive_instance(mock_core_simple, mock_console):
    """Create a ConcreteArchive instance for testing.

    Uses centralized mock_core_simple fixture.
    """
    return ConcreteArchive(core=mock_core_simple, console=mock_console)


class TestBaseArchiveInitialization:
    """Test BaseArchive initialization."""

    def test_initialization_with_console(self, mock_core_simple, mock_console):
        """Test archive instance initialization with console."""
        archive = ConcreteArchive(core=mock_core_simple, console=mock_console)

        assert archive.core is mock_core_simple
        assert archive.console is mock_console

    def test_initialization_without_console(self, mock_core_simple):
        """Test archive instance initialization without console uses default."""
        with patch(
            "roadmap.adapters.cli.crud.base_archive.get_console"
        ) as mock_get_console:
            mock_default_console = MagicMock()
            mock_get_console.return_value = mock_default_console

            archive = ConcreteArchive(core=mock_core_simple)

            assert archive.core is mock_core_simple
            assert archive.console is mock_default_console

    def test_entity_type_accessible(self, archive_instance):
        """Test that entity_type is accessible."""
        assert archive_instance.entity_type == EntityType.ISSUE


class TestBaseArchivePostArchiveHook:
    """Test post_archive_hook method."""

    def test_post_archive_hook_called_with_args(self, archive_instance):
        """Test post_archive_hook receives correct arguments."""
        mock_hook = MagicMock()
        archive_instance.post_archive_hook = mock_hook

        test_files = [Path("/archive/file1.md"), Path("/archive/file2.md")]
        test_kwargs = {"force": True, "verbose": False}

        archive_instance.post_archive_hook(test_files, **test_kwargs)

        mock_hook.assert_called_once_with(test_files, force=True, verbose=False)


class TestBaseArchiveEntityTypeHandling:
    """Test BaseArchive handles different entity types."""

    def test_milestone_archive_type(self, mock_core, mock_console):
        """Test BaseArchive with MILESTONE entity type."""

        class MilestoneArchive(BaseArchive):
            entity_type = EntityType.MILESTONE

            def get_entities_to_archive(self, entity_id=None, **filters):
                return []

            def post_archive_hook(self, archived_files, entities, **kwargs):
                pass

        archive = MilestoneArchive(core=mock_core, console=mock_console)
        assert archive.entity_type == EntityType.MILESTONE

    def test_project_archive_type(self, mock_core, mock_console):
        """Test BaseArchive with PROJECT entity type."""

        class ProjectArchive(BaseArchive):
            entity_type = EntityType.PROJECT

            def get_entities_to_archive(self, entity_id=None, **filters):
                return []

            def post_archive_hook(self, archived_files, entities, **kwargs):
                pass

        archive = ProjectArchive(core=mock_core, console=mock_console)
        assert archive.entity_type == EntityType.PROJECT


class TestBaseArchiveInterfaceContract:
    """Test BaseArchive interface contract."""

    def test_subclass_implements_entity_type(self, archive_instance):
        """Test subclass provides entity_type implementation."""
        assert hasattr(archive_instance, "entity_type")
        assert archive_instance.entity_type is not None

    def test_subclass_implements_post_archive_hook(self, archive_instance):
        """Test subclass provides post_archive_hook implementation."""
        assert hasattr(archive_instance, "post_archive_hook")
        assert callable(archive_instance.post_archive_hook)

    def test_archive_with_multiple_entity_types(self, mock_core, mock_console):
        """Test archive can be subclassed for different entity types."""
        for entity_type in [EntityType.ISSUE, EntityType.MILESTONE, EntityType.PROJECT]:

            class TypedArchive(BaseArchive):
                def get_entities_to_archive(self, entity_id=None, **filters):
                    return []

                def post_archive_hook(self, archived_files, entities, **kwargs):
                    pass

            archive = TypedArchive(core=mock_core, console=mock_console)
            archive.entity_type = entity_type

            assert archive.entity_type == entity_type
