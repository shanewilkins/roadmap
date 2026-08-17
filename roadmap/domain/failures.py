"""Failures raised by pure business rules."""


class DomainFailure(ValueError):
    """Base class for invalid domain operations."""


class InvalidValue(DomainFailure):
    """A value cannot enter the domain."""


class InvariantViolation(DomainFailure):
    """An aggregate would become internally inconsistent."""


class InvalidTransition(DomainFailure):
    """A requested workflow or retention transition is forbidden."""
