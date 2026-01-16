"""Performance tracking utilities for operation timing and monitoring.

Provides context managers and decorators to track operation duration,
identify bottlenecks, and monitor system performance.
"""

import time
from collections.abc import Generator
from contextlib import contextmanager

from roadmap.common.logging.loggers import get_logger

logger = get_logger(__name__)


@contextmanager
def track_operation_time(
    operation_name: str,
    warn_threshold_ms: int = 5000,
    log_level: str = "debug",
) -> Generator[dict, None, None]:
    """Context manager to track operation timing.

    Args:
        operation_name: Name of the operation being timed
        warn_threshold_ms: Log warning if operation exceeds this time
        log_level: Log level to use for normal operations (debug or info)

    Example:
        with track_operation_time("sync_issues", warn_threshold_ms=5000):
            sync_to_github()
    """
    start_time = time.time()
    result = {"duration_ms": 0, "exceeded_threshold": False}

    try:
        yield result
    finally:
        duration_ms = (time.time() - start_time) * 1000
        result["duration_ms"] = duration_ms

        if duration_ms > warn_threshold_ms:
            result["exceeded_threshold"] = True
            logger.warning(
                f"{operation_name}_slow",
                duration_ms=duration_ms,
                threshold_ms=warn_threshold_ms,
            )
        else:
            log_func = getattr(logger, log_level, logger.debug)
            log_func(
                f"{operation_name}_completed",
                duration_ms=duration_ms,
            )


@contextmanager
def track_database_operation(
    operation: str,
    entity_type: str,
    entity_id: str | None = None,
    warn_threshold_ms: int = 1000,
) -> Generator[dict, None, None]:
    """Context manager to track database operation timing.

    Args:
        operation: Type of operation (create, read, update, delete)
        entity_type: Type of entity
        entity_id: ID of the entity (if applicable)
        warn_threshold_ms: Warn if operation exceeds this time

    Example:
        with track_database_operation("create", "issue", entity_id="123"):
            db.create_issue(...)
    """
    start_time = time.time()
    result = {"duration_ms": 0, "exceeded_threshold": False}

    try:
        yield result
    finally:
        duration_ms = (time.time() - start_time) * 1000
        result["duration_ms"] = duration_ms

        if duration_ms > warn_threshold_ms:
            result["exceeded_threshold"] = True
            logger.warning(
                "database_operation_slow",
                operation=operation,
                entity_type=entity_type,
                entity_id=entity_id,
                duration_ms=duration_ms,
                threshold_ms=warn_threshold_ms,
            )
        else:
            logger.debug(
                "database_operation_completed",
                operation=operation,
                entity_type=entity_type,
                entity_id=entity_id,
                duration_ms=duration_ms,
            )


@contextmanager
def track_file_operation(
    operation: str,
    file_path: str,
    warn_threshold_ms: int = 500,
) -> Generator[dict, None, None]:
    """Context manager to track file I/O operation timing.

    Args:
        operation: Type of operation (read, write, sync)
        file_path: Path to the file
        warn_threshold_ms: Warn if operation exceeds this time

    Example:
        with track_file_operation("sync", "issue.md"):
            sync_issue_file(...)
    """
    start_time = time.time()
    result = {"duration_ms": 0, "exceeded_threshold": False}

    try:
        yield result
    finally:
        duration_ms = (time.time() - start_time) * 1000
        result["duration_ms"] = duration_ms

        if duration_ms > warn_threshold_ms:
            result["exceeded_threshold"] = True
            logger.warning(
                "file_operation_slow",
                operation=operation,
                file_path=file_path,
                duration_ms=duration_ms,
                threshold_ms=warn_threshold_ms,
            )
        else:
            logger.debug(
                "file_operation_completed",
                operation=operation,
                file_path=file_path,
                duration_ms=duration_ms,
            )


@contextmanager
def track_sync_operation(
    operation_name: str,
    entity_count: int | None = None,
    warn_threshold_ms: int = 10000,
) -> Generator[dict, None, None]:
    """Context manager to track sync operation timing and throughput.

    Args:
        operation_name: Name of the sync operation
        entity_count: Number of entities being synced
        warn_threshold_ms: Warn if operation exceeds this time

    Example:
        with track_sync_operation("sync_to_github", entity_count=10):
            github_client.sync_issues(...)
    """
    start_time = time.time()
    result = {
        "duration_ms": 0,
        "exceeded_threshold": False,
        "throughput_items_per_sec": 0,
    }

    try:
        yield result
    finally:
        duration_ms = (time.time() - start_time) * 1000
        result["duration_ms"] = duration_ms

        if entity_count:
            result["throughput_items_per_sec"] = (entity_count * 1000) / duration_ms

        if duration_ms > warn_threshold_ms:
            result["exceeded_threshold"] = True
            logger.warning(
                f"{operation_name}_slow",
                duration_ms=duration_ms,
                entity_count=entity_count,
                threshold_ms=warn_threshold_ms,
                throughput_items_per_sec=result.get("throughput_items_per_sec"),
            )
        else:
            logger.info(
                f"{operation_name}_completed",
                duration_ms=duration_ms,
                entity_count=entity_count,
                throughput_items_per_sec=result.get("throughput_items_per_sec"),
            )


class OperationTimer:
    """Class for tracking multi-step operations and performance metrics."""

    def __init__(self, operation_name: str):
        """Initialize operation timer.

        Args:
            operation_name: Name of the overall operation
        """
        self.operation_name = operation_name
        self.start_time = time.time()
        self.steps = {}
        self.current_step = None
        self.current_step_start = None

    def start_step(self, step_name: str) -> None:
        """Start tracking a named step.

        Args:
            step_name: Name of the step
        """
        if self.current_step:
            self.end_step()

        self.current_step = step_name
        self.current_step_start = time.time()

    def end_step(self) -> None:
        """End tracking current step."""
        if self.current_step and self.current_step_start:
            duration_ms = (time.time() - self.current_step_start) * 1000
            self.steps[self.current_step] = duration_ms
            logger.debug(
                f"{self.operation_name}_step_completed",
                step=self.current_step,
                duration_ms=duration_ms,
            )
            self.current_step = None
            self.current_step_start = None

    def finish(self) -> dict:
        """Finish timing operation and return summary.

        Returns:
            Dictionary with timing information
        """
        if self.current_step:
            self.end_step()

        total_duration_ms = (time.time() - self.start_time) * 1000
        result = {
            "operation": self.operation_name,
            "total_duration_ms": total_duration_ms,
            "steps": self.steps,
        }

        logger.info(
            f"{self.operation_name}_finished",
            **result,
        )

        return result
