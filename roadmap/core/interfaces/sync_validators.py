"""Protocol and abstract base class definitions for sync validation.

This module defines validators to ensure data integrity and prevent database
corruption during sync operations, particularly foreign key constraint violations.
"""

from abc import ABC, abstractmethod
from typing import Any, Protocol


class ForeignKeyValidator(ABC):
    """Abstract base class for validating foreign key constraints before syncing.

    Ensures prerequisite data exists before syncing dependent entities,
    preventing FOREIGN KEY constraint violations.

    Example:
        validator = MilestoneFKValidator(db_connection)
        try:
            validator.validate()  # Raises if projects table is empty
        except ForeignKeyValidationError as e:
            logger.error(f"Validation failed: {e}")
            raise
    """

    @abstractmethod
    def validate(self) -> None:
        """Validate that all foreign key prerequisites exist.

        Raises:
            ForeignKeyValidationError: If prerequisite data doesn't exist
            RuntimeError: If database connection fails

        Notes:
            - Should fail fast on missing prerequisites
            - Must not swallow exceptions
            - Log specific missing references with entity IDs
        """
        ...

    @abstractmethod
    def missing_prerequisites(self) -> list[str]:
        """Return list of missing prerequisite entities.

        Returns:
            List of entity IDs or descriptions that are missing

        Example:
            ['project-id-1', 'project-id-2']
        """
        ...


class SyncPhaseOrder(Protocol):
    """Protocol defining ordered sync phases to prevent constraint violations.

    Ensures entities are synced in correct dependency order:
    1. Projects (no dependencies)
    2. Milestones (depends on projects)
    3. Issues (depends on projects and milestones)

    Implementation should enforce this ordering and fail if called out-of-order.
    """

    def validate_phase_order(self, current_phase: str, next_phase: str) -> bool:
        """Validate that phase transition is allowed.

        Args:
            current_phase: Current sync phase ('projects', 'milestones', 'issues')
            next_phase: Next sync phase to execute

        Returns:
            True if transition is valid, False otherwise

        Raises:
            ValueError: If phases are invalid or transition violates ordering
        """
        ...

    def get_phase_order(self) -> list[str]:
        """Get the canonical phase execution order.

        Returns:
            Ordered list of phases: ['projects', 'milestones', 'issues']
        """
        ...


class PreSyncValidator(Protocol):
    """Protocol for pre-sync validation with fail-fast semantics.

    Validates preconditions before any sync operations begin.
    Failures immediately abort sync to prevent partial state corruptions.
    """

    def validate_pre_sync(self, roadmap_dir: str | None = None) -> dict[str, Any]:
        """Validate preconditions before sync.

        Args:
            roadmap_dir: Optional roadmap directory path to validate

        Returns:
            dict with validation results:
            {
                'valid': bool,
                'errors': list[str],
                'warnings': list[str],
                'prerequisite_count': int
            }

        Raises:
            ValueError: If critical preconditions fail (fail-fast)
            RuntimeError: If database connection fails

        Notes:
            - Errors (critical) cause immediate abort via exception
            - Warnings (non-critical) logged but allow sync to proceed
            - Should check prerequisite tables before FK-dependent syncing
        """
        ...


class AtomicSyncPhase(Protocol):
    """Protocol for atomic sync operations (transaction-based).

    Wraps entity sync in transactions to ensure all-or-nothing semantics
    per sync phase.

    Usage:
        with atomic_sync('projects') as phase:
            sync_project_1()  # If any sync fails, entire phase rolls back
            sync_project_2()
    """

    def __enter__(self) -> "AtomicSyncPhase":
        """Enter atomic sync context (start transaction)."""
        ...

    def __exit__(self, exc_type: type, exc_val: Exception, exc_tb: Any) -> None:
        """Exit atomic sync context (commit or rollback)."""
        ...


class ForeignKeyValidationError(Exception):
    """Raised when foreign key validation fails.

    Indicates missing prerequisite data that would cause FK constraint
    violations if sync proceeded.

    Attributes:
        entity_type: Type of entity with missing FK (e.g., 'milestone')
        missing_references: List of missing referenced entity IDs
        error_details: Detailed error message with context
    """

    def __init__(
        self,
        entity_type: str,
        missing_references: list[str],
        error_details: str,
    ):
        """Initialize validation error.

        Args:
            entity_type: Type of entity that failed validation
            missing_references: IDs of missing prerequisite entities
            error_details: Detailed error context
        """
        self.entity_type = entity_type
        self.missing_references = missing_references
        self.error_details = error_details
        super().__init__(
            f"FK validation failed for {entity_type}: "
            f"missing {len(missing_references)} references. {error_details}"
        )
