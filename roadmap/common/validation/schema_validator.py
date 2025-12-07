"""Schema-based validator for complex data structures."""

from typing import Any

from .field_validator import FieldValidator
from .result import ValidationResult


class SchemaValidator:
    """Schema-based validator for complex data structures."""

    def __init__(self, schema_name: str):
        self.schema_name = schema_name
        self.validators: dict[str, FieldValidator] = {}

    def add_field(self, validator: FieldValidator) -> "SchemaValidator":
        """Add a field validator to the schema."""
        self.validators[validator.field_name] = validator
        return self

    def validate(self, data: dict[str, Any]) -> ValidationResult:
        """Validate data against the schema."""
        result = ValidationResult()

        # Validate each field
        for field_name, validator in self.validators.items():
            value = data.get(field_name)
            field_result = validator.validate(value)
            result.merge(field_result)

        return result
