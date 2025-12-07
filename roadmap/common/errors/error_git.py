"""Git operation related error classes."""

from roadmap.common.errors.error_base import ErrorCategory, ErrorSeverity, RoadmapError


class GitOperationError(RoadmapError):
    """Errors related to Git operations."""

    def __init__(
        self,
        message: str,
        command: str | None = None,
        exit_code: int | None = None,
        **kwargs,
    ):
        context = kwargs.get("context", {})
        if command:
            context["command"] = command
        if exit_code is not None:
            context["exit_code"] = exit_code

        super().__init__(
            message,
            severity=kwargs.get("severity", ErrorSeverity.HIGH),
            category=ErrorCategory.GIT_OPERATION,
            context=context,
            cause=kwargs.get("cause"),
        )
        self.command = command
        self.exit_code = exit_code


class ConfigurationError(RoadmapError):
    """Errors related to configuration."""

    def __init__(self, message: str, config_file=None, **kwargs):
        from pathlib import Path

        context = kwargs.get("context", {})
        if config_file:
            context["config_file"] = (
                str(config_file) if isinstance(config_file, Path) else config_file
            )

        super().__init__(
            message,
            severity=kwargs.get("severity", ErrorSeverity.HIGH),
            category=ErrorCategory.CONFIGURATION,
            context=context,
            cause=kwargs.get("cause"),
        )
        self.config_file = config_file
