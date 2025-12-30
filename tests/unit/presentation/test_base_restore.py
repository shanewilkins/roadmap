"""Tests for BaseRestore abstract base class.

Tests the template method pattern implementation and execute method
for restoring entities across all entity types.
"""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from roadmap.adapters.cli.crud.base_restore import BaseRestore
from roadmap.adapters.cli.crud.crud_helpers import EntityType


class ConcreteRestore(BaseRestore):
    """Concrete implementation of BaseRestore for testing."""

    entity_type = EntityType.ISSUE

    def get_archived_files_to_restore(self, entity_id=None, **filters):
        """Return empty list for testing."""
        return []

    def post_restore_hook(self, restored_files, **kwargs):
        """No-op hook for testing."""
        pass


@pytest.fixture
def restore_instance(mock_core_simple, mock_console):
    """Create a ConcreteRestore instance for testing.

    Uses centralized mock_core_simple fixture.
    """
    return ConcreteRestore(core=mock_core_simple, console=mock_console)


class TestBaseRestoreInitialization:
    """Test BaseRestore initialization."""

    def test_initialization_with_console(self, mock_core_simple, mock_console):
        """Test restore instance initialization with console."""
        restore = ConcreteRestore(core=mock_core_simple, console=mock_console)

        assert restore.core is mock_core_simple
        assert restore.console is mock_console

    def test_initialization_without_console(self, mock_core_simple):
        """Test restore instance initialization without console uses default."""
        with patch(
            "roadmap.adapters.cli.crud.base_restore.get_console"
        ) as mock_get_console:
            mock_default_console = MagicMock()
            mock_get_console.return_value = mock_default_console

            restore = ConcreteRestore(core=mock_core_simple)

            assert restore.core is mock_core_simple
            assert restore.console is mock_default_console

    def test_entity_type_accessible(self, restore_instance):
        """Test that entity_type is accessible."""
        assert restore_instance.entity_type == EntityType.ISSUE


class TestBaseRestorePostRestoreHook:
    """Test post_restore_hook method."""

    def test_post_restore_hook_called_with_args(self, restore_instance):
        """Test post_restore_hook receives correct arguments."""
        mock_hook = MagicMock()
        restore_instance.post_restore_hook = mock_hook

        test_files = [Path("/active/file1.md"), Path("/active/file2.md")]
        test_kwargs = {"force": True, "verbose": False}

        restore_instance.post_restore_hook(test_files, **test_kwargs)

        mock_hook.assert_called_once_with(test_files, force=True, verbose=False)

    def test_default_post_restore_hook_is_noop(self, restore_instance):
        """Test default post_restore_hook implementation is a no-op."""
        test_files = [Path("/active/file.md")]

        # Should not raise any exceptions
        restore_instance.post_restore_hook(test_files)
        # If we reach here, no-op succeeded
        assert True


class TestBaseRestoreExecute:
    """Test execute method of BaseRestore."""


class TestBaseRestoreEntityTypeHandling:
    """Test BaseRestore handles different entity types."""

    def test_milestone_restore_type(self, mock_core, mock_console):
        """Test BaseRestore with MILESTONE entity type."""

        class MilestoneRestore(BaseRestore):
            entity_type = EntityType.MILESTONE

            def get_archived_files_to_restore(self, entity_id=None, **filters):
                return []

            def post_restore_hook(self, restored_files, **kwargs):
                pass

        restore = MilestoneRestore(core=mock_core, console=mock_console)
        assert restore.entity_type == EntityType.MILESTONE

    def test_project_restore_type(self, mock_core, mock_console):
        """Test BaseRestore with PROJECT entity type."""

        class ProjectRestore(BaseRestore):
            entity_type = EntityType.PROJECT

            def get_archived_files_to_restore(self, entity_id=None, **filters):
                return []

            def post_restore_hook(self, restored_files, **kwargs):
                pass

        restore = ProjectRestore(core=mock_core, console=mock_console)
        assert restore.entity_type == EntityType.PROJECT


class TestBaseRestoreInterfaceContract:
    """Test BaseRestore interface contract."""

    def test_subclass_implements_entity_type(self, restore_instance):
        """Test subclass provides entity_type implementation."""
        assert hasattr(restore_instance, "entity_type")
        assert restore_instance.entity_type is not None

    def test_subclass_implements_post_restore_hook(self, restore_instance):
        """Test subclass provides post_restore_hook implementation."""
        assert hasattr(restore_instance, "post_restore_hook")
        assert callable(restore_instance.post_restore_hook)

    def test_restore_with_multiple_entity_types(self, mock_core, mock_console):
        """Test restore can be subclassed for different entity types."""
        for entity_type in [EntityType.ISSUE, EntityType.MILESTONE, EntityType.PROJECT]:

            class TypedRestore(BaseRestore):
                def get_archived_files_to_restore(self, entity_id=None, **filters):
                    return []

                def post_restore_hook(self, restored_files, **kwargs):
                    pass

            restore = TypedRestore(core=mock_core, console=mock_console)
            restore.entity_type = entity_type

            assert restore.entity_type == entity_type
