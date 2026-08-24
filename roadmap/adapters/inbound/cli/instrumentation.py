"""Dependency-free command decorators retained for CLI compatibility."""

from collections.abc import Callable
from functools import wraps
from typing import Any


def log_command(
    _command_name: str,
    entity_type: str | None = None,
    track_duration: bool = True,
    log_args: bool = False,
) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    """Preserve command metadata without configuring a process-wide logger."""
    del entity_type, track_duration, log_args

    def decorate(function: Callable[..., Any]) -> Callable[..., Any]:
        @wraps(function)
        def invoke(*args: Any, **kwargs: Any) -> Any:
            return function(*args, **kwargs)

        return invoke

    return decorate


def verbose_output(function: Callable[..., Any]) -> Callable[..., Any]:
    """Retain the public ``--verbose`` option without ambient log mutation."""

    @wraps(function)
    def invoke(*args: Any, **kwargs: Any) -> Any:
        return function(*args, **kwargs)

    return invoke
