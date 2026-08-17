"""Protocol and abstract base class definitions for sync validation.

This module defines validators to ensure data integrity and prevent database
corruption during sync operations, particularly foreign key constraint violations.
"""

from abc import ABC, abstractmethod


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
