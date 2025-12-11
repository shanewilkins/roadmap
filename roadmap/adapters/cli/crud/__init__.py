"""CRUD operations base classes and shared utilities.

This module provides:
- Base classes for Create, Update, Delete, Archive, Restore operations
- Shared CRUD helpers and utilities
- Entity-specific builders and validators
- Template method pattern for extensible CRUD implementations
"""

from roadmap.adapters.cli.crud.base_archive import BaseArchive
from roadmap.adapters.cli.crud.base_create import BaseCreate
from roadmap.adapters.cli.crud.base_delete import BaseDelete
from roadmap.adapters.cli.crud.base_restore import BaseRestore
from roadmap.adapters.cli.crud.base_update import BaseUpdate
from roadmap.adapters.cli.crud.crud_helpers import (
    CRUDOperation,
    EntityType,
    collect_archive_files,
    display_archive_success,
    display_restore_success,
    format_entity_id,
    format_entity_title,
    get_active_dir,
    get_archive_dir,
    validate_entity_exists,
)

__all__ = [
    # Enums
    "EntityType",
    "CRUDOperation",
    # Base classes
    "BaseCreate",
    "BaseUpdate",
    "BaseDelete",
    "BaseArchive",
    "BaseRestore",
    # Helpers
    "validate_entity_exists",
    "format_entity_title",
    "format_entity_id",
    "collect_archive_files",
    "get_archive_dir",
    "get_active_dir",
    "display_archive_success",
    "display_restore_success",
]
