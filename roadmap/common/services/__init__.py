"""Service Utilities - Decorators, metrics, performance, and retry logic.

This module contains cross-cutting concerns like logging, metrics, performance
monitoring, and retry logic used by services.
"""

from .decorators import service_operation
from .logging_utils import (
    log_collection_operation,
    log_entry,
    log_event,
    log_exit,
    log_metric,
    log_operation,
    log_state_change,
)
from .metrics import MetricsCollector, OperationMetric, get_metrics_collector
from .performance import OperationTimer, async_timed_operation, timed_operation
from .profiling import (
    OperationProfile,
    PerformanceProfiler,
    PerformanceReport,
    get_profiler,
)
from .retry import (
    API_RETRY,
    DATABASE_RETRY,
    NETWORK_RETRY,
    RetryConfig,
    async_retry,
    retry,
)

__all__ = [
    # Decorators
    "service_operation",
    # Logging
    "log_collection_operation",
    "log_entry",
    "log_event",
    "log_exit",
    "log_metric",
    "log_operation",
    "log_state_change",
    # Metrics
    "MetricsCollector",
    "OperationMetric",
    "get_metrics_collector",
    # Performance
    "OperationTimer",
    "async_timed_operation",
    "timed_operation",
    # Profiling
    "OperationProfile",
    "PerformanceProfiler",
    "PerformanceReport",
    "get_profiler",
    # Retry
    "API_RETRY",
    "DATABASE_RETRY",
    "NETWORK_RETRY",
    "RetryConfig",
    "async_retry",
    "retry",
]
