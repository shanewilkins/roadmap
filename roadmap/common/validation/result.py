"""Validation result tracking and error aggregation."""


class ValidationResult:
    """Result of a validation operation."""

    def __init__(
        self,
        is_valid: bool = True,
        errors: list[str] | None = None,
        field: str | None = None,
    ):
        """Initialize ValidationResult.

        Args:
            is_valid: Whether validation passed.
            errors: List of validation error messages.
            field: Name of the field being validated.
        """
        self.is_valid = is_valid
        self.errors = errors or []
        self.field = field

    def add_error(self, error: str):
        """Add an error to the validation result."""
        self.errors.append(error)
        self.is_valid = False

    def merge(self, other: "ValidationResult"):
        """Merge another validation result into this one."""
        if not other.is_valid:
            self.is_valid = False
            self.errors.extend(other.errors)

    def __bool__(self) -> bool:
        """Return whether validation passed."""
        return self.is_valid
