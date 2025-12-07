"""Individual field validator with configurable rules."""

import re
from collections.abc import Callable
from typing import Any

from .result import ValidationResult


class FieldValidator:
    """Individual field validator with configurable rules."""

    def __init__(
        self,
        field_name: str,
        required: bool = False,
        min_length: int | None = None,
        max_length: int | None = None,
        pattern: str | None = None,
        enum_values: list[Any] | None = None,
        custom_validator: Callable[[Any], tuple[bool, str]] | None = None,
        allow_none: bool | None = None,
    ):
        self.field_name = field_name
        self.required = required
        self.min_length = min_length
        self.max_length = max_length
        self.pattern = re.compile(pattern) if pattern else None
        self.enum_values = enum_values
        self.custom_validator = custom_validator
        # If allow_none is not specified, set it based on required status
        self.allow_none = allow_none if allow_none is not None else not required

    def validate(self, value: Any) -> ValidationResult:
        """Validate a field value."""
        result = ValidationResult(field=self.field_name)

        # Check if value is None
        if value is None:
            if self.required and not self.allow_none:
                result.add_error(f"Field '{self.field_name}' is required")
            return result

        # Check required field
        if self.required and (value is None or value == ""):
            result.add_error(f"Field '{self.field_name}' is required")

        # Check enum values
        if self.enum_values is not None and value not in self.enum_values:
            result.add_error(
                f"Field '{self.field_name}' must be one of: "
                f"{', '.join(str(v) for v in self.enum_values)}"
            )

        # Check pattern
        if self.pattern is not None and isinstance(value, str):
            if not self.pattern.match(value):
                result.add_error(f"Field '{self.field_name}' format is invalid")

        # Check length
        if isinstance(value, str):
            if self.min_length is not None and len(value) < self.min_length:
                result.add_error(
                    f"Field '{self.field_name}' must be at least {self.min_length} characters"
                )

            if self.max_length is not None and len(value) > self.max_length:
                result.add_error(
                    f"Field '{self.field_name}' must be no more than {self.max_length} characters"
                )

        # Custom validator
        if self.custom_validator is not None:
            is_valid, error_msg = self.custom_validator(value)
            if not is_valid:
                result.add_error(f"Field '{self.field_name}' {error_msg}")

        return result
